import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

# These should be in your .env file
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

def send_payout_notification(artist_name: str, amount: float):
    """
    Sends an email to the Admin when a new payout is requested.
    """
    if not SMTP_USER or not ADMIN_EMAIL:
        print("Email settings not configured. Skipping notification.")
        return

    subject = f"🚨 New Payout Request: {artist_name}"
    body = f"""
    <h3>New Payout Request on Vibe Garage</h3>
    <p><strong>Artist:</strong> {artist_name}</p>
    <p><strong>Amount:</strong> {amount} V-Coins</p>
    <p>Please log in to the Admin Dashboard to review and approve this request.</p>
    <br>
    <a href="https://vibegarage.app/admin/payouts">Go to Admin Dashboard</a>
    """

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = ADMIN_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")