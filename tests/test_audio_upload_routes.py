"""All track upload endpoints share the same audio validation errors."""

import io
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
import supabase
from starlette.datastructures import Headers

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "unit-test-supabase-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "unit-test-secret")
os.environ.setdefault("MASTER_ADMIN_EMAIL", "admin@example.test")
os.environ.setdefault("MASTER_ADMIN_PASSWORD", "unit-test-password")
os.environ.setdefault("SMTP_USER", "smtp@example.test")
os.environ.setdefault("SMTP_PASSWORD", "unit-test-password")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.test")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "unit-test-paystack-key")

with patch.object(supabase, "create_client", return_value=None):
    from app.services import track_media
    from app.routers import album as album_router
    from app.routers import artist as artist_router
    from app.routers import track as track_router


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args):
        return self

    def first(self):
        return self.result


class FakeDB:
    def query(self, *_args):
        return FakeQuery(SimpleNamespace(
            id="album-1", artist_id="artist-1", cover_image=""
        ))


class AudioUploadRouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.artist = SimpleNamespace(id="artist-1", role="artist")
        self.db = FakeDB()

    @staticmethod
    def _upload(content_type, contents):
        return UploadFile(
            filename="upload.bin",
            file=io.BytesIO(contents),
            headers=Headers({"content-type": content_type}),
        )

    async def _invoke_route(self, route_name, content_type, contents):
        audio = self._upload(content_type, contents)
        if route_name == "track":
            with patch.object(track_router, "is_feature_enabled", return_value=False):
                return await track_router.upload_track(
                    title="Test track",
                    genre="Afrobeats",
                    duration=0,
                    audio=audio,
                    album_id=None,
                    cover=None,
                    price=0,
                    is_for_sale=False,
                    db=self.db,
                    current_user=self.artist,
                )
        if route_name == "artist":
            return await artist_router.upload_track(
                title="Test track",
                audio=audio,
                cover=None,
                price=0,
                is_for_sale=False,
                db=self.db,
                current_user=self.artist,
            )
        return await album_router.upload_track_to_album(
            album_id="album-1",
            title="Test track",
            genre="Afrobeats",
            price=0,
            audio_file=audio,
            db=self.db,
            current_user=self.artist,
        )

    async def test_all_upload_routes_return_the_same_unsupported_format_error(self):
        expected = "Unsupported audio format. Upload an MP3, WAV, FLAC, or OGG file."
        for route_name in ("track", "artist", "album"):
            with self.subTest(route=route_name):
                with self.assertRaises(HTTPException) as raised:
                    await self._invoke_route(route_name, "video/mp4", b"not audio")
                self.assertEqual(raised.exception.status_code, 400)
                self.assertEqual(raised.exception.detail, expected)

    async def test_all_upload_routes_return_the_same_empty_file_error(self):
        expected = "The audio file is empty. Choose a non-empty audio file and try again."
        for route_name in ("track", "artist", "album"):
            with self.subTest(route=route_name):
                with self.assertRaises(HTTPException) as raised:
                    await self._invoke_route(route_name, "audio/mpeg", b"")
                self.assertEqual(raised.exception.status_code, 400)
                self.assertEqual(raised.exception.detail, expected)

    async def test_all_upload_routes_reject_non_audio_content_with_audio_mime_type(self):
        expected = (
            "File contents do not match the selected audio format. "
            "Upload a valid MP3, WAV, FLAC, or OGG file."
        )
        for route_name in ("track", "artist", "album"):
            with self.subTest(route=route_name):
                with self.assertRaises(HTTPException) as raised:
                    await self._invoke_route(route_name, "audio/mpeg", b"not actually an audio file")
                self.assertEqual(raised.exception.status_code, 400)
                self.assertEqual(raised.exception.detail, expected)

    async def test_all_upload_routes_enforce_the_shared_audio_size_limit(self):
        expected = "Audio file exceeds the 50 MB limit. Choose a smaller file."
        with patch.object(track_media, "MAX_AUDIO_UPLOAD_BYTES", 8):
            for route_name in ("track", "artist", "album"):
                with self.subTest(route=route_name):
                    with self.assertRaises(HTTPException) as raised:
                        await self._invoke_route(route_name, "audio/mpeg", b"123456789")
                    self.assertEqual(raised.exception.status_code, 413)
                    self.assertEqual(raised.exception.detail, expected)


if __name__ == "__main__":
    unittest.main()
