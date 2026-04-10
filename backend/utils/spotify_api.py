import os
import re
import threading
import time
from urllib.parse import urlparse

import requests

_SPOTIFY_API_BASE = "https://api.spotify.com/v1"
_SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
_PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9]{10,64}$")

_TOKEN_LOCK = threading.Lock()
_TOKEN_CACHE = {
    "access_token": None,
    "expires_at": 0.0,
}


def _error_message_from_response(response):
    try:
        payload = response.json()
    except Exception:
        text = (response.text or "").strip()
        return text or "Spotify request failed"

    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            detail = (err.get("message") or "").strip()
            status = err.get("status")
            if detail and status:
                return "{} (status {})".format(detail, status)
            if detail:
                return detail
            if status:
                return "Spotify error status {}".format(status)
        if isinstance(err, str) and err.strip():
            return err.strip()

        detail = (payload.get("message") or "").strip()
        if detail:
            return detail

    return "Spotify request failed"


def _has_spotify_app_credentials():
    client_id = (os.environ.get("SPOTIFY_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("SPOTIFY_CLIENT_SECRET") or "").strip()
    return bool(client_id and client_secret)


def _spotify_default_market():
    raw = (os.environ.get("SPOTIFY_DEFAULT_MARKET") or "US").strip().upper()
    return raw if re.match(r"^[A-Z]{2}$", raw) else None


def _token_is_fresh():
    token = _TOKEN_CACHE.get("access_token")
    expires_at = float(_TOKEN_CACHE.get("expires_at") or 0)
    if not token:
        return False
    # Refresh a little early to avoid racing expiry.
    return time.time() < max(0.0, expires_at - 45)


def get_app_access_token(force_refresh=False):
    if not _has_spotify_app_credentials():
        return {
            "success": False,
            "error_code": "spotify_oauth_not_configured",
            "message": "Spotify OAuth is not configured. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.",
        }

    with _TOKEN_LOCK:
        if not force_refresh and _token_is_fresh():
            return {"success": True, "access_token": _TOKEN_CACHE["access_token"]}

        client_id = (os.environ.get("SPOTIFY_CLIENT_ID") or "").strip()
        client_secret = (os.environ.get("SPOTIFY_CLIENT_SECRET") or "").strip()

        try:
            response = requests.post(
                _SPOTIFY_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                timeout=(10, 20),
            )
        except Exception as exc:
            return {
                "success": False,
                "error_code": "spotify_oauth_unavailable",
                "message": "Could not reach Spotify OAuth service: {}".format(str(exc)),
            }

        if response.status_code >= 400:
            return {
                "success": False,
                "error_code": "spotify_oauth_failed",
                "message": "Spotify OAuth failed: {}".format(_error_message_from_response(response)),
                "status_code": response.status_code,
            }

        try:
            payload = response.json() or {}
        except Exception:
            return {
                "success": False,
                "error_code": "spotify_oauth_invalid_response",
                "message": "Spotify OAuth returned invalid JSON.",
            }

        access_token = (payload.get("access_token") or "").strip()
        expires_in_raw = payload.get("expires_in")
        try:
            expires_in = int(expires_in_raw)
        except Exception:
            expires_in = 3600

        if not access_token:
            return {
                "success": False,
                "error_code": "spotify_oauth_invalid_response",
                "message": "Spotify OAuth response did not include an access token.",
            }

        _TOKEN_CACHE["access_token"] = access_token
        _TOKEN_CACHE["expires_at"] = time.time() + max(60, expires_in)
        return {"success": True, "access_token": access_token}


def extract_playlist_id(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return None

    if value.startswith("spotify:playlist:"):
        candidate = value.split("spotify:playlist:", 1)[1].split(":", 1)[0].strip()
        return candidate if _PLAYLIST_ID_RE.match(candidate) else None

    parsed = urlparse(value)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        parts = [part for part in parsed.path.split("/") if part]
        if "playlist" in parts:
            idx = parts.index("playlist")
            if idx + 1 < len(parts):
                candidate = (parts[idx + 1] or "").strip()
                if _PLAYLIST_ID_RE.match(candidate):
                    return candidate

    return value if _PLAYLIST_ID_RE.match(value) else None


def spotify_get(path_or_url, access_token=None, params=None, allow_refresh=True):
    url = path_or_url
    if not str(url).startswith("http"):
        url = "{}{}".format(_SPOTIFY_API_BASE, path_or_url)

    user_token = (access_token or "").strip()
    using_user_token = bool(user_token)

    if not user_token:
        token_result = get_app_access_token(force_refresh=False)
        if not token_result.get("success"):
            return token_result
        user_token = token_result.get("access_token")

    try:
        response = requests.get(
            url,
            headers={"Authorization": "Bearer {}".format(user_token)},
            params=params,
            timeout=(10, 25),
        )
    except Exception as exc:
        return {
            "success": False,
            "error_code": "spotify_request_failed",
            "message": "Spotify API request failed: {}".format(str(exc)),
        }

    if response.status_code == 401 and not using_user_token and allow_refresh:
        refreshed = get_app_access_token(force_refresh=True)
        if not refreshed.get("success"):
            return refreshed
        return spotify_get(
            path_or_url,
            access_token=refreshed.get("access_token"),
            params=params,
            allow_refresh=False,
        )

    if response.status_code == 429:
        retry_after_raw = (response.headers.get("Retry-After") or "").strip()
        retry_after = int(retry_after_raw) if retry_after_raw.isdigit() else 0
        msg = "Spotify rate limit reached."
        if retry_after > 0:
            msg = "Spotify rate limit reached. Retry after {} second(s).".format(retry_after)
        return {
            "success": False,
            "error_code": "spotify_rate_limited",
            "message": msg,
            "status_code": 429,
            "retry_after": retry_after,
        }

    if response.status_code == 404:
        return {
            "success": False,
            "error_code": "spotify_not_found_or_private",
            "message": "Spotify playlist was not found or is private.",
            "status_code": 404,
        }

    if response.status_code == 403:
        raw_message = _error_message_from_response(response)
        normalized = raw_message.lower()

        if "insufficient client scope" in normalized or "insufficient scope" in normalized:
            return {
                "success": False,
                "error_code": "spotify_insufficient_scope",
                "message": (
                    "Spotify denied this request because the app token has insufficient scope "
                    "for this playlist. Some public playlists include restricted item types."
                ),
                "status_code": 403,
                "detail": raw_message,
            }

        return {
            "success": False,
            "error_code": "spotify_forbidden",
            "message": "Spotify denied access to this playlist: {}".format(raw_message),
            "status_code": 403,
        }

    if response.status_code >= 400:
        return {
            "success": False,
            "error_code": "spotify_api_error",
            "message": "Spotify API error: {}".format(_error_message_from_response(response)),
            "status_code": response.status_code,
        }

    try:
        payload = response.json()
    except Exception:
        return {
            "success": False,
            "error_code": "spotify_invalid_json",
            "message": "Spotify API returned invalid JSON.",
            "status_code": response.status_code,
        }

    return {"success": True, "data": payload, "status_code": response.status_code}


def fetch_playlist_with_tracks(playlist_id, access_token=None):
    if not playlist_id:
        return {
            "success": False,
            "error_code": "invalid_playlist_id",
            "message": "Spotify playlist ID is required.",
        }

    market = _spotify_default_market()

    metadata_params = {
        "fields": "id,name,description,public,external_urls,owner(display_name,id),images,tracks(total)",
    }
    if market:
        metadata_params["market"] = market

    metadata_result = spotify_get(
        "/playlists/{}".format(playlist_id),
        access_token=access_token,
        params=metadata_params,
    )

    # Some public playlists can reject strict field projections with app tokens.
    if not metadata_result.get("success") and metadata_result.get("error_code") in (
        "spotify_forbidden",
        "spotify_insufficient_scope",
    ):
        fallback_metadata_params = {}
        if market:
            fallback_metadata_params["market"] = market
        metadata_result = spotify_get(
            "/playlists/{}".format(playlist_id),
            access_token=access_token,
            params=fallback_metadata_params or None,
        )

    if not metadata_result.get("success"):
        return metadata_result

    metadata = metadata_result.get("data") or {}

    all_tracks = []
    offset = 0
    page_limit = 100
    partial_warning = None

    def _build_track_params(compact=False):
        params = {
            "limit": page_limit,
            "offset": offset,
            "additional_types": "track",
        }
        if market:
            params["market"] = market
        if not compact:
            params["fields"] = (
                "items(track(id,name,artists(name),duration_ms,external_urls,is_local,is_playable,album(name,images))),next,total"
            )
        return params

    while True:
        page_result = spotify_get(
            "/playlists/{}/tracks".format(playlist_id),
            access_token=access_token,
            params=_build_track_params(compact=False),
        )

        # Retry with a minimal shape when strict projection is forbidden.
        if not page_result.get("success") and page_result.get("error_code") in (
            "spotify_forbidden",
            "spotify_insufficient_scope",
        ):
            page_result = spotify_get(
                "/playlists/{}/tracks".format(playlist_id),
                access_token=access_token,
                params=_build_track_params(compact=True),
            )

        if not page_result.get("success"):
            if all_tracks:
                partial_warning = page_result
                break
            return page_result

        payload = page_result.get("data") or {}
        items = payload.get("items") or []
        if not isinstance(items, list):
            items = []

        for item in items:
            track = item.get("track") if isinstance(item, dict) else None
            if not isinstance(track, dict):
                continue

            name = (track.get("name") or "").strip()
            if not name:
                continue

            artists = []
            for artist in track.get("artists") or []:
                if isinstance(artist, dict):
                    artist_name = (artist.get("name") or "").strip()
                    if artist_name:
                        artists.append(artist_name)

            album = track.get("album") or {}
            image_url = None
            images = album.get("images") if isinstance(album, dict) else None
            if isinstance(images, list) and images:
                for image in images:
                    if isinstance(image, dict) and image.get("url"):
                        image_url = image.get("url")

            all_tracks.append(
                {
                    "id": track.get("id"),
                    "name": name,
                    "artists": artists,
                    "duration_ms": track.get("duration_ms"),
                    "external_url": (track.get("external_urls") or {}).get("spotify"),
                    "album_name": (album.get("name") or "") if isinstance(album, dict) else "",
                    "image_url": image_url,
                    "is_local": bool(track.get("is_local")),
                    "is_playable": track.get("is_playable"),
                }
            )

        total = payload.get("total")
        if not isinstance(total, int):
            total = len(all_tracks)

        fetched_count = len(items)
        offset += fetched_count

        if fetched_count <= 0 or offset >= total:
            break

    return {
        "success": True,
        "playlist": {
            "id": metadata.get("id"),
            "name": (metadata.get("name") or "").strip(),
            "description": metadata.get("description") or "",
            "public": metadata.get("public"),
            "external_url": (metadata.get("external_urls") or {}).get("spotify"),
            "owner": metadata.get("owner") or {},
            "image_url": ((metadata.get("images") or [{}])[0] or {}).get("url") if isinstance(metadata.get("images"), list) and metadata.get("images") else None,
            "tracks_total": ((metadata.get("tracks") or {}).get("total") if isinstance(metadata.get("tracks"), dict) else None),
        },
        "tracks": all_tracks,
        "partial": bool(partial_warning),
        "warning": (partial_warning or {}).get("message") if partial_warning else None,
        "warning_code": (partial_warning or {}).get("error_code") if partial_warning else None,
        "warning_retry_after": (partial_warning or {}).get("retry_after") if partial_warning else None,
    }
