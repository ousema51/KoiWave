"""
YouTube Music search and audio streaming backend.

Dependencies:
  - ytmusicapi  (music-specific search)
  - yt-dlp      (audio stream URL extraction)
"""

import traceback

# ---------------------------------------------------------------------------
# Optional dependency loading
# ---------------------------------------------------------------------------
_YT_AVAILABLE = False
_YTDLP_AVAILABLE = False

ytmusic = None
yt_dlp = None

try:
    from ytmusicapi import YTMusic
    ytmusic = YTMusic()
    _YT_AVAILABLE = True
except Exception:
    _YT_AVAILABLE = False

try:
    import yt_dlp as _yt_dlp
    yt_dlp = _yt_dlp
    _YTDLP_AVAILABLE = True
except Exception:
    _YTDLP_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_first(lst: list | None, key: str = "name") -> str | None:
    """Return *key* from the first element of *lst*, or ``None``."""
    if lst and len(lst) > 0:
        return lst[0].get(key)
    return None


def _best_thumbnail(thumbnails: list | None) -> str | None:
    """Return the highest-resolution thumbnail URL."""
    if thumbnails and len(thumbnails) > 0:
        return thumbnails[-1].get("url")
    return None


def _normalize_song(raw: dict) -> dict:
    """Turn a ytmusicapi song result into the flat dict the frontend expects."""
    return {
        "id":        raw.get("videoId"),
        "title":     raw.get("title"),
        "artist":    _safe_first(raw.get("artists")),
        "duration":  raw.get("duration"),
        "thumbnail": _best_thumbnail(raw.get("thumbnails")),
    }


def _extract_stream_url(video_id: str) -> str | None:
    """Use yt-dlp to pull the best audio stream URL for *video_id*.

    Tries ``music.youtube.com`` first, then falls back to ``youtube.com``.
    Returns the URL string or ``None``.
    """
    if not _YTDLP_AVAILABLE or yt_dlp is None:
        return None

    candidates = [
        f"https://music.youtube.com/watch?v={video_id}",
        f"https://www.youtube.com/watch?v={video_id}",
    ]

    opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    for url in candidates:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # 1) Direct URL (most common with "bestaudio" format selection)
            if info.get("url"):
                return info["url"]

            # 2) Walk the formats list and pick the best audio-only stream
            formats = info.get("formats") or info.get("requested_formats") or []
            best_url = None
            best_score = -1

            for f in formats:
                acodec = f.get("acodec") or "none"
                vcodec = f.get("vcodec") or "none"
                abr = f.get("abr") or f.get("tbr") or 0

                if acodec == "none" or not f.get("url"):
                    continue

                score = int(abr)
                # Strongly prefer audio-only (no video codec)
                if vcodec in ("none", "unknown", None):
                    score += 10_000

                if score > best_score:
                    best_score = score
                    best_url = f["url"]

            if best_url:
                return best_url

        except Exception:
            continue

    return None


# ---------------------------------------------------------------------------
# Public API – search
# ---------------------------------------------------------------------------

def search_songs(query: str, page: int = 1, limit: int = 20) -> dict:
    """Search YouTube Music for songs matching *query*.

    Returns ``{success: True, data: [...]}``.
    """
    if not _YT_AVAILABLE or ytmusic is None:
        return {"success": False, "message": "ytmusicapi is not available on this server"}

    try:
        raw_results = ytmusic.search(query, filter="songs") or []

        start = max(0, (page - 1) * limit)
        end = start + limit
        songs = [_normalize_song(r) for r in raw_results[start:end]]

        # Drop entries that somehow have no id (safety net)
        songs = [s for s in songs if s["id"]]

        return {"success": True, "data": songs}

    except Exception as e:
        return {
            "success": False,
            "message": f"search_songs failed: {e}",
            "traceback": traceback.format_exc(),
        }


def search_all(query: str):
    """Alias used by some route handlers."""
    return search_songs(query)


# ---------------------------------------------------------------------------
# Public API – stream URL
# ---------------------------------------------------------------------------

def get_stream_url(video_id: str) -> dict:
    """Return a playable audio stream URL for *video_id*.

    Response shape on success::

        {"success": True, "data": {"stream_url": "<url>"}}
    """
    if not _YTDLP_AVAILABLE:
        return {"success": False, "message": "yt-dlp is not available on this server"}

    stream_url = _extract_stream_url(video_id)

    if stream_url:
        return {"success": True, "data": {"stream_url": stream_url}}

    return {"success": False, "message": f"Could not resolve a stream URL for {video_id}"}


