"""Regression tests for payout balance reservations."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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

# Register every model referenced by User relationships before constructing ORM rows.
from app.models import album, follow, like, lyrics, payment, play, track  # noqa: F401
from app.models.payout import PayoutStatus
from app.models.user import User
from app.services.wallet import create_payout_request


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def filter(self, *_criteria):
        return self

    def with_for_update(self):
        self.db.user_row_locks += 1
        return self

    def first(self):
        return self.db.user

    def scalar(self):
        return sum(
            payout.amount
            for payout in self.db.payouts
            if payout.status in (PayoutStatus.PENDING, PayoutStatus.APPROVED, PayoutStatus.COMPLETED)
        )


class FakeSession:
    def __init__(self, user):
        self.user = user
        self.payouts = []
        self.user_row_locks = 0
        self.commits = 0

    def query(self, model):
        return FakeQuery(self, model)

    def add(self, payout):
        self.payouts.append(payout)

    def commit(self):
        self.commits += 1


class PayoutReservationTests(unittest.TestCase):
    def test_second_request_cannot_reserve_funds_twice(self):
        user = SimpleNamespace(id="artist-1", balance_ngn=100.0)
        db = FakeSession(user)

        with patch("app.services.wallet.calculate_artist_earnings", return_value=0.0):
            first, first_error = create_payout_request(user.id, 80.0, db)
            second, second_error = create_payout_request(user.id, 80.0, db)

        self.assertIsNone(first_error)
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertIn("Insufficient funds", second_error)
        self.assertEqual(len(db.payouts), 1)
        self.assertEqual(db.user_row_locks, 2)
        self.assertEqual(db.commits, 1)

    def test_in_flight_payout_keeps_balance_reserved(self):
        user = SimpleNamespace(id="artist-1", balance_ngn=100.0)
        db = FakeSession(user)
        db.payouts.append(SimpleNamespace(amount=80.0, status=PayoutStatus.APPROVED))

        with patch("app.services.wallet.calculate_artist_earnings", return_value=0.0):
            payout, error = create_payout_request(user.id, 30.0, db)

        self.assertIsNone(payout)
        self.assertIn("Insufficient funds", error)
        self.assertEqual(len(db.payouts), 1)


if __name__ == "__main__":
    unittest.main()
