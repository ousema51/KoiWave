"""
YouTube Music search and audio streaming backend.

Dependencies:
  - ytmusicapi  (music-specific search)
  - yt-dlp      (audio stream URL extraction)
"""

import traceback
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency loading
# ---------------------------------------------------------------------------
_YT_AVAILABLE = False
_YTDLP_AVAILABLE = False

ytmusic = None
yt_dlp = None
YTMusic = None

try:
    from ytmusicapi import YTMusic as _YTMusic
    YTMusic = _YTMusic
    _YT_AVAILABLE = True
except ImportError:
    logger.warning("ytmusicapi not installed")
except Exception as e:
    logger.warning(f"ytmusicapi import error: {e}")

try:
    import yt_dlp as _yt_dlp
    yt_dlp = _yt_dlp
    _YTDLP_AVAILABLE = True
except ImportError:
    logger.warning("yt-dlp not installed")
except Exception as e:
    logger.warning(f"yt-dlp import error: {e}")

# Initialize ytmusic client — try multiple strategies
if _YT_AVAILABLE and YTMusic is not None:
    # Strategy 1: default (no auth)
    try:
        ytmusic = YTMusic()
        # Smoke test: run a tiny search to confirm it actually works
        _test = ytmusic.search("test", filter="songs", limit=1)
        if not _test:
            raise RuntimeError("smoke test returned empty")
        logger.info("ytmusicapi initialized (default)")
    except Exception as e1:
        logger.warning(f"ytmusicapi default init failed: {e1}")
        ytmusic = None

        # Strategy 2: with language/geo params
        try:
            ytmusic = YTMusic(language="en", location="US")
            _test = ytmusic.search("test", filter="songs", limit=1)
            if not _test:
                raise RuntimeError("smoke test returned empty")
            logger.info("ytmusicapi initialized (en/US)")
        except Exception as e2:
            logger.warning(f"ytmusicapi en/US init failed: {e2}")
            ytmusic = None
            _YT_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_first(lst, key: str = "name"):
    """Return *key* from the first element of *lst*, or None."""
    if isinstance(lst, list) and len(lst) > 0 and isinstance(lst[0], dict):
        return lst[0].get(key)
    return None


def _best_thumbnail(thumbnails):
    """Return the highest-resolution thumbnail URL."""
    if isinstance(thumbnails, list) and len(thumbnails) > 0:
        return thumbnails[-1].get("url")
    return None


def _normalize_song(raw: dict) -> dict:
    """Turn a ytmusicapi song result into the flat dict the frontend expects."""
    vid = raw.get("videoId") or raw.get("id")
    title = raw.get("title") or "Unknown"
    artist = _safe_first(raw.get("artists")) or raw.get("artist") or "Unknown Artist"
    duration = raw.get("duration") or raw.get("duration_seconds")
    thumbnail = _best_thumbnail(raw.get("thumbnails")) or raw.get("thumbnail")

    return {
        "id": vid,
        "title": title,
        "artist": artist,
        "duration": duration,
        "thumbnail": thumbnail,
    }


def _get_ytdlp_opts() -> dict:
    """Base yt-dlp options that work reliably across environments."""
    return {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        # Bypass age-gate and some restrictions
        "age_limit": None,
        # Use android client which is less restrictive
        "extractor_args": {
            "youtube": {
                "player_client": ["android_music", "android", "web"],
            }
        },
        # Needed for some environments
        "socket_timeout": 15,
        "retries": 3,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "source_address": "0.0.0.0",
        # HTTP headers to look like a real client
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 13; Pixel 7)"
                " AppleWebKit/537.36 (KHTML, like Gecko)"
                " Chrome/120.0.0.0 Mobile Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    }


