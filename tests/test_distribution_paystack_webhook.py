"""Regression tests for signed, one-time distribution payment callbacks."""

import hashlib
import hmac
import json
import os
import sys
import types
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
        "GOOGLE_API_KEY": "unit-test-google-api-key",
    }
)

import supabase

supabase.create_client = lambda *_args, **_kwargs: None

from fastapi import HTTPException

from app.agent_distro.models import DistributionRelease, ReleaseStatus

# Keep webhook tests independent from the external Gemini client initialized by
# the distribution pipeline module.
service_stub = types.ModuleType("app.agent_distro.service")
service_stub.run_autonomous_agent_pipeline = lambda *_args, **_kwargs: None
sys.modules["app.agent_distro.service"] = service_stub

from app.agent_distro.router import paystack_secure_webhook


class FakeRequest:
    def __init__(self, body):
        self._body = body

    async def body(self):
        return self._body


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self.reference = None

    def filter(self, criterion):
        self.reference = criterion.right.value
        return self

    def with_for_update(self):
        self.db.row_locks += 1
        return self

    def first(self):
        if self.model is not DistributionRelease:
            raise AssertionError(f"Unexpected query model: {self.model}")
        if self.db.release.paystack_reference == self.reference:
            return self.db.release
        return None


class FakeSession:
    def __init__(self, release):
        self.release = release
        self.row_locks = 0
        self.commits = 0

    def query(self, model):
        return FakeQuery(self, model)

    def commit(self):
        self.commits += 1


class DistributionPaystackWebhookTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.release = SimpleNamespace(
            id="release-123",
            track_id="track-456",
            paystack_reference="paystack-ref-789",
            status=ReleaseStatus.PENDING_PAYMENT,
        )
        self.db = FakeSession(self.release)

    def _signed_request(self, payment):
        body = json.dumps({"event": "charge.success", "data": payment}).encode()
        signature = hmac.new(
            b"sk_test_unit_test_key", body, hashlib.sha512
        ).hexdigest()
        return FakeRequest(body), signature

    def _payment(self, **overrides):
        payment = {
            "reference": "paystack-ref-789",
            "status": "success",
            "amount": 500000,
            "currency": "NGN",
            "metadata": {"release_id": "release-123", "track_id": "track-456"},
        }
        payment.update(overrides)
        return payment

    async def test_rejects_invalid_signature_before_database_access(self):
        request = FakeRequest(b'{"event":"charge.success","data":{}}')

        with self.assertRaises(HTTPException) as raised:
            await paystack_secure_webhook(request, "invalid", self.db)

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(self.db.row_locks, 0)

    async def test_mismatched_amount_does_not_advance_release(self):
        request, signature = self._signed_request(self._payment(amount=1))

        with patch("app.agent_distro.router.run_autonomous_agent_pipeline") as pipeline:
            result = await paystack_secure_webhook(request, signature, self.db)

        self.assertEqual(result["status"], "event_acknowledged")
        self.assertEqual(self.release.status, ReleaseStatus.PENDING_PAYMENT)
        self.assertEqual(self.db.commits, 0)
        pipeline.assert_not_called()

    async def test_duplicate_success_callback_runs_pipeline_once(self):
        request, signature = self._signed_request(self._payment())

        with patch("app.agent_distro.router.run_autonomous_agent_pipeline") as pipeline:
            await paystack_secure_webhook(request, signature, self.db)
            await paystack_secure_webhook(request, signature, self.db)

        self.assertEqual(self.release.status, ReleaseStatus.PAYMENT_RECEIVED)
        self.assertEqual(self.db.commits, 1)
        self.assertEqual(self.db.row_locks, 2)
        pipeline.assert_called_once_with("release-123", self.db)


if __name__ == "__main__":
    unittest.main()
