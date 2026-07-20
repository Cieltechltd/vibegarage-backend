import requests
from app.core.config import settings

PAYSTACK_BASE_URL = "https://api.paystack.co"

def initialize_payment(email: str, amount: float, track_id: str, reference: str):
    
    url = f"{PAYSTACK_BASE_URL}/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": email,
        "amount": int(amount * 100), 
        "callback_url": f"{settings.BASE_URL}/payment/callback",
        "reference": reference,
        "metadata": {"track_id": track_id}
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def verify_payment(reference: str):
    """Verifies a transaction using the reference returned by Paystack."""
    url = f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    
    response = requests.get(url, headers=headers)
    return response.json()


def create_transfer_recipient(name: str, account_number: str, bank_code: str) -> dict:
    
    url = f"{PAYSTACK_BASE_URL}/transferrecipient"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "type": "nuban",
        "name": name,
        "account_number": account_number,
        "bank_code": bank_code,
        "currency": "NGN"
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def initiate_transfer(amount_ngn: float, recipient_code: str, reason: str, reference: str) -> dict:
    
    url = f"{PAYSTACK_BASE_URL}/transfer"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "source": "balance",
        "amount": int(round(amount_ngn * 100)),
        "recipient": recipient_code,
        "reason": reason,
        "reference": reference
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()