"""
YouTube Music backend — search via ytmusicapi
"""

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
    logger.error("ytmusicapi failed: {}".format(e))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_str(value):
    """Safely convert to string with UTF-8 encoding."""
    if value is None:
        return None
    if isinstance(value, str):
        # Ensure string is valid UTF-8
        try:
            value.encode('utf-8')
            return value
        except UnicodeEncodeError:
            # If encoding fails, encode with errors='replace'
            return value.encode('utf-8', errors='replace').decode('utf-8')
    return str(value)


def _get_thumbnail(r):
    """Extract thumbnail URL with fallback handling."""
    if r is None:
        return None
        
    thumbs = r.get("thumbnails")
    if isinstance(thumbs, list) and thumbs:
        url = thumbs[-1].get("url") if thumbs[-1] else None
        if url:
            url = _safe_str(url)
            # Ensure url is absolute and uses https
            if url and url.startswith("//"):
                return f"https:{url}"
            if url and url.startswith("http"):
                return url
            if url:
                return f"https:{url}"

    thumb_obj = r.get("thumbnail")
    if isinstance(thumb_obj, dict):
        inner = thumb_obj.get("thumbnails")
        if isinstance(inner, list) and inner:
            url = inner[-1].get("url") if inner[-1] else None
            if url:
                url = _safe_str(url)
                if url and url.startswith("http"):
                    return url
                if url:
                    return f"https:{url}"

    # Generate YouTube CDN thumbnail as fallback
    vid = r.get("videoId") or r.get("id")
    if vid:
        vid = _safe_str(vid)
        if vid:
            return "https://img.youtube.com/vi/{}/hqdefault.jpg".format(vid)

    return None


def _normalize(r):
    """Normalize song result from ytmusicapi with UTF-8 encoding."""
    if r is None:
        return None
        
    artists = r.get("artists") or []
    artist = None
    if artists:
        if isinstance(artists[0], dict):
            artist = artists[0].get("name")
        else:
            artist = artists[0]
    if not artist:
        artist = r.get("artist")
    
    artist = _safe_str(artist) or "Unknown Artist"

    return {
        "id": _safe_str(r.get("videoId") or r.get("id")),
        "title": _safe_str(r.get("title")) or "Unknown",
        "name": _safe_str(r.get("title")) or "Unknown",
        "artist": artist,
        "duration": r.get("duration"),
        "thumbnail": _get_thumbnail(r),
        "image": _get_thumbnail(r),
        "cover_url": _get_thumbnail(r),
    }


# ---------------------------------------------------------------------------
# Public API — Search
# ---------------------------------------------------------------------------

def search_songs(query="", page=1, limit=20):
    if not ytmusic:
        return {"success": False, "message": "ytmusicapi not available"}
    try:
        query = _safe_str(query)
        start = (page - 1) * limit
        raw = ytmusic.search(query, filter="songs", limit=start + limit) or []
        songs = []
        for r in raw[start:start + limit]:
            if r.get("videoId"):
                normalized = _normalize(r)
                if normalized:
                    songs.append(normalized)
        return {"success": True, "data": songs}
    except Exception as e:
        logger.error("Search error: {}".format(e))
        return {"success": False, "message": str(e)}


def search_all(query=""):
    return search_songs(query)


# ---------------------------------------------------------------------------
# Public API — Stream URL
# ---------------------------------------------------------------------------

PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.adminforge.de",
    "https://api.piped.yt",
    "https://pipedapi.r4fo.com",
    "https://pipedapi.leptons.xyz",
]


def get_song_by_id(video_id=""):
    """Get song metadata with UTF-8 encoding and thumbnail fallback."""
    if not video_id or not video_id.strip():
        return {"success": False, "message": "No video_id provided"}

    video_id = _safe_str(video_id.strip())
    if not video_id:
        return {"success": False, "message": "Invalid video_id"}

    meta = {
        "title": None,
        "artist": "Unknown Artist",
        "duration": None,
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
    }

    if ytmusic:
        try:
            info = ytmusic.get_song(video_id)
            vd = info.get("videoDetails") or {}
            thumbs = vd.get("thumbnail", {}).get("thumbnails") or []
            
            meta["title"] = _safe_str(vd.get("title"))
            meta["artist"] = _safe_str(vd.get("author")) or meta["artist"]
            meta["duration"] = vd.get("lengthSeconds")
            
            if thumbs:
                turl = thumbs[-1].get("url") if thumbs[-1] else None
                if turl:
                    turl = _safe_str(turl)
                    if turl:
                        if turl.startswith("//"):
                            meta["thumbnail"] = f"https:{turl}"
                        else:
                            meta["thumbnail"] = turl
        except Exception as e:
            logger.error(f"Failed to fetch song metadata: {e}")

    # Ensure title fallback is meaningful
    meta["title"] = meta["title"] or f"Unknown Title ({video_id})"
    
    # Ensure all strings are UTF-8 safe
    meta["title"] = _safe_str(meta["title"])
    meta["artist"] = _safe_str(meta["artist"])

    data = {
        "id": video_id,
        "piped_instances": PIPED_INSTANCES,
        "resolve_on_client": True,
    }
    data.update(meta)
    return {"success": True, "data": data}


