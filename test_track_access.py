"""Regression coverage for batched purchase checks in listener feeds."""

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

from app.models.playlist import Playlist
from app.models.purchase import Purchase
from app.models.track import Track
from app.models.user import User
from app.routers import daily_mix, playlists
from app.services.track_access import get_owned_track_ids


class RecordingQuery:
    def __init__(self, rows=(), first=None):
        self.rows = list(rows)
        self.first_result = first
        self.filters = []

    def filter(self, *conditions):
        self.filters.extend(conditions)
        return self

    def join(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.first_result


class PurchaseLookupDB:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.query_calls = []
        self.purchase_query = RecordingQuery(self.rows)

    def query(self, *entities):
        self.query_calls.append(entities)
        return self.purchase_query


class FeedDB:
    def __init__(self, playlist, tracks, purchased_track_ids):
        self.playlist = playlist
        self.tracks = tracks
        self.purchased_track_ids = purchased_track_ids
        self.query_calls = []

    def query(self, *entities):
        self.query_calls.append(entities)
        if len(entities) == 1 and entities[0] is Playlist:
            return RecordingQuery(first=self.playlist)
        if len(entities) == 2 and entities[0] is Track and entities[1] is User:
            return RecordingQuery(rows=self.tracks)
        if len(entities) == 1 and entities[0] is Purchase.track_id:
            return RecordingQuery(rows=[(track_id,) for track_id in self.purchased_track_ids])
        raise AssertionError(f"Unexpected database query: {entities!r}")


class BatchedTrackAccessTests(unittest.TestCase):
    def test_owned_track_lookup_uses_one_query_for_unique_ids(self):
        db = PurchaseLookupDB(rows=[("paid-2",), ("paid-1",)])

        owned = get_owned_track_ids(
            db, "listener-1", ["paid-1", "paid-2", "paid-1"]
        )

        self.assertEqual(owned, {"paid-1", "paid-2"})
        self.assertEqual(len(db.query_calls), 1)
        self.assertEqual(db.query_calls[0], (Purchase.track_id,))
        self.assertEqual(len(db.purchase_query.filters), 2)

    def test_owned_track_lookup_skips_empty_track_collection(self):
        db = PurchaseLookupDB()

        self.assertEqual(get_owned_track_ids(db, "listener-1", []), set())

        self.assertEqual(db.query_calls, [])

    def test_daily_mix_keeps_preview_and_full_access_rules(self):
        listener = SimpleNamespace(id="listener-1")
        tracks = [
            SimpleNamespace(
                id="unowned-paid",
                title="Unowned song",
                artist_id="artist-1",
                is_for_sale=True,
                artist=SimpleNamespace(stage_name="Artist", is_verified_artist=True),
                cover_path="cover.jpg",
                genre="Afrobeats",
            ),
            SimpleNamespace(
                id="owned-paid",
                title="Purchased song",
                artist_id="artist-1",
                is_for_sale=True,
                artist=SimpleNamespace(stage_name="Artist", is_verified_artist=True),
                cover_path="cover.jpg",
                genre="Afrobeats",
            ),
            SimpleNamespace(
                id="artist-paid",
                title="Artist song",
                artist_id="listener-1",
                is_for_sale=True,
                artist=SimpleNamespace(stage_name="Listener", is_verified_artist=False),
                cover_path="cover.jpg",
                genre="Afrobeats",
            ),
        ]
        db = PurchaseLookupDB(rows=[("owned-paid",)])

        with (
            patch.object(daily_mix.RecommenderService, "generate_daily_mix", return_value=tracks),
            patch.object(
                daily_mix,
                "track_playback_url",
                side_effect=lambda track, can_play_full: (
                    f"full:{track.id}" if can_play_full else f"preview:{track.id}"
                ),
            ),
        ):
            response = daily_mix.get_daily_mix(db, listener)

        self.assertEqual(len(db.query_calls), 1)
        self.assertEqual(
            [(track["id"], track["audio_url"], track["is_preview"]) for track in response["tracks"]],
            [
                ("unowned-paid", "preview:unowned-paid", True),
                ("owned-paid", "full:owned-paid", False),
                ("artist-paid", "full:artist-paid", False),
            ],
        )

    def test_playlist_uses_one_batched_purchase_query_and_preserves_access(self):
        listener = SimpleNamespace(id="listener-1")
        playlist = SimpleNamespace(
            id="playlist-1",
            user_id="listener-1",
            is_public=False,
            name="Favorites",
            cover_image=None,
        )
        artist = SimpleNamespace(
            stage_name="Artist", username="artist", is_verified_artist=True
        )
        tracks = [
            (
                SimpleNamespace(
                    id="unowned-paid",
                    title="Preview track",
                    artist_id="artist-1",
                    is_for_sale=True,
                ),
                artist,
            ),
            (
                SimpleNamespace(
                    id="owned-paid",
                    title="Purchased track",
                    artist_id="artist-1",
                    is_for_sale=True,
                ),
                artist,
            ),
            (
                SimpleNamespace(
                    id="artist-paid",
                    title="Artist track",
                    artist_id="listener-1",
                    is_for_sale=True,
                ),
                artist,
            ),
        ]
        db = FeedDB(playlist, tracks, {"owned-paid"})

        with patch.object(
            playlists,
            "track_playback_url",
            side_effect=lambda track, can_play_full: (
                f"full:{track.id}" if can_play_full else f"preview:{track.id}"
            ),
        ):
            response = playlists.get_playlist_details("playlist-1", db, listener)

        self.assertEqual(len(db.query_calls), 3)
        self.assertEqual(
            sum(
                len(entities) == 1 and entities[0] is Purchase.track_id
                for entities in db.query_calls
            ),
            1,
        )
        self.assertEqual(
            [(track["id"], track["audio_url"], track["is_preview"]) for track in response["tracks"]],
            [
                ("unowned-paid", "preview:unowned-paid", True),
                ("owned-paid", "full:owned-paid", False),
                ("artist-paid", "full:artist-paid", False),
            ],
        )


if __name__ == "__main__":
    unittest.main()
