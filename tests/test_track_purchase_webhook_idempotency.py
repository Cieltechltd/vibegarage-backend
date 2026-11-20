"""Regression tests for one-time track-purchase webhook processing."""

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

from fastapi import HTTPException

# Load models referenced by User relationships before constructing ORM records.
from app.models import album, follow, like, lyrics, payment, play, track as track_model  # noqa: F401
from app.models.earning import EarningEntry
from app.models.purchase import Purchase
from app.models.track import Track
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.routers.billing import _process_track_purchase


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
        if self.model is Transaction:
            reference = self._filter_value("reference")
            if self.db.transaction is None:
                return None
            return self.db.transaction if self.db.transaction.reference == reference else None
        if self.model is Track:
            track_id = self._filter_value("id")
            return self.db.track if str(self.db.track.id) == str(track_id) else None
        if self.model is Purchase:
            reference = self._filter_value("transaction_ref")
            return next(
                (purchase for purchase in self.db.purchases if purchase.transaction_ref == reference),
                None,
            )
        if self.model is User:
            artist_id = self._filter_value("id")
            return self.db.artist if self.db.artist.id == artist_id else None
        raise AssertionError(f"Unexpected query model: {self.model}")


class FakeSession:
    def __init__(self, transaction, track, artist):
        self.transaction = transaction
        self.track = track
        self.artist = artist
        self.purchases = []
        self.earnings = []
        self.row_locks = 0
        self.commits = 0

    def query(self, model):
        return FakeQuery(self, model)

    def add(self, row):
        if isinstance(row, Purchase):
            self.purchases.append(row)
        elif isinstance(row, EarningEntry):
            self.earnings.append(row)
        else:
            raise AssertionError(f"Unexpected row: {row}")

    def commit(self):
        self.commits += 1


class TrackPurchaseWebhookIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.reference = "VG-TRK-REFERENCE"
        self.user_id = "listener-1"
        self.track_id = "track-1"
        self.transaction = SimpleNamespace(
            reference=self.reference,
            user_id=self.user_id,
            track_id=self.track_id,
            amount=1000.0,
            type=TransactionType.PURCHASE,
            status="pending",
        )
        self.track = SimpleNamespace(id=self.track_id, artist_id="artist-1", price=1000.0)
        self.artist = SimpleNamespace(id="artist-1", balance_ngn=0.0)
        self.db = FakeSession(self.transaction, self.track, self.artist)

    def test_repeated_callback_credits_artist_once(self):
        self.assertTrue(
            _process_track_purchase(
                self.db, self.user_id, self.track_id, 100000, self.reference
            )
        )
        credited_balance = self.artist.balance_ngn

        self.assertTrue(
            _process_track_purchase(
                self.db, self.user_id, self.track_id, 100000, self.reference
            )
        )

        self.assertEqual(len(self.db.purchases), 1)
        self.assertEqual(len(self.db.earnings), 1)
        self.assertEqual(self.artist.balance_ngn, credited_balance)
        self.assertEqual(self.db.row_locks, 3)
        self.assertEqual(self.db.commits, 1)
        self.assertEqual(self.transaction.status, "success")

    def test_mismatched_amount_does_not_create_purchase_or_credit(self):
        self.assertFalse(
            _process_track_purchase(
                self.db, self.user_id, self.track_id, 1, self.reference
            )
        )

        self.assertEqual(self.db.purchases, [])
        self.assertEqual(self.db.earnings, [])
        self.assertEqual(self.artist.balance_ngn, 0.0)
        self.assertEqual(self.db.commits, 0)
        self.assertEqual(self.transaction.status, "pending")

    def test_mismatched_user_does_not_create_purchase_or_credit(self):
        self.assertFalse(
            _process_track_purchase(
                self.db, "another-listener", self.track_id, 100000, self.reference
            )
        )

        self.assertEqual(self.db.purchases, [])
        self.assertEqual(self.db.earnings, [])
        self.assertEqual(self.artist.balance_ngn, 0.0)
        self.assertEqual(self.db.commits, 0)

    def test_missing_transaction_requests_paystack_retry(self):
        self.db.transaction = None

        with self.assertRaises(HTTPException) as raised:
            _process_track_purchase(
                self.db, self.user_id, self.track_id, 100000, self.reference
            )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(self.db.purchases, [])
        self.assertEqual(self.db.earnings, [])
        self.assertEqual(self.db.commits, 0)


if __name__ == "__main__":
    unittest.main()
