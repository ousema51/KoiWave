import os
import sys
import unittest
from unittest.mock import patch

from flask import Flask


BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from routes.music import music_bp
from routes import music as music_routes


class MusicStreamJsonRouteTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(music_bp, url_prefix="/api/music")
        app.testing = True
        self.client = app.test_client()

    def test_stream_by_video_id_normalizes_payload(self):
        mocked = {
            "success": True,
            "data": {
                "url": "https://audio.example.com/stream.m4a",
                "headers": {"X-Test": 123},
                "duration": "189.6",
                "title": "Example Song",
            },
        }

        with patch.object(music_routes.youtube_music, "get_stream_url", return_value=mocked):
            response = self.client.get("/api/music/stream/dQw4w9WgXcQ")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["success"], True)
        self.assertTrue(body["data"]["audio_url"].endswith("/api/music/stream-proxy/dQw4w9WgXcQ"))
        self.assertEqual(body["data"]["proxy_url"], body["data"]["audio_url"])
        self.assertEqual(body["data"]["upstream_audio_url"], "https://audio.example.com/stream.m4a")
        self.assertEqual(body["data"]["headers"], {})
        self.assertEqual(body["data"]["video_id"], "dQw4w9WgXcQ")
        self.assertEqual(body["data"]["duration"], 189)
        self.assertEqual(body["data"]["source"], "yt-dlp")

    def test_stream_by_video_id_rejects_invalid_payload(self):
        mocked = {
            "success": True,
            "data": {
                "headers": {"X-Test": "ok"},
            },
        }

        with patch.object(music_routes.youtube_music, "get_stream_url", return_value=mocked):
            response = self.client.get("/api/music/stream/dQw4w9WgXcQ")

        self.assertEqual(response.status_code, 502)
        body = response.get_json()
        self.assertEqual(body["success"], False)
        self.assertIn("Invalid stream payload", body["message"])

    def test_stream_by_query_returns_normalized_payload(self):
        mocked = {
            "success": True,
            "data": {
                "audio_url": "https://audio.example.com/query-stream.webm",
                "video_id": "abc123def45",
                "headers": {"Authorization": "token"},
                "source": "yt-dlp",
            },
        }

        with patch.object(
            music_routes.youtube_music,
            "get_stream_from_search",
            return_value=mocked,
        ):
            response = self.client.get("/api/music/stream?q=My%20Song")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["success"], True)
        self.assertTrue(body["data"]["audio_url"].endswith("/api/music/stream-proxy/abc123def45"))
        self.assertEqual(body["data"]["upstream_audio_url"], "https://audio.example.com/query-stream.webm")
        self.assertEqual(body["data"]["video_id"], "abc123def45")
        self.assertEqual(body["data"]["headers"], {})

    def test_stream_query_requires_q(self):
        response = self.client.get("/api/music/stream")
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["success"], False)
        self.assertIn("Query parameter 'q' is required", body["message"])

    def test_stream_proxy_forwards_range_and_headers(self):
        class FakeUpstreamResponse:
            def __init__(self):
                self.status_code = 206
                self.headers = {
                    "Content-Type": "audio/mp4",
                    "Content-Range": "bytes 0-5/100",
                    "Accept-Ranges": "bytes",
                    "Content-Length": "6",
                }
                self.closed = False

            def iter_content(self, chunk_size=65536):
                yield b"abc"
                yield b"def"

            def close(self):
                self.closed = True

        mocked = {
            "success": True,
            "data": {
                "audio_url": "https://audio.example.com/raw-stream.m4a",
                "headers": {
                    "Authorization": "Bearer token",
                    "Referer": "https://music.youtube.com/",
                },
                "video_id": "dQw4w9WgXcQ",
            },
        }

        fake_upstream = FakeUpstreamResponse()

        with patch.object(music_routes.youtube_music, "get_stream_url", return_value=mocked):
            with patch.object(music_routes.requests, "get", return_value=fake_upstream) as mocked_get:
                response = self.client.get(
                    "/api/music/stream-proxy/dQw4w9WgXcQ",
                    headers={"Range": "bytes=0-5"},
                )

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.data, b"abcdef")
        self.assertEqual(response.headers.get("Content-Range"), "bytes 0-5/100")

        args, kwargs = mocked_get.call_args
        self.assertEqual(args[0], "https://audio.example.com/raw-stream.m4a")
        self.assertEqual(kwargs["headers"]["Range"], "bytes=0-5")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer token")


if __name__ == "__main__":
    unittest.main()
