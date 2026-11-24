"""Regression tests for one-time artist verification payment processing."""

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

from app.models.transaction import TransactionType
from app.models.user import User
from app.routers.billing import _grant_or_extend_verification


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self.value = None

    def filter(self, criterion):
        self.value = criterion.right.value
        return self

    def with_for_update(self):
        return self

    def first(self):
        if self.model is User:
            return self.db.user if self.db.user.id == self.value else None
        return self.db.transactions.get(self.value)


class FakeSession:
    def __init__(self, user, transaction):
        self.user = user
        self.transactions = {transaction.reference: transaction}
        self.commits = 0

    def query(self, model):
        return FakeQuery(self, model)

    def add(self, transaction):
        self.transactions[transaction.reference] = transaction

    def commit(self):
        self.commits += 1


class VerificationPaymentIdempotencyTests(unittest.TestCase):
    def test_repeated_callback_grants_subscription_once(self):
        user = SimpleNamespace(
            id="artist-1",
            subscription_expiry=None,
            is_verified_artist=False,
            verification_fee_paid=False,
            verified_at=None,
        )
        transaction = SimpleNamespace(
            reference="VG-VER-REFERENCE",
            user_id=user.id,
            type=TransactionType.PURCHASE,
            description="artist_verification:monthly",
            amount=7000,
            status="pending",
        )
        db = FakeSession(user, transaction)

        self.assertTrue(
            _grant_or_extend_verification(db, user, "monthly", 700000, transaction.reference)
        )
        first_expiry = user.subscription_expiry
        self.assertIsNotNone(first_expiry)
        self.assertEqual(db.commits, 1)

        self.assertTrue(
            _grant_or_extend_verification(db, user, "monthly", 700000, transaction.reference)
        )
        self.assertEqual(user.subscription_expiry, first_expiry)
        self.assertEqual(db.commits, 1)
        self.assertEqual(transaction.status, "success")

    def test_mismatched_amount_does_not_record_or_grant_payment(self):
        user = SimpleNamespace(
            id="artist-1",
            subscription_expiry=None,
            is_verified_artist=False,
            verification_fee_paid=False,
            verified_at=None,
        )
        transaction = SimpleNamespace(
            reference="VG-VER-REFERENCE",
            user_id=user.id,
            type=TransactionType.PURCHASE,
            description="artist_verification:monthly",
            amount=7000,
            status="pending",
        )
        db = FakeSession(user, transaction)

        self.assertFalse(
            _grant_or_extend_verification(db, user, "monthly", 1, transaction.reference)
        )
        self.assertIsNone(user.subscription_expiry)
        self.assertEqual(transaction.status, "pending")
        self.assertEqual(db.commits, 0)

    def test_non_ngn_payment_does_not_grant_verification(self):
        user = SimpleNamespace(
            id="artist-1",
            subscription_expiry=None,
            is_verified_artist=False,
            verification_fee_paid=False,
            verified_at=None,
        )
        transaction = SimpleNamespace(
            reference="VG-VER-REFERENCE",
            user_id=user.id,
            type=TransactionType.PURCHASE,
            description="artist_verification:monthly",
            amount=7000,
            status="pending",
        )
        db = FakeSession(user, transaction)

        self.assertFalse(
            _grant_or_extend_verification(
                db, user, "monthly", 700000, transaction.reference, currency="USD"
            )
        )
        self.assertIsNone(user.subscription_expiry)
        self.assertEqual(transaction.status, "pending")
        self.assertEqual(db.commits, 0)


if __name__ == "__main__":
    unittest.main()
