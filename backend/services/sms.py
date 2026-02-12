"""
Beauty OS — SMS Service (Twilio)
"""

from config.settings import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER


def send_sms(to: str, body: str) -> str:
    """
    Send an SMS via Twilio.
    Returns the message SID on success.
    """
    from twilio.rest import Client

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=body,
        from_=TWILIO_PHONE_NUMBER,
        to=to,
    )
    return message.sid


def send_sms_dry_run(to: str, body: str) -> dict:
    """Simulate sending an SMS (for testing without Twilio credentials)."""
    print(f"[DRY RUN SMS] To: {to}")
    print(f"[DRY RUN SMS] Body: {body}")
    return {"sid": "dry_run", "to": to, "body": body}