def _extract_stream_url(video_id: str) -> dict | None:
    """Use yt-dlp to extract the best audio stream URL for *video_id*.

    Returns a dict with stream info on success, or None on failure.
    """
    if not _YTDLP_AVAILABLE or yt_dlp is None:
        return None

    candidates = [
        f"https://music.youtube.com/watch?v={video_id}",
        f"https://www.youtube.com/watch?v={video_id}",
    ]

    opts = _get_ytdlp_opts()
    last_error = None

    for watch_url in candidates:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(watch_url, download=False)

            if not info:
                continue

            # --- Try to find a working stream URL ---

            # 1) Direct URL from the selected format
            stream_url = info.get("url")
            if stream_url and stream_url.startswith("http"):
                return {
                    "stream_url": stream_url,
                    "title": info.get("title"),
                    "artist": info.get("artist") or info.get("uploader"),
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail"),
                }

            # 2) requested_formats (when yt-dlp merges audio+video)
            req_formats = info.get("requested_formats") or []
            for rf in req_formats:
                acodec = rf.get("acodec") or "none"
                if acodec != "none" and rf.get("url", "").startswith("http"):
                    return {
                        "stream_url": rf["url"],
                        "title": info.get("title"),
                        "artist": info.get("artist") or info.get("uploader"),
                        "duration": info.get("duration"),
                        "thumbnail": info.get("thumbnail"),
                    }

            # 3) Walk all formats, pick best audio-only
            formats = info.get("formats") or []
            best_url = None
            best_score = -1
            for f in formats:
                f_url = f.get("url") or ""
                if not f_url.startswith("http"):
                    continue
                acodec = f.get("acodec") or "none"
                vcodec = f.get("vcodec") or "none"
                if acodec == "none":
                    continue

                abr = 0
                try:
                    abr = float(f.get("abr") or f.get("tbr") or 0)
                except (ValueError, TypeError):
                    pass

                score = abr
                # Strongly prefer audio-only streams
                if vcodec in ("none", "unknown"):
                    score += 10_000
                # Prefer m4a/webm over others for browser compatibility
                ext = f.get("ext") or ""
                if ext in ("m4a", "webm", "opus"):
                    score += 5_000

                if score > best_score:
                    best_score = score
                    best_url = f_url

            if best_url:
                return {
                    "stream_url": best_url,
                    "title": info.get("title"),
                    "artist": info.get("artist") or info.get("uploader"),
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail"),
                }

        except Exception as e:
            last_error = str(e)
            logger.warning(f"yt-dlp failed for {watch_url}: {e}")
            continue

    logger.error(f"All extraction attempts failed for {video_id}. Last error: {last_error}")
    return None


# ---------------------------------------------------------------------------
# yt-dlp fallback search (music-only via YouTube Music)
# ---------------------------------------------------------------------------

