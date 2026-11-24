"""Tests for uploaded media object storage behavior."""

import os
import sys
import tempfile
import types
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.update(
    {
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "unit-test-secret",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_KEY": "unit-test-supabase-key",
        "MASTER_ADMIN_EMAIL": "admin@example.com",
        "MASTER_ADMIN_PASSWORD": "unit-test-password",
        "SMTP_USER": "smtp@example.com",
        "SMTP_PASSWORD": "unit-test-smtp-password",
        "ADMIN_EMAIL": "admin@example.com",
        "PAYSTACK_SECRET_KEY": "unit-test-paystack-key",
    }
)

try:
    import supabase
except ModuleNotFoundError:
    supabase_stub = types.ModuleType("supabase")
    supabase_stub.Client = object
    supabase_stub.create_client = lambda *_args, **_kwargs: None
    sys.modules["supabase"] = supabase_stub
    import supabase

with patch.object(supabase, "create_client", return_value=SimpleNamespace()):
    from app.services import file_storage


class FileStorageUploadTests(unittest.IsolatedAsyncioTestCase):
    def _upload_file(self):
        return SimpleNamespace(
            filename="cover.png",
            content_type="image/png",
            seek=self._async_noop,
            read=self._async_read,
        )

    async def _async_noop(self, *_args):
        return None

    async def _async_read(self):
        return b"image-bytes"

    async def test_storage_failure_does_not_return_a_broken_public_url(self):
        bucket = SimpleNamespace(upload=Mock(side_effect=OSError("offline")))
        storage = SimpleNamespace(from_=Mock(return_value=bucket))

        with patch.object(file_storage, "supabase", SimpleNamespace(storage=storage)):
            with self.assertRaisesRegex(RuntimeError, "Cloud asset storage upload failed"):
                await file_storage.save_file(self._upload_file(), "covers")

        bucket.upload.assert_called_once()

    async def test_success_returns_public_url_without_local_duplicate(self):
        bucket = SimpleNamespace(upload=Mock())
        storage = SimpleNamespace(from_=Mock(return_value=bucket))

        with tempfile.TemporaryDirectory() as local_dir:
            with (
                patch.object(file_storage, "supabase", SimpleNamespace(storage=storage)),
                patch.object(file_storage, "BASE_DIR", local_dir),
            ):
                url = await file_storage.save_file(self._upload_file(), "covers")

            self.assertEqual(os.listdir(local_dir), [])

        self.assertTrue(
            url.startswith(
                "https://example.supabase.co/storage/v1/object/public/vibegarage/"
                "app/uploads/covers/"
            )
        )
        bucket.upload.assert_called_once()


if __name__ == "__main__":
    unittest.main()
