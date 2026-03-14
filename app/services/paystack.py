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

def verify_payment(self, reference: str):
    """Verifies a transaction using the reference returned by Paystack."""
    url = f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    
    response = requests.get(url, headers=headers)
    return response.json()