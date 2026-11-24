"""Route-level regression tests for paid track streaming access."""

import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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
from app.models.user import User
from app.routers import track as track_router


class RecordingQuery:
    def __init__(self, first=None):
        self.first_result = first

    def filter(self, *_conditions):
        return self

    def first(self):
        return self.first_result

    def update(self, _values):
        return 1


class QueryField:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return self.name, "eq", other

    def __ge__(self, other):
        return self.name, "ge", other


class FakePlay:
    user_id = QueryField("user_id")
    track_id = QueryField("track_id")
    created_at = QueryField("created_at")

    def __init__(self, **values):
        self.__dict__.update(values)


class StreamDB:
    def __init__(self, track, artist, purchase=None):
        self.track = track
        self.artist = artist
        self.purchase = purchase
        self.query_calls = []
        self.track_queries = 0
        self.added = []

    def query(self, model):
        self.query_calls.append(model)
        if model is Track:
            self.track_queries += 1
            return RecordingQuery(first=self.track if self.track_queries == 1 else None)
        if model is User:
            return RecordingQuery(first=self.artist)
        if model is Purchase:
            return RecordingQuery(first=self.purchase)
        if model is track_router.Play:
            return RecordingQuery(first=None)
        raise AssertionError(f"Unexpected database query: {model!r}")

    def add(self, item):
        self.added.append(item)

    def commit(self):
        pass

    def rollback(self):
        pass

    def refresh(self, _item):
        pass


class TrackStreamAccessTests(unittest.TestCase):
    def setUp(self):
        self.track = SimpleNamespace(
            id="paid-track-1",
            artist_id="artist-1",
            is_for_sale=True,
            audio_path="private://vibegarage-paid-audio/audio/paid-track-1.mp3",
            plays=7,
        )
        self.artist = SimpleNamespace(monetization_eligible=False)

    def _stream(self, current_user, purchase=None):
        db = StreamDB(self.track, self.artist, purchase=purchase)
        with patch.object(
            track_router,
            "track_playback_url",
            side_effect=lambda _track, can_play_full: (
                "signed-full-audio" if can_play_full else "public-preview"
            ),
        ) as playback_url, patch.object(track_router, "Play", FakePlay):
            response = track_router.stream_track(
                "paid-track-1", db=db, current_user=current_user
            )
        return response, db, playback_url

    def test_unowned_listener_receives_preview_only(self):
        listener = SimpleNamespace(id="listener-1")

        response, db, playback_url = self._stream(listener)

        self.assertEqual(response["stream_url"], "public-preview")
        self.assertTrue(response["is_preview"])
        playback_url.assert_called_once_with(self.track, can_play_full=False)
        self.assertEqual(db.query_calls.count(Purchase), 1)

    def test_buyer_receives_full_audio(self):
        listener = SimpleNamespace(id="listener-1")

        response, db, playback_url = self._stream(
            listener, purchase=SimpleNamespace(track_id="paid-track-1")
        )

        self.assertEqual(response["stream_url"], "signed-full-audio")
        self.assertFalse(response["is_preview"])
        playback_url.assert_called_once_with(self.track, can_play_full=True)
        self.assertEqual(db.query_calls.count(Purchase), 1)

    def test_artist_receives_full_audio_without_purchase_lookup(self):
        artist_user = SimpleNamespace(id="artist-1")

        response, db, playback_url = self._stream(artist_user)

        self.assertEqual(response["stream_url"], "signed-full-audio")
        self.assertFalse(response["is_preview"])
        playback_url.assert_called_once_with(self.track, can_play_full=True)
        self.assertNotIn(Purchase, db.query_calls)

    def test_free_track_without_audio_returns_unavailable_without_counting_play(self):
        self.track.is_for_sale = False
        self.track.audio_path = None
        db = StreamDB(self.track, self.artist)

        with (
            patch.object(
                track_router,
                "track_playback_url",
                side_effect=RuntimeError("Track audio is not available in storage."),
            ),
            patch.object(track_router, "Play", FakePlay),
        ):
            with self.assertRaises(track_router.HTTPException) as raised:
                track_router.stream_track(
                    "paid-track-1", db=db, current_user=None
                )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(db.added, [])


if __name__ == "__main__":
    unittest.main()
