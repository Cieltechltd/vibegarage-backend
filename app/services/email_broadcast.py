import os
import logging
import httpx
from typing import List

logger = logging.getLogger("vibe-garage-broadcast")

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_ADDRESS = os.getenv("RESEND_FROM_ADDRESS", "Vibe Garage <noreply@vibegarage.app>")
RESEND_BATCH_URL = "https://api.resend.com/emails/batch"
BATCH_SIZE = 100  # Resend's per-request cap on the batch endpoint


def send_broadcast_email(subject: str, html_body: str, recipient_emails: List[str]) -> None:
    """
    Sends the same email to many recipients via Resend's batch endpoint,
    chunked into groups of 100 (Resend's per-request limit).

    IMPORTANT: each recipient gets their own individual email object with a
    single-address "to" field -- never one email with everyone's address
    listed together. Doing it the other way would leak every recipient's
    email address to every other recipient (visible via "reply all" or
    just viewing headers), which is a real, common mass-email privacy bug.

    Runs as a background task -- errors are logged rather than raised,
    since there's no request left to return a failure to by the time this
    executes.
    """
    if not RESEND_API_KEY:
        logger.error("Cannot send broadcast email: RESEND_API_KEY not configured.")
        return

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    sent_count = 0
    for i in range(0, len(recipient_emails), BATCH_SIZE):
        chunk = recipient_emails[i:i + BATCH_SIZE]
        payload = [
            {
                "from": RESEND_FROM_ADDRESS,
                "to": [email],  # one recipient per email object -- see note above
                "subject": subject,
                "html": html_body
            }
            for email in chunk
        ]

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(RESEND_BATCH_URL, headers=headers, json=payload)
            if response.status_code >= 400:
                logger.error(f"Resend batch send failed for chunk starting at index {i}: {response.text}")
            else:
                sent_count += len(chunk)
        except Exception as e:
            logger.error(f"Resend batch send raised an exception for chunk starting at index {i}: {e}")

    logger.info(f"Broadcast email '{subject}' sent to {sent_count}/{len(recipient_emails)} recipients.")