def get_song_by_id(video_id: str) -> dict:
    """Return full metadata + stream URL for a single song.

    Response shape on success::

        {"success": True, "data": {"id", "title", "artist", "duration",
                                    "thumbnail", "stream_url"}}
    """
    if not _YTDLP_AVAILABLE or yt_dlp is None:
        return {"success": False, "message": "yt-dlp is not available on this server"}

    url = f"https://music.youtube.com/watch?v={video_id}"
    opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return {"success": False, "message": str(e)}

    # Resolve the stream URL the same way get_stream_url does
    stream_url = info.get("url")
    if not stream_url:
        stream_url = _extract_stream_url(video_id)

    if not stream_url:
        return {"success": False, "message": f"Could not resolve stream for {video_id}"}

    return {
        "success": True,
        "data": {
            "id":         video_id,
            "title":      info.get("title"),
            "artist":     info.get("artist") or info.get("uploader"),
            "duration":   info.get("duration"),
            "thumbnail":  info.get("thumbnail"),
            "stream_url": stream_url,
        },
    }


def get_stream_from_search(query: str, index: int = 0) -> dict:
    """Search YouTube Music and return the stream URL for the *index*-th hit."""
    if not _YT_AVAILABLE or ytmusic is None:
        return {"success": False, "message": "ytmusicapi is not available"}

    try:
        results = ytmusic.search(query, filter="songs") or []
        if not results:
            return {"success": False, "message": "No song results found"}

        chosen = results[index] if index < len(results) else results[0]
        vid = chosen.get("videoId")
        if not vid:
            return {"success": False, "message": "No videoId for the chosen result"}

        return get_stream_url(vid)

    except Exception as e:
        return {"success": False, "message": str(e)}


# ---------------------------------------------------------------------------
# Lightweight stubs for other route-level APIs
# ---------------------------------------------------------------------------

def search_albums(query: str, page: int = 1, limit: int = 20) -> dict:
    if not _YT_AVAILABLE or ytmusic is None:
        return {"success": True, "data": []}
    try:
        raw = ytmusic.search(query, filter="albums") or []
        start = max(0, (page - 1) * limit)
        data = []
        for r in raw[start : start + limit]:
            data.append({
                "id":        r.get("browseId"),
                "title":     r.get("title"),
                "artist":    _safe_first(r.get("artists")),
                "thumbnail": _best_thumbnail(r.get("thumbnails")),
            })
        return {"success": True, "data": data}
    except Exception:
        return {"success": True, "data": []}


def search_artists(query: str, page: int = 1, limit: int = 20) -> dict:
    if not _YT_AVAILABLE or ytmusic is None:
        return {"success": True, "data": []}
    try:
        raw = ytmusic.search(query, filter="artists") or []
        start = max(0, (page - 1) * limit)
        data = []
        for r in raw[start : start + limit]:
            data.append({
                "id":        r.get("browseId"),
                "name":      r.get("artist"),
                "thumbnail": _best_thumbnail(r.get("thumbnails")),
            })
        return {"success": True, "data": data}
    except Exception:
        return {"success": True, "data": []}


def get_album_by_id(album_id: str) -> dict:
    if not _YT_AVAILABLE or ytmusic is None:
        return {"success": False, "message": "ytmusicapi not available"}
    try:
        album = ytmusic.get_album(album_id)
        tracks = []
        for t in album.get("tracks") or []:
            tracks.append(_normalize_song(t))
        return {
            "success": True,
            "data": {
                "id":        album_id,
                "title":     album.get("title"),
                "artist":    _safe_first(album.get("artists")),
                "thumbnail": _best_thumbnail(album.get("thumbnails")),
                "tracks":    tracks,
            },
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_artist_by_id(artist_id: str) -> dict:
    if not _YT_AVAILABLE or ytmusic is None:
        return {"success": False, "message": "ytmusicapi not available"}
    try:
        artist = ytmusic.get_artist(artist_id)
        songs = []
        for s in (artist.get("songs", {}).get("results") or []):
            songs.append(_normalize_song(s))
        return {
            "success": True,
            "data": {
                "id":        artist_id,
                "name":      artist.get("name"),
                "thumbnail": _best_thumbnail(artist.get("thumbnails")),
                "songs":     songs,
            },
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_trending() -> dict:
    """Return a list of currently popular songs from YouTube Music."""
    if not _YT_AVAILABLE or ytmusic is None:
        return {"success": True, "data": []}
    try:
        charts = ytmusic.get_charts()
        trending_songs = []
        for item in (charts.get("trending", {}).get("items") or [])[:20]:
            trending_songs.append(_normalize_song(item))

        # Fallback if charts endpoint returned nothing useful
        if not trending_songs:
            raw = ytmusic.search("top hits", filter="songs") or []
            trending_songs = [_normalize_song(r) for r in raw[:20]]

        return {"success": True, "data": trending_songs}

    except Exception as e:
        return {"success": False, "message": str(e)}