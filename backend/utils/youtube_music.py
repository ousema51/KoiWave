"""
Simple, test.py-style youtube music helper.
- Uses ytmusicapi.search(..., filter='songs') for music-only search results.
- Uses yt_dlp to extract a direct audio URL for a given YouTube video id.

This implementation intentionally avoids cookie/consent logic and mirrors the working
`test.py` flow you provided.
"""

try:
    from ytmusicapi import YTMusic
    _YT_AVAILABLE = True
except Exception as _e:
    print(f"[youtube_music] ytmusicapi not available: {_e}", flush=True)
    YTMusic = None
    _YT_AVAILABLE = False

try:
    import yt_dlp
    _YTDLP_AVAILABLE = True
except Exception as _e:
    print(f"[youtube_music] yt_dlp not available: {_e}", flush=True)
    yt_dlp = None
    _YTDLP_AVAILABLE = False

import requests
import os

# Initialize YTMusic client if available
ytmusic = None
if _YT_AVAILABLE:
    try:
        ytmusic = YTMusic()
    except Exception as _e:
        print(f"[youtube_music] YTMusic() init failed: {_e}", flush=True)
        ytmusic = None
        _YT_AVAILABLE = False


def _normalize_song_entry(r):
    return {
        "id": r.get("videoId") or r.get("browseId") or r.get("video_id") or r.get("id"),
        "title": r.get("title"),
        "artist": (r.get("artists") and len(r.get("artists")) > 0 and r.get("artists")[0].get("name")) or r.get("uploader") or None,
        "duration": r.get("duration"),
        "thumbnail": (r.get("thumbnails") and len(r.get("thumbnails")) > 0 and r.get("thumbnails")[-1].get("url")) or r.get("thumbnail") or None,
    }


def search_songs(query, page=1, limit=20):
    """Return music-only search results (list) in a consistent format.
    Mirrors test.py behavior: use ytmusicapi.search(filter='songs').
    """
    try:
        results = []
        if ytmusic:
            raw = ytmusic.search(query, filter="songs") or []
            start = max(0, (page - 1) * limit)
            end = start + limit
            for r in raw[start:end]:
                results.append(_normalize_song_entry(r))
        else:
            # If ytmusicapi is not available, return empty list (caller handles it)
            results = []
        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_stream_url(video_id):
    """Extract a playable audio URL for a YouTube video id using yt-dlp.

    This follows the `test.py` flow: build the watch URL, run yt_dlp.extract_info(..., download=False)
    and return `info['url']` when available. If not present, try to select an audio format.
    """
    if not _YTDLP_AVAILABLE or yt_dlp is None:
        return {"success": False, "message": "yt_dlp not available on server"}

    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {"format": "bestaudio", "quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Direct URL (works for many videos)
        if info is None:
            return {"success": False, "message": "yt-dlp returned no info"}

        stream = info.get("url")
        if stream:
            return {"success": True, "data": {"stream_url": stream}}

        # Otherwise pick a best audio format from formats
        formats = info.get("formats") or info.get("requested_formats") or []
        if formats:
            # Prefer audio-only formats with highest abr
            best = None
            best_abr = -1
            for f in formats:
                abr = f.get("abr") or f.get("tbr") or 0
                vcodec = f.get("vcodec")
                acodec = f.get("acodec")
                is_audio_only = (vcodec in (None, "none", "unknown") or vcodec == "none") and acodec not in (None, "none")
                score = int(abr) if abr else 0
                if is_audio_only:
                    score += 10000
                if score > best_abr:
                    best_abr = score
                    best = f
            if best and best.get("url"):
                return {"success": True, "data": {"stream_url": best.get("url")}}

        return {"success": False, "message": "Could not resolve stream URL"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_song_by_id(video_id):
    """Return song metadata and attempt to include a stream_url when possible."""
    try:
        meta = {"id": video_id}
        # Try to fetch metadata via ytmusicapi if available
        if ytmusic:
            # ytmusic.get_song is not always available; search for the id
            results = ytmusic.search(video_id, filter="songs") or []
            if results:
                r = results[0]
                meta.update(_normalize_song_entry(r))
        # Try to attach a stream URL (best-effort)
        stream_res = get_stream_url(video_id)
        if stream_res.get("success"):
            meta["stream_url"] = stream_res["data"]["stream_url"]
        return {"success": True, "data": meta}
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_stream_from_search(query, index=0):
    """Search for a music result (ytmusicapi) and return a stream URL for the chosen index."""
    if not ytmusic:
        return {"success": False, "message": "ytmusicapi not available"}
    try:
        results = ytmusic.search(query, filter="songs") or []
        if not results:
            return {"success": False, "message": "No song results found"}
        chosen = results[index] if index < len(results) else results[0]
        vid = chosen.get("videoId")
        if not vid:
            return {"success": False, "message": "No videoId found for chosen song"}
        return get_stream_url(vid)
    except Exception as e:
        return {"success": False, "message": str(e)}


# minimal stubs to satisfy routes

def search_all(query):
    return search_songs(query)


def search_albums(query, page=1, limit=20):
    return {"success": True, "data": []}


def search_artists(query, page=1, limit=20):
    return {"success": True, "data": []}


def get_album_by_id(album_id):
    return {"success": True, "data": None}


def get_artist_by_id(artist_id):
    return {"success": True, "data": None}


def get_trending():
    if not ytmusic:
        return {"success": True, "data": []}
    try:
        results = ytmusic.search("top hits", filter="songs") or []
        songs = []
        for r in results[:20]:
            songs.append(_normalize_song_entry(r))
        return {"success": True, "data": songs}
    except Exception as e:
        return {"success": False, "message": str(e)}
