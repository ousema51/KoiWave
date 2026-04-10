import os
from datetime import datetime, timezone
from html import unescape

import jwt as _jwt
from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, g, jsonify, request

import models.db as db
from middleware.auth_middleware import token_required
from utils import spotify_api, youtube_music

playlists_bp = Blueprint("playlists", __name__)


def _pl_to_dict(pl):
    pl = dict(pl)
    pl["_id"] = str(pl["_id"])
    return pl


def _get_playlist_or_404(playlist_id):
    try:
        oid = ObjectId(playlist_id)
    except InvalidId:
        return None, jsonify({"success": False, "message": "Invalid playlist ID"}), 400
    pl = db.playlists.find_one({"_id": oid})
    if not pl:
        return None, jsonify({"success": False, "message": "Playlist not found"}), 404
    return pl, None, None


def _spotify_error_http_status(error_code):
    if error_code == "spotify_rate_limited":
        return 429
    if error_code in ("spotify_not_found_or_private", "invalid_playlist_id"):
        return 404
    if error_code in ("spotify_forbidden", "spotify_insufficient_scope"):
        return 403
    if error_code == "spotify_oauth_not_configured":
        return 500
    if error_code in (
        "spotify_oauth_failed",
        "spotify_oauth_unavailable",
        "spotify_oauth_invalid_response",
        "spotify_request_failed",
        "spotify_api_error",
        "spotify_invalid_json",
    ):
        return 502
    return 400


def _to_int_or_none(value):
    try:
        if value is None:
            return None
        return int(float(value))
    except Exception:
        return None


def _build_track_query(track):
    name = (track.get("name") or "").strip()
    if not name:
        return ""

    artists = track.get("artists") or []
    normalized_artists = []
    for artist in artists:
        artist_name = (artist or "").strip()
        if artist_name:
            normalized_artists.append(artist_name)

    if not normalized_artists:
        return name

    # Keep query compact; too many tokens tends to hurt matching quality.
    return "{} {}".format(name, " ".join(normalized_artists[:2])).strip()


def _map_youtube_song_for_playlist(youtube_song, spotify_track, imported_at_iso):
    song_id = (youtube_song.get("id") or "").strip()
    title = (youtube_song.get("title") or spotify_track.get("name") or "Unknown").strip()

    artist = (youtube_song.get("artist") or "").strip()
    if not artist:
        artists = spotify_track.get("artists") or []
        artist = ", ".join([a for a in artists if a]).strip()

    duration = _to_int_or_none(youtube_song.get("duration"))
    if duration is None:
        duration_ms = _to_int_or_none(spotify_track.get("duration_ms"))
        if duration_ms is not None:
            duration = max(0, duration_ms // 1000)

    return {
        "song_id": song_id,
        "title": title,
        "artist": artist,
        "cover_url": youtube_song.get("cover_url") or youtube_song.get("thumbnail") or spotify_track.get("image_url"),
        "duration": duration,
        "source": "spotify_import",
        "spotify_track": {
            "id": spotify_track.get("id"),
            "name": spotify_track.get("name"),
            "artists": spotify_track.get("artists") or [],
            "external_url": spotify_track.get("external_url"),
        },
        "added_at": imported_at_iso,
    }


# ── Owner's playlists ────────────────────────────────────────────────────────

@playlists_bp.route("/mine", methods=["GET"])
@token_required
def get_mine():
    user_id = g.current_user["_id"]
    cursor = db.playlists.find({"owner_id": user_id}).sort("created_at", -1)
    return jsonify({"success": True, "data": [_pl_to_dict(p) for p in cursor]}), 200


@playlists_bp.route("", methods=["POST"])
@token_required
def create_playlist():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "Playlist name is required"}), 400

    now = datetime.now(tz=timezone.utc)
    doc = {
        "owner_id": g.current_user["_id"],
        "name": name,
        "description": data.get("description", ""),
        "is_public": bool(data.get("is_public", True)),
        "songs": [],
        "created_at": now,
        "updated_at": now,
    }
    result = db.playlists.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return jsonify({"success": True, "data": doc}), 201


