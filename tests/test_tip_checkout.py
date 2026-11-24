"""Tests for public tip checkout initialization without contacting Paystack."""

import os
import unittest
from decimal import Decimal
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

from fastapi import HTTPException
from app.models.fanlink import FanLink
from app.models.transaction import Transaction
from app.routers.billing import TipCheckoutRequest, initialize_fanlink_tip


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self.slug = None

    def filter(self, criterion):
        self.slug = criterion.right.value
        return self

    def first(self):
        if self.model is not FanLink:
            raise AssertionError(f"Unexpected query model: {self.model}")
        return self.db.fanlink if self.db.fanlink.slug == self.slug else None


class FakeSession:
    def __init__(self, fanlink):
        self.fanlink = fanlink
        self.rows = []
        self.commits = 0

    def query(self, model):
        return FakeQuery(self, model)

    def add(self, row):
        self.rows.append(row)

    def commit(self):
        self.commits += 1


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakePaystackClient:
    def __init__(self, payload):
        self.payload = payload
        self.request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, _url, *, json, headers):
        self.request = {"payload": json, "headers": headers}
        return FakeResponse(self.payload)


class TipCheckoutTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fanlink = SimpleNamespace(
            slug="artist-link", artist_id="artist-1", track_id="track-1", accept_tips=True
        )
        self.db = FakeSession(self.fanlink)
        self.client = FakePaystackClient(
            {
                "status": True,
                "data": {
                    "reference": "VG-TIP-TEST",
                    "authorization_url": "https://checkout.example.test/123",
                },
            }
        )

    async def test_initializes_ngn_checkout_and_stores_reference_first(self):
        checkout = TipCheckoutRequest(email="fan@example.com", amount_ngn=Decimal("125.50"))
        self.client.payload["data"]["reference"] = "VG-TIP-TEST"

        with patch("app.routers.billing.uuid.uuid4") as uuid4, patch(
            "app.routers.billing.httpx.AsyncClient", return_value=self.client
        ):
            uuid4.return_value.hex = "test"
            result = await initialize_fanlink_tip("artist-link", checkout, self.db)

        self.assertEqual(result["reference"], "VG-TIP-TEST")
        self.assertEqual(self.client.request["payload"]["amount"], 12550)
        self.assertEqual(self.client.request["payload"]["currency"], "NGN")
        self.assertEqual(self.client.request["payload"]["metadata"]["artist_id"], "artist-1")
        self.assertEqual(len(self.db.rows), 1)
        self.assertIsInstance(self.db.rows[0], Transaction)
        self.assertEqual(self.db.rows[0].status, "pending")
        self.assertEqual(self.db.commits, 1)

    async def test_rejects_disabled_tipping_before_calling_paystack(self):
        self.fanlink.accept_tips = False
        checkout = TipCheckoutRequest(email="fan@example.com", amount_ngn=Decimal("100"))
        with patch("app.routers.billing.httpx.AsyncClient", return_value=self.client) as client:
            with self.assertRaises(HTTPException) as raised:
                await initialize_fanlink_tip("artist-link", checkout, self.db)

        self.assertEqual(raised.exception.status_code, 404)
        client.assert_not_called()
        self.assertEqual(self.db.rows, [])


if __name__ == "__main__":
    unittest.main()