# ---------------------------------------------------------------------------
# Albums / Artists / Trending
# ---------------------------------------------------------------------------

def search_albums(query="", page=1, limit=20):
    if not ytmusic:
        return {"success": True, "data": []}
    try:
        query = _safe_str(query)
        raw = ytmusic.search(query, filter="albums", limit=limit) or []
        start = (page - 1) * limit
        albums = []
        for r in raw[start:start + limit]:
            artists = r.get("artists") or [{}]
            artist_name = None
            if artists and isinstance(artists[0], dict):
                artist_name = artists[0].get("name")
            elif artists:
                artist_name = artists[0]
            
            album = {
                "id": _safe_str(r.get("browseId")),
                "title": _safe_str(r.get("title")) or "Unknown",
                "artist": _safe_str(artist_name) or "Unknown",
                "thumbnail": _get_thumbnail(r),
                "cover_url": _get_thumbnail(r),
                "image": _get_thumbnail(r),
            }
            albums.append(album)
        return {"success": True, "data": albums}
    except Exception as e:
        logger.error("Album search error: {}".format(e))
        return {"success": True, "data": []}


def search_artists(query="", page=1, limit=20):
    if not ytmusic:
        return {"success": True, "data": []}
    try:
        query = _safe_str(query)
        raw = ytmusic.search(query, filter="artists", limit=limit) or []
        start = (page - 1) * limit
        artists = []
        for r in raw[start:start + limit]:
            artist = {
                "id": _safe_str(r.get("browseId")),
                "name": _safe_str(r.get("artist")) or "Unknown",
                "thumbnail": _get_thumbnail(r),
                "image": _get_thumbnail(r),
            }
            artists.append(artist)
        return {"success": True, "data": artists}
    except Exception as e:
        logger.error("Artist search error: {}".format(e))
        return {"success": True, "data": []}


def get_album_by_id(album_id=""):
    if not ytmusic:
        return {"success": False, "message": "ytmusicapi not available"}
    try:
        album_id = _safe_str(album_id)
        album = ytmusic.get_album(album_id)
        
        artists = album.get("artists") or [{}]
        artist_name = None
        if artists and isinstance(artists[0], dict):
            artist_name = artists[0].get("name")
        elif artists:
            artist_name = artists[0]
        
        return {"success": True, "data": {
            "id": album_id,
            "title": _safe_str(album.get("title")) or "Unknown",
            "artist": _safe_str(artist_name) or "Unknown",
            "thumbnail": _get_thumbnail(album),
            "cover_url": _get_thumbnail(album),
            "image": _get_thumbnail(album),
            "tracks": [_normalize(t) for t in (album.get("tracks") or []) if t],
        }}
    except Exception as e:
        logger.error("Album get error: {}".format(e))
        return {"success": False, "message": str(e)}


def get_artist_by_id(artist_id=""):
    if not ytmusic:
        return {"success": False, "message": "ytmusicapi not available"}
    try:
        artist_id = _safe_str(artist_id)
        artist = ytmusic.get_artist(artist_id)
        
        songs = [_normalize(s) for s in (artist.get("songs", {}).get("results") or []) if s]
        
        return {"success": True, "data": {
            "id": artist_id,
            "name": _safe_str(artist.get("name")) or "Unknown",
            "thumbnail": _get_thumbnail(artist),
            "image": _get_thumbnail(artist),
            "image_url": _get_thumbnail(artist),
            "songs": songs,
        }}
    except Exception as e:
        logger.error("Artist get error: {}".format(e))
        return {"success": False, "message": str(e)}


def get_trending():
    if not ytmusic:
        return {"success": True, "data": []}
    try:
        raw = ytmusic.search("top hits USA", filter="songs", limit=40) or []
        songs = []
        for r in raw:
            if r.get("videoId"):
                normalized = _normalize(r)
                if normalized:
                    songs.append(normalized)
        return {"success": True, "data": songs[:20]}
    except Exception as e:
        logger.error("Trending error: {}".format(e))
        return {"success": True, "data": []}


def health_check():
    status = {
        "ytmusic": ytmusic is not None,
        "search": False,
        "stream_method": "client-side piped",
        "piped_instances": PIPED_INSTANCES,
    }
    if ytmusic:
        try:
            r = ytmusic.search("test", filter="songs", limit=1)
            status["search"] = bool(r)
            if r:
                thumb = _get_thumbnail(r[0])
                status["thumbnail_test"] = thumb if thumb else "null"
        except Exception as e:
            status["search_error"] = str(e)
    return {"success": True, "data": status}