@playlists_bp.route("/import/spotify", methods=["POST"])
@token_required
def import_spotify_playlist():
    data = request.get_json(silent=True) or {}
    spotify_url = (data.get("spotify_url") or data.get("url") or "").strip()
    spotify_access_token = (data.get("spotify_access_token") or "").strip() or None

    if not spotify_url:
        return jsonify({"success": False, "message": "Spotify playlist URL is required"}), 400

    playlist_id = spotify_api.extract_playlist_id(spotify_url)
    if not playlist_id:
        return jsonify({"success": False, "message": "Invalid Spotify playlist URL"}), 400

    fetched = spotify_api.fetch_playlist_with_tracks(playlist_id, access_token=spotify_access_token)
    if not fetched.get("success"):
        error_code = fetched.get("error_code")
        payload = {
            "success": False,
            "message": fetched.get("message") or "Failed to fetch Spotify playlist",
            "error_code": error_code,
        }
        detail = fetched.get("detail")
        if detail:
            payload["detail"] = detail
        retry_after = fetched.get("retry_after")
        if retry_after:
            payload["retry_after"] = retry_after
        return jsonify(payload), _spotify_error_http_status(error_code)

    spotify_playlist = fetched.get("playlist") or {}
    spotify_tracks = fetched.get("tracks") or []
    imported_at = datetime.now(tz=timezone.utc)
    imported_at_iso = imported_at.isoformat()

    playlist_name = (spotify_playlist.get("name") or "Imported from Spotify").strip()
    spotify_description = unescape((spotify_playlist.get("description") or "").strip())

    description_parts = []
    if spotify_description:
        description_parts.append(spotify_description)
    description_parts.append("Imported from Spotify")

    import_source_url = spotify_playlist.get("external_url") or spotify_url

    added_song_ids = set()
    local_songs = []
    skipped_tracks = []
    query_cache = {}
    duplicate_count = 0

    for track in spotify_tracks:
        query = _build_track_query(track)
        if not query:
            skipped_tracks.append(
                {
                    "name": track.get("name") or "Unknown Track",
                    "artists": track.get("artists") or [],
                    "reason": "missing_track_metadata",
                }
            )
            continue

        youtube_song = query_cache.get(query)
        if query not in query_cache:
            youtube_song = None
            search_result = youtube_music.search_songs(query, page=1, limit=3)
            if isinstance(search_result, dict) and search_result.get("success"):
                for candidate in search_result.get("data") or []:
                    if not isinstance(candidate, dict):
                        continue
                    candidate_id = (candidate.get("id") or "").strip()
                    if candidate_id:
                        youtube_song = candidate
                        break
            query_cache[query] = youtube_song

        if not youtube_song:
            skipped_tracks.append(
                {
                    "name": track.get("name") or "Unknown Track",
                    "artists": track.get("artists") or [],
                    "reason": "not_available_on_source",
                }
            )
            continue

        song_id = (youtube_song.get("id") or "").strip()
        if song_id in added_song_ids:
            duplicate_count += 1
            continue
        added_song_ids.add(song_id)

        local_songs.append(_map_youtube_song_for_playlist(youtube_song, track, imported_at_iso))

    now = datetime.now(tz=timezone.utc)
    doc = {
        "owner_id": g.current_user["_id"],
        "name": playlist_name,
        "description": " | ".join([part for part in description_parts if part]),
        "is_public": False,
        "songs": local_songs,
        "created_at": now,
        "updated_at": now,
        "import_source": {
            "provider": "spotify",
            "playlist_id": spotify_playlist.get("id") or playlist_id,
            "playlist_url": import_source_url,
            "owner": spotify_playlist.get("owner") or {},
        },
    }

    result = db.playlists.insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    total_tracks = len(spotify_tracks)
    imported_count = len(local_songs)
    missing_count = len(skipped_tracks)

    if total_tracks == 0:
        message = "Spotify playlist imported, but it has no tracks."
    elif imported_count == 0:
        message = "Playlist created, but none of the Spotify tracks were available on this source."
    elif missing_count > 0:
        message = "Playlist imported with partial success: {} of {} tracks added.".format(imported_count, total_tracks)
    else:
        message = "Spotify playlist imported successfully."

    response_data = {
        "playlist": doc,
        "spotify": spotify_playlist,
        "summary": {
            "total_spotify_tracks": total_tracks,
            "imported_tracks": imported_count,
            "skipped_missing": missing_count,
            "skipped_duplicates": duplicate_count,
        },
        "skipped_tracks": skipped_tracks[:50],
    }

    if fetched.get("partial"):
        response_data["summary"]["partial_fetch"] = True
        response_data["summary"]["fetch_warning"] = fetched.get("warning")
        warning_retry_after = fetched.get("warning_retry_after")
        if warning_retry_after:
            response_data["summary"]["retry_after"] = warning_retry_after

    return jsonify({"success": True, "message": message, "data": response_data}), 201


# ── Single playlist ──────────────────────────────────────────────────────────

@playlists_bp.route("/<playlist_id>", methods=["GET"])
def get_playlist(playlist_id):
    pl, err, code = _get_playlist_or_404(playlist_id)
    if err:
        return err, code

    requesting_user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = _jwt.decode(token, os.environ.get("JWT_SECRET", "changeme"), algorithms=["HS256"])
            requesting_user_id = payload.get("user_id")
        except Exception:
            pass

    if not pl["is_public"] and pl["owner_id"] != requesting_user_id:
        return jsonify({"success": False, "message": "Access denied"}), 403

    return jsonify({"success": True, "data": _pl_to_dict(pl)}), 200


