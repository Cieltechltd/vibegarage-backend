"""Tests for signed Paystack transfer status reconciliation."""

import os
import hashlib
import hmac
import json
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

from app.models.payout import PayoutStatus, PayoutRequest
from app.routers.billing import _process_transfer_event, paystack_webhook


class FakeRequest:
    def __init__(self, body, signature):
        self._body = body
        self.headers = {"x-paystack-signature": signature}

    async def body(self):
        return self._body


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def filter(self, criterion):
        self.reference = criterion.right.value
        return self

    def with_for_update(self):
        self.db.row_locks += 1
        return self

    def first(self):
        if self.model is not PayoutRequest:
            raise AssertionError(f"Unexpected query model: {self.model}")
        return self.db.payout if self.db.payout.transfer_reference == self.reference else None


class FakeSession:
    def __init__(self, payout):
        self.payout = payout
        self.row_locks = 0
        self.commits = 0

    def query(self, model):
        return FakeQuery(self, model)

    def commit(self):
        self.commits += 1


class PayoutTransferWebhookTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.payout = SimpleNamespace(
            id="payout-1",
            amount=250.0,
            status=PayoutStatus.APPROVED,
            transfer_reference="vg-payout-test-reference",
            transfer_status="pending",
        )
        self.db = FakeSession(self.payout)
        self.transfer = {
            "reference": "vg-payout-test-reference",
            "amount": 25000,
            "currency": "NGN",
        }

    def test_success_completes_payout_once(self):
        self.assertTrue(_process_transfer_event(self.db, "transfer.success", self.transfer))
        self.assertTrue(_process_transfer_event(self.db, "transfer.success", self.transfer))
        self.assertEqual(self.payout.status, PayoutStatus.COMPLETED)
        self.assertEqual(self.payout.transfer_status, "success")
        self.assertEqual(self.db.commits, 1)

    def test_failed_transfer_releases_completed_status_but_keeps_request_reserved(self):
        self.assertTrue(_process_transfer_event(self.db, "transfer.failed", self.transfer))
        self.assertEqual(self.payout.status, PayoutStatus.PENDING)
        self.assertEqual(self.payout.transfer_status, "failed")

    def test_amount_and_currency_must_match_before_status_changes(self):
        self.assertFalse(
            _process_transfer_event(self.db, "transfer.success", {**self.transfer, "amount": 1})
        )
        self.assertFalse(
            _process_transfer_event(self.db, "transfer.success", {**self.transfer, "currency": "USD"})
        )
        self.assertEqual(self.payout.status, PayoutStatus.APPROVED)
        self.assertEqual(self.db.commits, 0)

    async def test_signed_paystack_webhook_reconciles_transfer(self):
        body = json.dumps({"event": "transfer.success", "data": self.transfer}).encode()
        signature = hmac.new(
            b"sk_test_unit_test_key", body, hashlib.sha512
        ).hexdigest()

        result = await paystack_webhook(FakeRequest(body, signature), self.db)

        self.assertEqual(result["status"], "success")
        self.assertEqual(self.payout.status, PayoutStatus.COMPLETED)
        self.assertEqual(self.db.commits, 1)


if __name__ == "__main__":
    unittest.main()
