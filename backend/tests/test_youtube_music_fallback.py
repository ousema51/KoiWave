import os
import sys
import unittest
from unittest.mock import patch


BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from utils import youtube_music


class YoutubeMusicFallbackTests(unittest.TestCase):
    def setUp(self):
        youtube_music._STREAM_CACHE.clear()

    def test_get_stream_url_uses_piped_when_yt_dlp_bot_challenge(self):
        ytdlp_failure = {
            "success": False,
            "error_code": "bot_challenge",
            "message": "YouTube bot challenge detected",
        }
        piped_success = {
            "success": True,
            "data": {
                "audio_url": "https://piped.example/stream.webm",
                "headers": {"Referer": "https://music.youtube.com/"},
                "video_id": "GwrLUr01NOY",
                "source": "piped",
            },
        }

        with patch.object(youtube_music, "_resolve_stream_from_yt_dlp", return_value=ytdlp_failure):
            with patch.object(youtube_music, "_resolve_stream_from_piped", return_value=piped_success):
                result = youtube_music.get_stream_url("GwrLUr01NOY")

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["source"], "piped")
        self.assertEqual(result["data"]["video_id"], "GwrLUr01NOY")

    def test_get_stream_url_reports_combined_error_when_all_extractors_fail(self):
        ytdlp_failure = {
            "success": False,
            "error_code": "bot_challenge",
            "message": "YouTube bot challenge detected",
        }
        piped_failure = {
            "success": False,
            "message": "Piped fallback failed to resolve stream",
        }

        with patch.object(youtube_music, "_resolve_stream_from_yt_dlp", return_value=ytdlp_failure):
            with patch.object(youtube_music, "_resolve_stream_from_piped", return_value=piped_failure):
                result = youtube_music.get_stream_url("GwrLUr01NOY")

        self.assertFalse(result["success"])
        self.assertEqual(result.get("error_code"), "bot_challenge")
        self.assertIn("Piped fallback error", result.get("message", ""))


if __name__ == "__main__":
    unittest.main()
