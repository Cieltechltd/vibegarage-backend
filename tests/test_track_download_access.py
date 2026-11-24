"""Route-level regression tests for paid track download access."""

import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

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
    import supabase  # noqa: F401
except ModuleNotFoundError:
    supabase_stub = types.ModuleType("supabase")
    supabase_stub.Client = object
    supabase_stub.create_client = lambda *_args, **_kwargs: None
    sys.modules["supabase"] = supabase_stub

from app.models.purchase import Purchase
from app.models.track import Track
from app.routers import track as track_router


class RecordingQuery:
    def __init__(self, first=None):
        self.first_result = first

    def filter(self, *_conditions):
        return self

    def first(self):
        return self.first_result


class FakeDownload:
    def __init__(self, **values):
        self.__dict__.update(values)


class DownloadDB:
    def __init__(self, track, purchase=None):
        self.track = track
        self.purchase = purchase
        self.added = []
        self.commit_calls = 0

    def query(self, model):
        if model is Track:
            return RecordingQuery(first=self.track)
        if model is Purchase:
            return RecordingQuery(first=self.purchase)
        raise AssertionError(f"Unexpected database query: {model!r}")

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commit_calls += 1


class TrackDownloadAccessTests(unittest.TestCase):
    def setUp(self):
        self.track = SimpleNamespace(
            id="paid-track-1",
            artist_id="artist-1",
            is_for_sale=True,
            audio_path="private://vibegarage-paid-audio/audio/paid-track-1.mp3",
        )

    def _download(self, current_user, purchase=None):
        db = DownloadDB(self.track, purchase=purchase)
        with (
            patch.object(track_router, "Download", FakeDownload),
            patch.object(
                track_router,
                "track_playback_url",
                return_value="https://example.test/signed-full-audio",
            ) as playback_url,
        ):
            response = track_router.download_track(
                "paid-track-1", db=db, current_user=current_user
            )
        return response, db, playback_url

    def test_unowned_listener_cannot_download_paid_track(self):
        listener = SimpleNamespace(id="listener-1")
        db = DownloadDB(self.track)

        with (
            patch.object(track_router, "Download", FakeDownload),
            patch.object(track_router, "track_playback_url") as playback_url,
            self.assertRaises(HTTPException) as error,
        ):
            track_router.download_track(
                "paid-track-1", db=db, current_user=listener
            )

        self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(db.added, [])
        self.assertEqual(db.commit_calls, 0)
        playback_url.assert_not_called()

    def test_buyer_can_download_paid_track(self):
        listener = SimpleNamespace(id="listener-1")

        response, db, playback_url = self._download(
            listener, purchase=SimpleNamespace(track_id="paid-track-1")
        )

        self.assertEqual(response.status_code, 307)
        self.assertEqual(
            response.headers["location"], "https://example.test/signed-full-audio"
        )
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.added[0].user_id, "listener-1")
        self.assertEqual(db.commit_calls, 1)
        playback_url.assert_called_once_with(self.track, can_play_full=True)

    def test_artist_can_download_own_paid_track(self):
        artist = SimpleNamespace(id="artist-1")

        response, db, playback_url = self._download(artist)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.added[0].user_id, "artist-1")
        self.assertEqual(db.commit_calls, 1)
        playback_url.assert_called_once_with(self.track, can_play_full=True)


if __name__ == "__main__":
    unittest.main()
