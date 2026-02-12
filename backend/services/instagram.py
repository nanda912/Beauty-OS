"""
Beauty OS — Instagram Graph API Service

Handles reading DMs and sending replies via the Instagram Graph API.
"""

import requests
from config.settings import IG_ACCESS_TOKEN, IG_PAGE_ID

BASE_URL = "https://graph.facebook.com/v18.0"


def send_dm_reply(recipient_id: str, message_text: str) -> dict:
    """
    Send a reply to an Instagram DM conversation.
    Uses the Instagram Messaging API (requires approved permissions).
    """
    url = f"{BASE_URL}/{IG_PAGE_ID}/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "access_token": IG_ACCESS_TOKEN,
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def send_dm_reply_dry_run(recipient_id: str, message_text: str) -> dict:
    """Simulate sending an IG DM (for testing without credentials)."""
    print(f"[DRY RUN IG DM] To: {recipient_id}")
    print(f"[DRY RUN IG DM] Message: {message_text}")
    return {"recipient_id": recipient_id, "message": message_text}
