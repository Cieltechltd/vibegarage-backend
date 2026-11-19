"""Focused regression tests for the password reset security flow."""

import hashlib
import os
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

# Keep imports isolated from production services and databases.
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
        "RESEND_API_KEY": "re_test_unit_test_key",
    }
)

import supabase

supabase.create_client = lambda *_args, **_kwargs: None

from fastapi import BackgroundTasks, HTTPException

from app.core import security
from app.routers.auth import forgot_password, reset_password
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest


class FakeQuery:
    def __init__(self, user):
        self.user = user

    def filter(self, *_criteria):
        return self

    def first(self):
        return self.user


class FakeSession:
    def __init__(self, user):
        self.user = user
        self.commits = 0

    def query(self, _model):
        return FakeQuery(self.user)

    def commit(self):
        self.commits += 1


class PasswordResetTests(unittest.TestCase):
    def test_unknown_email_gets_same_generic_response(self):
        tasks = BackgroundTasks()
        result = forgot_password(
            ForgotPasswordRequest(email="missing@example.com"),
            tasks,
            FakeSession(None),
        )
        self.assertEqual(result, {"message": "If the email exists, a reset link has been sent"})
        self.assertEqual(tasks.tasks, [])

    def test_existing_email_stores_only_token_hash_and_queues_email(self):
        user = SimpleNamespace(email="person@example.com")
        db = FakeSession(user)
        tasks = BackgroundTasks()
        result = forgot_password(ForgotPasswordRequest(email=user.email), tasks, db)
        self.assertEqual(result, {"message": "If the email exists, a reset link has been sent"})
        self.assertEqual(len(tasks.tasks), 1)
        self.assertIs(tasks.tasks[0].func, security.send_password_reset_email)
        token = tasks.tasks[0].args[1]
        self.assertEqual(user.reset_token, hashlib.sha256(token.encode("utf-8")).hexdigest())
        self.assertNotIn(token, result.values())
        self.assertIsNotNone(user.reset_token_expires)
        self.assertEqual(db.commits, 1)

    def test_reset_consumes_token_after_success(self):
        token = "one-time-reset-token"
        user = SimpleNamespace(
            email="person@example.test",
            password_hash="old-hash",
            reset_token=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            reset_token_expires=datetime.utcnow() + timedelta(minutes=10),
            two_factor_enabled=False,
        )
        db = FakeSession(user)
        result = reset_password(ResetPasswordRequest(token=token, new_password="new-password"), db=db)
        self.assertEqual(result, {"message": "Password reset successful"})
        self.assertNotEqual(user.password_hash, "old-hash")
        self.assertIsNone(user.reset_token)
        self.assertIsNone(user.reset_token_expires)
        self.assertEqual(db.commits, 1)

    def test_expired_token_is_rejected(self):
        token = "expired-reset-token"
        user = SimpleNamespace(
            email="person@example.test",
            password_hash="old-hash",
            reset_token=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            reset_token_expires=datetime.utcnow() - timedelta(seconds=1),
            two_factor_enabled=False,
        )
        with self.assertRaises(HTTPException) as raised:
            reset_password(ResetPasswordRequest(token=token, new_password="new-password"), db=FakeSession(user))
        self.assertEqual(raised.exception.status_code, 400)

    @patch("app.core.security.requests.post")
    def test_reset_email_uses_configured_frontend_url(self, post):
        from app.core.config import settings

        settings.PASSWORD_RESET_URL = "https://vibegarage.app/account/recover"
        post.return_value.status_code = 200
        self.assertTrue(security.send_password_reset_email("person@example.com", "safe-token"))
        payload = post.call_args.kwargs["json"]
        self.assertIn("https://vibegarage.app/account/recover?token=safe-token", payload["html"])


if __name__ == "__main__":
    unittest.main()
