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
        self._env_patcher = patch.dict(
            os.environ,
            {
                "YTDLP_PROVIDER": "",
                "YTDLP_RAPIDAPI_KEY": "",
                "RAPIDAPI_KEY": "",
                "YTDLP_ALLOW_LOCAL_FALLBACK": "",
                "YTDLP_DISABLE_EMBEDDED_RAPIDAPI_KEY": "1",
            },
            clear=False,
        )
        self._env_patcher.start()

    def tearDown(self):
        self._env_patcher.stop()

    def test_get_stream_url_returns_error_when_external_provider_disabled(self):
        with patch.dict(
            os.environ,
            {
                "YTDLP_PROVIDER": "",
                "YTDLP_RAPIDAPI_KEY": "",
                "RAPIDAPI_KEY": "",
                "YTDLP_DISABLE_EMBEDDED_RAPIDAPI_KEY": "1",
            },
            clear=False,
        ):
            result = youtube_music.get_stream_url("GwrLUr01NOY")

        self.assertFalse(result["success"])
        self.assertEqual(result.get("error_code"), "external_disabled")
        self.assertIn("external provider", result.get("message", "").lower())

    def test_get_stream_url_uses_external_api_when_enabled(self):
        external_success = {
            "success": True,
            "data": {
                "audio_url": "https://rapidapi.example/stream.webm",
                "headers": {},
                "video_id": "GwrLUr01NOY",
                "source": "rapidapi-yt-dlp",
            },
        }

        with patch.dict(os.environ, {"YTDLP_PROVIDER": "rapidapi", "YTDLP_RAPIDAPI_KEY": "key"}, clear=False):
            with patch.object(youtube_music, "_resolve_stream_from_external_api", return_value=external_success):
                with patch.object(youtube_music, "_resolve_stream_from_yt_dlp") as mocked_local:
                    with patch.object(youtube_music, "_resolve_stream_from_piped") as mocked_piped:
                        result = youtube_music.get_stream_url("GwrLUr01NOY")

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["source"], "rapidapi-yt-dlp")
        mocked_local.assert_not_called()
        mocked_piped.assert_not_called()

    def test_get_stream_url_reports_external_failure_without_local_or_piped_fallback(self):
        external_failure = {
            "success": False,
            "error_code": "external_http_error",
            "message": "RapidAPI yt-dlp returned status 500",
        }

        with patch.dict(os.environ, {"YTDLP_PROVIDER": "rapidapi", "YTDLP_RAPIDAPI_KEY": "key"}, clear=False):
            with patch.object(youtube_music, "_resolve_stream_from_external_api", return_value=external_failure):
                with patch.object(youtube_music, "_resolve_stream_from_yt_dlp") as mocked_local:
                    with patch.object(youtube_music, "_resolve_stream_from_piped") as mocked_piped:
                        result = youtube_music.get_stream_url("GwrLUr01NOY")

        self.assertFalse(result["success"])
        self.assertEqual(result.get("error_code"), "external_http_error")
        self.assertIn("status 500", result.get("message", ""))
        mocked_local.assert_not_called()
        mocked_piped.assert_not_called()

    def test_get_stream_url_uses_piped_fallback_on_region_restriction(self):
        external_failure = {
            "success": False,
            "error_code": "external_http_error",
            "status_code": 406,
            "message": "Unable to download video due to regional restrictions",
        }
        piped_success = {
            "success": True,
            "data": {
                "audio_url": "https://piped.example/audio.webm",
                "headers": {},
                "video_id": "GwrLUr01NOY",
                "source": "piped",
            },
        }

        with patch.dict(os.environ, {"YTDLP_PROVIDER": "rapidapi", "YTDLP_RAPIDAPI_KEY": "key"}, clear=False):
            with patch.object(youtube_music, "_resolve_stream_from_external_api", return_value=external_failure):
                with patch.object(youtube_music, "_resolve_stream_from_piped", return_value=piped_success) as mocked_piped:
                    with patch.object(youtube_music, "_resolve_stream_from_yt_dlp") as mocked_local:
                        result = youtube_music.get_stream_url("GwrLUr01NOY")

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["audio_url"], "https://piped.example/audio.webm")
        self.assertEqual(result["data"].get("fallback_reason"), "regional_restriction")
        self.assertEqual(result["data"].get("fallback_source"), "piped")
        mocked_piped.assert_called_once()
        mocked_local.assert_not_called()

    def test_get_stream_url_uses_piped_fallback_on_external_invalid_session_url(self):
        external_success = {
            "success": True,
            "data": {
                "audio_url": "https://robotilab.online/download-api/yt/audio?url=https://www.youtube.com/watch?v=GwrLUr01NOY",
                "headers": {},
                "video_id": "GwrLUr01NOY",
                "source": "rapidapi-yt-dlp",
            },
        }
        piped_success = {
            "success": True,
            "data": {
                "audio_url": "https://piped.example/audio.webm",
                "headers": {},
                "video_id": "GwrLUr01NOY",
                "source": "piped",
            },
        }

        with patch.dict(os.environ, {"YTDLP_PROVIDER": "rapidapi", "YTDLP_RAPIDAPI_KEY": "key"}, clear=False):
            with patch.object(youtube_music, "_resolve_stream_from_external_api", return_value=external_success):
                with patch.object(youtube_music, "_resolve_stream_from_piped", return_value=piped_success) as mocked_piped:
                    result = youtube_music.get_stream_url("GwrLUr01NOY")

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["audio_url"], "https://piped.example/audio.webm")
        self.assertEqual(result["data"].get("fallback_reason"), "external_invalid_session")
        self.assertEqual(result["data"].get("fallback_source"), "piped")
        mocked_piped.assert_called_once()

    def test_get_stream_url_uses_local_fallback_on_external_invalid_session_url_when_piped_fails(self):
        external_success = {
            "success": True,
            "data": {
                "audio_url": "https://robotilab.online/download-api/yt/audio?url=https://www.youtube.com/watch?v=GwrLUr01NOY",
                "headers": {},
                "video_id": "GwrLUr01NOY",
                "source": "rapidapi-yt-dlp",
            },
        }
        local_success = {
            "success": True,
            "data": {
                "audio_url": "https://local.example/audio.m4a",
                "headers": {},
                "video_id": "GwrLUr01NOY",
                "source": "local_yt_dlp",
            },
        }

        with patch.dict(os.environ, {"YTDLP_PROVIDER": "rapidapi", "YTDLP_RAPIDAPI_KEY": "key"}, clear=False):
            with patch.object(youtube_music, "_resolve_stream_from_external_api", return_value=external_success):
                with patch.object(
                    youtube_music,
                    "_resolve_stream_from_piped",
                    return_value={"success": False, "message": "piped unavailable"},
                ):
                    with patch.object(youtube_music, "_resolve_stream_from_yt_dlp", return_value=local_success):
                        result = youtube_music.get_stream_url("GwrLUr01NOY")

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["audio_url"], "https://local.example/audio.m4a")
        self.assertEqual(result["data"].get("fallback_reason"), "external_invalid_session")
        self.assertEqual(result["data"].get("fallback_source"), "local_yt_dlp")

    def test_get_stream_from_search_skips_region_restricted_candidate(self):
        with patch.object(
            youtube_music,
            "search_songs",
            return_value={
                "success": True,
                "data": [
                    {"id": "GwrLUr01NOY", "title": "Blocked Candidate"},
                    {"id": "Ckom3gf57Yw", "title": "Playable Candidate"},
                ],
            },
        ):
            with patch.object(
                youtube_music,
                "get_stream_url",
                side_effect=[
                    {
                        "success": False,
                        "error_code": "external_http_error",
                        "status_code": 406,
                        "message": "Unable to download video due to regional restrictions",
                    },
                    {
                        "success": True,
                        "data": {
                            "audio_url": "https://cdn.example.com/ok.mp3",
                            "video_id": "Ckom3gf57Yw",
                            "source": "rapidapi-yt-dlp",
                        },
                    },
                ],
            ) as mocked_get_stream:
                result = youtube_music.get_stream_from_search("query")

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["video_id"], "Ckom3gf57Yw")
        self.assertEqual(mocked_get_stream.call_count, 2)

    def test_get_stream_from_search_uses_search_then_external_by_id(self):
        with patch.object(
            youtube_music,
            "search_songs",
            return_value={
                "success": True,
                "data": [{"id": "GwrLUr01NOY", "title": "Any Song"}],
            },
        ):
            with patch.object(
                youtube_music,
                "get_stream_url",
                return_value={
                    "success": True,
                    "data": {
                        "audio_url": "https://rapidapi.example/out.mp3",
                        "video_id": "GwrLUr01NOY",
                        "source": "rapidapi-yt-dlp",
                    },
                },
            ) as mocked_get_stream:
                result = youtube_music.get_stream_from_search("some query")

        self.assertTrue(result["success"])
        mocked_get_stream.assert_called_once_with("GwrLUr01NOY")

    def test_resolve_stream_from_external_api_post_id_flow(self):
        class FakeResponse:
            def __init__(self, status_code, payload):
                self.status_code = status_code
                self._payload = payload
                self.text = str(payload)

            def json(self):
                return self._payload

        post_payload = {
            "videoId": "GwrLUr01NOY",
            "title": "Demo Song",
            "lengthSeconds": "180",
            "linkStream": "https://cdn.example.com/audio.m4a",
            "linkDownload": "https://cdn.example.com/audio-download.m4a",
            "error": False,
        }

        with patch.dict(
            os.environ,
            {
                "YTDLP_PROVIDER": "rapidapi",
                "YTDLP_RAPIDAPI_KEY": "key",
                "YTDLP_RAPIDAPI_HOST": "youtube-mp3-2025.p.rapidapi.com",
                "YTDLP_RAPIDAPI_URL": "https://youtube-mp3-2025.p.rapidapi.com/v1/social/youtube/audio",
            },
            clear=False,
        ):
            with patch.object(youtube_music.requests, "post", return_value=FakeResponse(200, post_payload)) as mocked_post:
                result = youtube_music._resolve_stream_from_external_api("GwrLUr01NOY")

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["audio_url"], "https://cdn.example.com/audio.m4a")
        self.assertEqual(result["data"]["external_method"], "POST")
        self.assertEqual(result["data"]["title"], "Demo Song")
        self.assertEqual(result["data"]["duration"], 180)

        _, kwargs = mocked_post.call_args
        self.assertEqual(kwargs.get("json", {}).get("id"), "GwrLUr01NOY")
        self.assertIsNone(kwargs.get("params"))

    def test_resolve_stream_from_external_api_provider_error_payload(self):
        class FakeResponse:
            def __init__(self, status_code, payload):
                self.status_code = status_code
                self._payload = payload
                self.text = str(payload)

            def json(self):
                return self._payload

        payload = {
            "error": True,
            "message": {
                "status": 400,
                "body": "Bad id",
            },
        }

        with patch.dict(
            os.environ,
            {
                "YTDLP_PROVIDER": "rapidapi",
                "YTDLP_RAPIDAPI_KEY": "key",
                "YTDLP_RAPIDAPI_HOST": "youtube-mp3-2025.p.rapidapi.com",
                "YTDLP_RAPIDAPI_URL": "https://youtube-mp3-2025.p.rapidapi.com/v1/social/youtube/audio",
            },
            clear=False,
        ):
            with patch.object(youtube_music.requests, "post", return_value=FakeResponse(200, payload)):
                result = youtube_music._resolve_stream_from_external_api("https://www.youtube.com/watch?v=Ckom3gf57Yw")

        self.assertFalse(result["success"])
        self.assertEqual(result.get("error_code"), "external_provider_error")
        self.assertIn("Bad id", result.get("message", ""))

    def test_resolve_stream_from_external_api_uses_backup_key_on_quota_limit(self):
        class FakeResponse:
            def __init__(self, status_code, payload, headers=None):
                self.status_code = status_code
                self._payload = payload
                self.text = str(payload)
                self.headers = headers or {}

            def json(self):
                return self._payload

        quota_payload = {
            "error": True,
            "message": {
                "status": 429,
                "body": "You have exceeded the MONTHLY quota",
            },
        }
        success_payload = {
            "videoId": "GwrLUr01NOY",
            "title": "Recovered Song",
            "lengthSeconds": "181",
            "linkStream": "https://cdn.example.com/recovered.m4a",
            "error": False,
        }

        with patch.dict(
            os.environ,
            {
                "YTDLP_PROVIDER": "rapidapi",
                "YTDLP_RAPIDAPI_KEYS": "first-key,second-key",
                "YTDLP_DISABLE_EMBEDDED_RAPIDAPI_KEY": "1",
            },
            clear=False,
        ):
            with patch.object(
                youtube_music.requests,
                "post",
                side_effect=[
                    FakeResponse(429, quota_payload, {"X-RateLimit-Requests-Remaining": "0"}),
                    FakeResponse(200, success_payload),
                ],
            ) as mocked_post:
                result = youtube_music._resolve_stream_from_external_api("GwrLUr01NOY")

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["audio_url"], "https://cdn.example.com/recovered.m4a")
        self.assertEqual(mocked_post.call_count, 2)
        self.assertEqual(mocked_post.call_args_list[0].kwargs["headers"]["x-rapidapi-key"], "first-key")
        self.assertEqual(mocked_post.call_args_list[1].kwargs["headers"]["x-rapidapi-key"], "second-key")

    def test_resolve_stream_from_external_api_returns_quota_exhausted_when_all_keys_limited(self):
        class FakeResponse:
            def __init__(self, status_code, payload, headers=None):
                self.status_code = status_code
                self._payload = payload
                self.text = str(payload)
                self.headers = headers or {}

            def json(self):
                return self._payload

        quota_payload = {
            "error": True,
            "message": {
                "status": 429,
                "body": "You have exceeded the MONTHLY quota",
            },
        }

        with patch.dict(
            os.environ,
            {
                "YTDLP_PROVIDER": "rapidapi",
                "YTDLP_RAPIDAPI_KEYS": "first-key,second-key",
                "YTDLP_DISABLE_EMBEDDED_RAPIDAPI_KEY": "1",
            },
            clear=False,
        ):
            with patch.object(
                youtube_music.requests,
                "post",
                side_effect=[
                    FakeResponse(429, quota_payload, {"X-RateLimit-Requests-Remaining": "0"}),
                    FakeResponse(429, quota_payload, {"X-RateLimit-Requests-Remaining": "0"}),
                ],
            ) as mocked_post:
                result = youtube_music._resolve_stream_from_external_api("GwrLUr01NOY")

        self.assertFalse(result["success"])
        self.assertEqual(result.get("error_code"), "external_quota_exhausted")
        self.assertEqual(mocked_post.call_count, 2)


if __name__ == "__main__":
    unittest.main()
