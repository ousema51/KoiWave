"""
YouTube Music backend — search via ytmusicapi, streams via Piped/Invidious.
Works on Vercel serverless with zero binary dependencies.
"""

import requests
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Init ytmusicapi
# ---------------------------------------------------------------------------
ytmusic = None
try:
    from ytmusicapi import YTMusic
    ytmusic = YTMusic()
except Exception as e:
    logger.error(f"ytmusicapi failed: {e}")

# ---------------------------------------------------------------------------
# Piped instances (free, public, return direct audio URLs)
# ---------------------------------------------------------------------------
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.adminforge.de",
    "https://api.piped.yt",
]


def _get_stream_url(video_id: str) -> str | None:
    """Hit Piped API to get a direct audio stream URL."""
    for base in PIPED_INSTANCES:
        try:
            resp = requests.get(f"{base}/streams/{video_id}", timeout=8)
            if resp.status_code != 200:
                continue
            data = resp.json()
            audio_streams = data.get("audioStreams") or []
            # Pick highest bitrate
            best = max(audio_streams, key=lambda s: s.get("bitrate", 0), default=None)
            if best and best.get("url"):
                return best["url"]
        except Exception as e:
            logger.warning(f"Piped instance {base} failed: {e}")
            continue
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(r: dict) -> dict:
    artists = r.get("artists") or []
    thumbs = r.get("thumbnails") or []
    return {
        "id": r.get("videoId"),
        "title": r.get("title"),
        "artist": artists[0].get("name") if artists else None,
        "duration": r.get("duration"),
        "thumbnail": thumbs[-1].get("url") if thumbs else None,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_songs(query: str, page: int = 1, limit: int = 20) -> dict:
    if not ytmusic:
        return {"success": False, "message": "ytmusicapi not available"}
    try:
        start = (page - 1) * limit
        raw = ytmusic.search(query, filter="songs", limit=start + limit) or []
        songs = [_normalize(r) for r in raw[start:start + limit] if r.get("videoId")]
        return {"success": True, "data": songs}
    except Exception as e:
        return {"success": False, "message": str(e)}


def search_all(query: str):
    return search_songs(query)


def get_stream_url(video_id: str) -> dict:
    url = _get_stream_url(video_id)
    if url:
        return {"success": True, "data": {"stream_url": url}}
    return {"success": False, "message": f"Could not get stream for {video_id}"}


def get_song_by_id(video_id: str) -> dict:
    # Get metadata
    meta = {}
    if ytmusic:
        try:
            info = ytmusic.get_song(video_id)
            vd = info.get("videoDetails") or {}
            thumbs = vd.get("thumbnail", {}).get("thumbnails") or []
            meta = {
                "title": vd.get("title"),
                "artist": vd.get("author"),
                "duration": vd.get("lengthSeconds"),
                "thumbnail": thumbs[-1].get("url") if thumbs else None,
            }
        except Exception:
            pass

    # Get stream
    url = _get_stream_url(video_id)
    if not url:
        return {"success": False, "message": f"Could not get stream for {video_id}"}

    return {
        "success": True,
        "data": {
            "id": video_id,
            "title": meta.get("title"),
            "artist": meta.get("artist"),
            "duration": meta.get("duration"),
            "thumbnail": meta.get("thumbnail"),
            "stream_url": url,
        },
    }


def get_stream_from_search(query: str, index: int = 0) -> dict:
    result = search_songs(query, limit=index + 5)
    if not result.get("success") or not result.get("data"):
        return {"success": False, "message": "No results"}
    songs = result["data"]
    chosen = songs[index] if index < len(songs) else songs[0]
    return get_stream_url(chosen["id"])


def search_albums(query: str, page: int = 1, limit: int = 20) -> dict:
    if not ytmusic:
        return {"success": True, "data": []}
    try:
        raw = ytmusic.search(query, filter="albums", limit=limit) or []
        start = (page - 1) * limit
        return {"success": True, "data": [
            {
                "id": r.get("browseId"),
                "title": r.get("title"),
                "artist": (r.get("artists") or [{}])[0].get("name"),
                "thumbnail": (r.get("thumbnails") or [{}])[-1].get("url"),
            }
            for r in raw[start:start + limit]
        ]}
    except Exception:
        return {"success": True, "data": []}


def search_artists(query: str, page: int = 1, limit: int = 20) -> dict:
    if not ytmusic:
        return {"success": True, "data": []}
    try:
        raw = ytmusic.search(query, filter="artists", limit=limit) or []
        start = (page - 1) * limit
        return {"success": True, "data": [
            {
                "id": r.get("browseId"),
                "name": r.get("artist"),
                "thumbnail": (r.get("thumbnails") or [{}])[-1].get("url"),
            }
            for r in raw[start:start + limit]
        ]}
    except Exception:
        return {"success": True, "data": []}


def get_album_by_id(album_id: str) -> dict:
    if not ytmusic:
        return {"success": False, "message": "ytmusicapi not available"}
    try:
        album = ytmusic.get_album(album_id)
        return {"success": True, "data": {
            "id": album_id,
            "title": album.get("title"),
            "artist": (album.get("artists") or [{}])[0].get("name"),
            "thumbnail": (album.get("thumbnails") or [{}])[-1].get("url"),
            "tracks": [_normalize(t) for t in (album.get("tracks") or [])],
        }}
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_artist_by_id(artist_id: str) -> dict:
    if not ytmusic:
        return {"success": False, "message": "ytmusicapi not available"}
    try:
        artist = ytmusic.get_artist(artist_id)
        return {"success": True, "data": {
            "id": artist_id,
            "name": artist.get("name"),
            "thumbnail": (artist.get("thumbnails") or [{}])[-1].get("url"),
            "songs": [_normalize(s) for s in (artist.get("songs", {}).get("results") or [])],
        }}
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_trending() -> dict:
    if not ytmusic:
        return {"success": True, "data": []}
    try:
        raw = ytmusic.search("top hits 2024", filter="songs", limit=20) or []
        return {"success": True, "data": [_normalize(r) for r in raw if r.get("videoId")]}
    except Exception:
        return {"success": True, "data": []}


def health_check() -> dict:
    """Quick diagnostic endpoint."""
    status = {"ytmusic": ytmusic is not None, "piped": False}
    # Test stream
    test_url = _get_stream_url("dQw4w9WgXcQ")
    status["piped"] = bool(test_url)
    return {"success": True, "data": status}