@playlists_bp.route("/<playlist_id>", methods=["PUT"])
@token_required
def update_playlist(playlist_id):
    pl, err, code = _get_playlist_or_404(playlist_id)
    if err:
        return err, code
    if pl["owner_id"] != g.current_user["_id"]:
        return jsonify({"success": False, "message": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}
    updates = {}
    if "name" in data:
        name = data["name"].strip()
        if not name:
            return jsonify({"success": False, "message": "Playlist name cannot be empty"}), 400
        updates["name"] = name
    if "description" in data:
        updates["description"] = data["description"]
    if "is_public" in data:
        updates["is_public"] = bool(data["is_public"])
    updates["updated_at"] = datetime.now(tz=timezone.utc)

    db.playlists.update_one({"_id": pl["_id"]}, {"$set": updates})
    updated = db.playlists.find_one({"_id": pl["_id"]})
    return jsonify({"success": True, "data": _pl_to_dict(updated)}), 200


@playlists_bp.route("/<playlist_id>", methods=["DELETE"])
@token_required
def delete_playlist(playlist_id):
    pl, err, code = _get_playlist_or_404(playlist_id)
    if err:
        return err, code
    if pl["owner_id"] != g.current_user["_id"]:
        return jsonify({"success": False, "message": "Forbidden"}), 403

    db.playlists.delete_one({"_id": pl["_id"]})
    db.playlist_follows.delete_many({"playlist_id": playlist_id})
    return jsonify({"success": True, "message": "Playlist deleted"}), 200


# ── Playlist songs ───────────────────────────────────────────────────────────

@playlists_bp.route("/<playlist_id>/songs", methods=["POST"])
@token_required
def add_song(playlist_id):
    pl, err, code = _get_playlist_or_404(playlist_id)
    if err:
        return err, code
    if pl["owner_id"] != g.current_user["_id"]:
        return jsonify({"success": False, "message": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}
    song_id = (data.get("song_id") or "").strip()
    if not song_id:
        return jsonify({"success": False, "message": "song_id is required"}), 400

    # Prevent duplicates
    if any(s.get("song_id") == song_id for s in pl.get("songs", [])):
        return jsonify({"success": False, "message": "Song already in playlist"}), 400

    song_entry = {
        "song_id": song_id,
        "title": data.get("title"),
        "artist": data.get("artist"),
        "cover_url": data.get("cover_url"),
        "duration": data.get("duration"),
        "added_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    db.playlists.update_one(
        {"_id": pl["_id"]},
        {"$push": {"songs": song_entry}, "$set": {"updated_at": datetime.now(tz=timezone.utc)}},
    )
    return jsonify({"success": True, "message": "Song added to playlist"}), 201


@playlists_bp.route("/<playlist_id>/songs/<song_id>", methods=["DELETE"])
@token_required
def remove_song(playlist_id, song_id):
    pl, err, code = _get_playlist_or_404(playlist_id)
    if err:
        return err, code
    if pl["owner_id"] != g.current_user["_id"]:
        return jsonify({"success": False, "message": "Forbidden"}), 403

    db.playlists.update_one(
        {"_id": pl["_id"]},
        {"$pull": {"songs": {"song_id": song_id}}, "$set": {"updated_at": datetime.now(tz=timezone.utc)}},
    )
    return jsonify({"success": True, "message": "Song removed from playlist"}), 200


# ── Follow / unfollow ────────────────────────────────────────────────────────

@playlists_bp.route("/<playlist_id>/follow", methods=["POST"])
@token_required
def follow_playlist(playlist_id):
    pl, err, code = _get_playlist_or_404(playlist_id)
    if err:
        return err, code
    if not pl["is_public"]:
        return jsonify({"success": False, "message": "Cannot follow a private playlist"}), 403

    user_id = g.current_user["_id"]
    if db.playlist_follows.find_one({"user_id": user_id, "playlist_id": playlist_id}):
        return jsonify({"success": False, "message": "Already following this playlist"}), 400

    db.playlist_follows.insert_one({"user_id": user_id, "playlist_id": playlist_id, "followed_at": datetime.now(tz=timezone.utc)})
    return jsonify({"success": True, "message": "Playlist followed"}), 201


@playlists_bp.route("/<playlist_id>/follow", methods=["DELETE"])
@token_required
def unfollow_playlist(playlist_id):
    user_id = g.current_user["_id"]
    result = db.playlist_follows.delete_one({"user_id": user_id, "playlist_id": playlist_id})
    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "You are not following this playlist"}), 404
    return jsonify({"success": True, "message": "Playlist unfollowed"}), 200


@playlists_bp.route("/following", methods=["GET"])
@token_required
def get_following():
    user_id = g.current_user["_id"]
    follows = list(db.playlist_follows.find({"user_id": user_id}))
    playlist_ids = []
    for f in follows:
        try:
            playlist_ids.append(ObjectId(f["playlist_id"]))
        except InvalidId:
            pass

    result = []
    for pl in db.playlists.find({"_id": {"$in": playlist_ids}}):
        result.append(_pl_to_dict(pl))

    return jsonify({"success": True, "data": result}), 200
