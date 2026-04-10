import os
import sys
import unittest
from unittest.mock import patch


BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from utils import spotify_api


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)
        self.headers = {}

    def json(self):
        return self._payload


class SpotifyApiTests(unittest.TestCase):
    def test_spotify_get_classifies_insufficient_scope(self):
        forbidden_payload = {
            "error": {
                "status": 403,
                "message": "Insufficient client scope",
            }
        }

        with patch.object(
            spotify_api,
            "get_app_access_token",
            return_value={"success": True, "access_token": "token-123"},
        ):
            with patch.object(
                spotify_api.requests,
                "get",
                return_value=_FakeResponse(403, forbidden_payload),
            ):
                result = spotify_api.spotify_get("/playlists/abc")

        self.assertFalse(result["success"])
        self.assertEqual(result.get("error_code"), "spotify_insufficient_scope")
        self.assertIn("insufficient", (result.get("detail") or "").lower())

    def test_fetch_playlist_with_tracks_retries_with_compact_track_request(self):
        calls = []

        def fake_spotify_get(path_or_url, access_token=None, params=None, allow_refresh=True):
            calls.append({"path": path_or_url, "params": params})

            if len(calls) == 1:
                return {
                    "success": True,
                    "data": {
                        "id": "playlist123",
                        "name": "Public Playlist",
                        "description": "Demo",
                        "public": True,
                        "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist123"},
                        "owner": {"display_name": "Spotify", "id": "spotify"},
                        "images": [{"url": "https://img.example.com/cover.jpg"}],
                        "tracks": {"total": 1},
                    },
                }

            if len(calls) == 2:
                return {
                    "success": False,
                    "error_code": "spotify_insufficient_scope",
                    "message": "Insufficient scope",
                    "status_code": 403,
                }

            if len(calls) == 3:
                return {
                    "success": True,
                    "data": {
                        "items": [
                            {
                                "track": {
                                    "id": "track-1",
                                    "name": "Song 1",
                                    "artists": [{"name": "Artist A"}],
                                    "duration_ms": 200000,
                                    "external_urls": {"spotify": "https://open.spotify.com/track/track-1"},
                                    "album": {
                                        "name": "Album A",
                                        "images": [{"url": "https://img.example.com/song.jpg"}],
                                    },
                                    "is_local": False,
                                    "is_playable": True,
                                }
                            }
                        ],
                        "total": 1,
                        "next": None,
                    },
                }

            return {"success": False, "error_code": "unexpected", "message": "Unexpected call"}

        with patch.object(spotify_api, "spotify_get", side_effect=fake_spotify_get):
            result = spotify_api.fetch_playlist_with_tracks("playlist123")

        self.assertTrue(result.get("success"))
        self.assertEqual(len(result.get("tracks") or []), 1)

        self.assertGreaterEqual(len(calls), 3)
        self.assertIn("fields", calls[1]["params"])
        self.assertEqual(calls[2]["params"].get("additional_types"), "track")
        self.assertNotIn("fields", calls[2]["params"])


if __name__ == "__main__":
    unittest.main()