def _ytdlp_music_search(query: str, limit: int = 20) -> list:
    """Use yt-dlp to search YouTube Music directly as a fallback."""
    if not _YTDLP_AVAILABLE or yt_dlp is None:
        return []

    search_url = f"https://music.youtube.com/search?q={query}"
    opts = {
        **_get_ytdlp_opts(),
        "extract_flat": True,
        "playlist_items": f"1:{limit}",
        "default_search": "ytsearch",
    }

    try:
        # yt-dlp supports ytmsearch: prefix for YouTube Music
        search_query = f"ytmsearch{limit}:{query}"
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
        entries = info.get("entries") or []
        results = []
        for e in entries:
            vid = e.get("id") or e.get("url", "").split("v=")[-1].split("&")[0]
            if not vid:
                continue
            results.append({
                "id": vid,
                "title": e.get("title") or "Unknown",
                "artist": e.get("artist") or e.get("uploader") or e.get("channel") or "Unknown Artist",
                "duration": e.get("duration"),
                "thumbnail": e.get("thumbnail") or e.get("thumbnails", [{}])[-1].get("url") if e.get("thumbnails") else None,
            })
        return results
    except Exception as e:
        logger.warning(f"yt-dlp music search failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Public API – search
# ---------------------------------------------------------------------------

def search_songs(query: str, page: int = 1, limit: int = 20) -> dict:
    """Search YouTube Music for songs matching *query*.

    Returns ``{success: True, data: [...]}``.
    Uses ytmusicapi as primary, yt-dlp ytmsearch as fallback.
    """
    if not query or not query.strip():
        return {"success": False, "message": "Empty search query"}

    query = query.strip()
    start = max(0, (page - 1) * limit)
    end = start + limit

    # --- Primary: ytmusicapi ---
    if _YT_AVAILABLE and ytmusic is not None:
        try:
            raw_results = ytmusic.search(query, filter="songs", limit=limit + start) or []
            songs = [_normalize_song(r) for r in raw_results[start:end]]
            # Drop entries with no usable id
            songs = [s for s in songs if s.get("id")]

            if songs:
                return {"success": True, "data": songs}

            logger.warning(f"ytmusicapi returned 0 results for: {query}")
        except Exception as e:
            logger.warning(f"ytmusicapi search failed: {e}")

    # --- Fallback: yt-dlp YouTube Music search ---
    if _YTDLP_AVAILABLE:
        try:
            fallback_results = _ytdlp_music_search(query, limit=limit + start)
            songs = fallback_results[start:end]
            songs = [s for s in songs if s.get("id")]

            if songs:
                return {"success": True, "data": songs}

            logger.warning(f"yt-dlp music search returned 0 results for: {query}")
        except Exception as e:
            logger.warning(f"yt-dlp fallback search failed: {e}")

    # --- Nothing worked ---
    available = []
    if _YT_AVAILABLE:
        available.append("ytmusicapi")
    if _YTDLP_AVAILABLE:
        available.append("yt-dlp")

    return {
        "success": False,
        "message": f"No results found for '{query}'",
        "debug": {
            "available_backends": available,
            "ytmusic_initialized": ytmusic is not None,
            "ytdlp_available": _YTDLP_AVAILABLE,
        },
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
    if not video_id or not video_id.strip():
        return {"success": False, "message": "No video_id provided"}

    video_id = video_id.strip()

    if not _YTDLP_AVAILABLE:
        return {
            "success": False,
            "message": "yt-dlp is not available on this server",
        }

    result = _extract_stream_url(video_id)

    if result and result.get("stream_url"):
        return {"success": True, "data": result}

    return {
        "success": False,
        "message": f"Could not resolve a stream URL for {video_id}",
        "debug": {
            "ytdlp_available": _YTDLP_AVAILABLE,
            "ytmusic_available": _YT_AVAILABLE,
            "video_id": video_id,
            "hint": "Ensure yt-dlp is up to date: pip install -U yt-dlp",
        },
    }


def get_song_by_id(video_id: str) -> dict:
    """Return full metadata + stream URL for a single song.

    Response shape on success::
        {"success": True, "data": {"id", "title", "artist", "duration",
                                    "thumbnail", "stream_url"}}
    """
    if not video_id or not video_id.strip():
        return {"success": False, "message": "No video_id provided"}

    video_id = video_id.strip()

    if not _YTDLP_AVAILABLE or yt_dlp is None:
        return {"success": False, "message": "yt-dlp is not available on this server"}

    result = _extract_stream_url(video_id)

    if not result or not result.get("stream_url"):
        return {"success": False, "message": f"Could not resolve stream for {video_id}"}

    return {
        "success": True,
        "data": {
            "id": video_id,
            "title": result.get("title"),
            "artist": result.get("artist"),
            "duration": result.get("duration"),
            "thumbnail": result.get("thumbnail"),
            "stream_url": result["stream_url"],
        },
    }


def get_stream_from_search(query: str, index: int = 0) -> dict:
    """Search YouTube Music and return the stream URL for the *index*-th hit."""
    search_result = search_songs(query, page=1, limit=index + 5)

    if not search_result.get("success") or not search_result.get("data"):
        return {"success": False, "message": f"No results found for '{query}'"}

    songs = search_result["data"]
    chosen = songs[index] if index < len(songs) else songs[0]
    vid = chosen.get("id")

    if not vid:
        return {"success": False, "message": "No videoId for the chosen result"}

    stream_result = get_stream_url(vid)

    # Merge song metadata into the stream result
    if stream_result.get("success"):
        stream_result["data"]["id"] = vid
        stream_result["data"]["title"] = stream_result["data"].get("title") or chosen.get("title")
        stream_result["data"]["artist"] = stream_result["data"].get("artist") or chosen.get("artist")
        stream_result["data"]["thumbnail"] = stream_result["data"].get("thumbnail") or chosen.get("thumbnail")

    return stream_result


# ---------------------------------------------------------------------------
# Lightweight stubs / real implementations for other route-level APIs
# ---------------------------------------------------------------------------

def search_albums(query: str, page: int = 1, limit: int = 20) -> dict:
    if not _YT_AVAILABLE or ytmusic is None:
        return {"success": True, "data": []}
    try:
        raw = ytmusic.search(query, filter="albums", limit=limit) or []
        start = max(0, (page - 1) * limit)
        data = []
        for r in raw[start: start + limit]:
            data.append({
                "id": r.get("browseId"),
                "title": r.get("title"),
                "artist": _safe_first(r.get("artists")),
                "thumbnail": _best_thumbnail(r.get("thumbnails")),
            })
        return {"success": True, "data": data}
    except Exception as e:
        logger.warning(f"search_albums failed: {e}")
        return {"success": True, "data": []}


def search_artists(query: str, page: int = 1, limit: int = 20) -> dict:
    if not _YT_AVAILABLE or ytmusic is None:
        return {"success": True, "data": []}
    try:
        raw = ytmusic.search(query, filter="artists", limit=limit) or []
        start = max(0, (page - 1) * limit)
        data = []
        for r in raw[start: start + limit]:
            data.append({
                "id": r.get("browseId"),
                "name": r.get("artist"),
                "thumbnail": _best_thumbnail(r.get("thumbnails")),
            })
        return {"success": True, "data": data}
    except Exception as e:
        logger.warning(f"search_artists failed: {e}")
        return {"success": True, "data": []}


def get_album_by_id(album_id: str) -> dict:
    if not _YT_AVAILABLE or ytmusic is None:
        return {"success": False, "message": "ytmusicapi not available"}
    try:
        album = ytmusic.get_album(album_id)
        tracks = [_normalize_song(t) for t in (album.get("tracks") or [])]
        return {
            "success": True,
            "data": {
                "id": album_id,
                "title": album.get("title"),
                "artist": _safe_first(album.get("artists")),
                "thumbnail": _best_thumbnail(album.get("thumbnails")),
                "tracks": tracks,
            },
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_artist_by_id(artist_id: str) -> dict:
    if not _YT_AVAILABLE or ytmusic is None:
        return {"success": False, "message": "ytmusicapi not available"}
    try:
        artist = ytmusic.get_artist(artist_id)
        songs_data = artist.get("songs", {})
        songs = [_normalize_song(s) for s in (songs_data.get("results") or [])]
        return {
            "success": True,
            "data": {
                "id": artist_id,
                "name": artist.get("name"),
                "thumbnail": _best_thumbnail(artist.get("thumbnails")),
                "songs": songs,
            },
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_trending() -> dict:
    """Return a list of currently popular songs from YouTube Music."""
    if not _YT_AVAILABLE or ytmusic is None:
        return {"success": True, "data": []}
    try:
        # Try charts endpoint first
        try:
            charts = ytmusic.get_charts(country="US")
            trending_items = []
            # get_charts returns different structures depending on ytmusicapi version
            if isinstance(charts, dict):
                for key in ("songs", "trending", "videos"):
                    section = charts.get(key)
                    if isinstance(section, dict):
                        trending_items = section.get("items") or []
                    elif isinstance(section, list):
                        trending_items = section
                    if trending_items:
                        break

            if trending_items:
                songs = [_normalize_song(item) for item in trending_items[:20]]
                songs = [s for s in songs if s.get("id")]
                if songs:
                    return {"success": True, "data": songs}
        except Exception as e:
            logger.warning(f"get_charts failed: {e}")

        # Fallback: search for popular music
        raw = ytmusic.search("top hits 2024", filter="songs", limit=20) or []
        songs = [_normalize_song(r) for r in raw[:20]]
        songs = [s for s in songs if s.get("id")]
        return {"success": True, "data": songs}

    except Exception as e:
        logger.warning(f"get_trending failed: {e}")
        return {"success": False, "message": str(e)}


# ---------------------------------------------------------------------------
# Health check (useful for debugging deployment)
# ---------------------------------------------------------------------------

def health_check() -> dict:
    """Return system status for debugging."""
    status = {
        "ytmusicapi_installed": YTMusic is not None,
        "ytmusicapi_initialized": ytmusic is not None,
        "ytdlp_installed": _YTDLP_AVAILABLE,
    }

    if _YTDLP_AVAILABLE and yt_dlp:
        try:
            status["ytdlp_version"] = yt_dlp.version.__version__
        except Exception:
            status["ytdlp_version"] = "unknown"

    # Quick smoke test
    if ytmusic:
        try:
            r = ytmusic.search("hello", filter="songs", limit=1)
            status["ytmusic_search_works"] = bool(r and len(r) > 0)
        except Exception as e:
            status["ytmusic_search_works"] = False
            status["ytmusic_search_error"] = str(e)

    return {"success": True, "data": status}