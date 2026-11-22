"""Regression tests for safe Paystack tip processing."""

import os
import unittest
from types import SimpleNamespace

os.environ.update(
    {
        "DATABASE_URL": "sqlite://",
        "SECRET_KEY": "unit-test-secret-key",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_KEY": "unit-test-supabase-key",
        "MASTER_ADMIN_EMAIL": "admin@example.test",
        "MASTER_ADMIN_PASSWORD": "unit-test-password",
        "SMTP_USER": "mailer@example.test",
        "SMTP_PASSWORD": "unit-test-password",
        "ADMIN_EMAIL": "admin@example.test",
        "PAYSTACK_SECRET_KEY": "sk_test_unit_test_key",
    }
)

import supabase

supabase.create_client = lambda *_args, **_kwargs: None

# Load User relationship models before constructing earning records.
from app.models import album, follow, like, lyrics, payment, play, track as track_model  # noqa: F401
from app.models.earning import EarningEntry
from app.models.fanlink import FanLink
from app.models.user import User
from app.routers.billing import _process_tip


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self.filters = []

    def filter(self, *criteria):
        self.filters.extend(criteria)
        return self

    def with_for_update(self):
        self.db.row_locks += 1
        return self

    def _filter_value(self, field_name):
        for criterion in self.filters:
            if getattr(criterion.left, "key", None) == field_name:
                return criterion.right.value
        return None

    def first(self):
        if self.model is EarningEntry:
            reference = self._filter_value("reference")
            return next(
                (entry for entry in self.db.earnings if entry.reference == reference),
                None,
            )
        if self.model is FanLink:
            slug = self._filter_value("slug")
            return self.db.fanlink if self.db.fanlink.slug == slug else None
        if self.model is User:
            artist_id = self._filter_value("id")
            return self.db.artist if self.db.artist.id == artist_id else None
        raise AssertionError(f"Unexpected query model: {self.model}")


class FakeSession:
    def __init__(self, artist, fanlink):
        self.artist = artist
        self.fanlink = fanlink
        self.earnings = []
        self.advisory_locks = []
        self.row_locks = 0
        self.commits = 0

    def execute(self, statement, parameters):
        self.advisory_locks.append(parameters["reference"])

    def query(self, model):
        return FakeQuery(self, model)

    def add(self, entry):
        if not isinstance(entry, EarningEntry):
            raise AssertionError(f"Unexpected row: {entry}")
        self.earnings.append(entry)

    def commit(self):
        self.commits += 1


class TipWebhookIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.artist = SimpleNamespace(id="artist-1", balance_ngn=100.0)
        self.fanlink = SimpleNamespace(
            slug="artist-link",
            artist_id="artist-1",
            track_id="track-1",
            accept_tips=True,
        )
        self.db = FakeSession(self.artist, self.fanlink)

    def _process(self, **overrides):
        params = {
            "artist_id": "artist-1",
            "fanlink_slug": "artist-link",
            "paid_amount_kobo": 100000,
            "reference": "tip-reference-1",
            "currency": "NGN",
        }
        params.update(overrides)
        return _process_tip(self.db, **params)

    def test_duplicate_reference_credits_artist_once(self):
        self.assertTrue(self._process())
        self.assertTrue(self._process())

        self.assertEqual(self.artist.balance_ngn, 950.0)
        self.assertEqual(len(self.db.earnings), 1)
        self.assertEqual(self.db.commits, 1)
        self.assertEqual(self.db.advisory_locks, ["tip-reference-1", "tip-reference-1"])

    def test_tip_must_match_an_enabled_fanlink_and_its_artist(self):
        self.assertFalse(self._process(artist_id="artist-2"))

        self.fanlink.accept_tips = False
        self.assertFalse(self._process(reference="tip-reference-2"))

        self.assertEqual(self.artist.balance_ngn, 100.0)
        self.assertEqual(self.db.earnings, [])

    def test_rejects_invalid_amount_or_currency(self):
        self.assertFalse(self._process(paid_amount_kobo=0))
        self.assertFalse(self._process(paid_amount_kobo=-100))
        self.assertFalse(self._process(paid_amount_kobo="100000"))
        self.assertFalse(self._process(currency="USD"))

        self.assertEqual(self.db.advisory_locks, [])
        self.assertEqual(self.artist.balance_ngn, 100.0)
        self.assertEqual(self.db.earnings, [])


if __name__ == "__main__":
    unittest.main()
