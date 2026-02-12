"""
Beauty OS — Zapier / Make.com Webhook Schemas

These are the webhook payload schemas that Zapier or Make.com
scenarios should POST to Beauty OS endpoints.

This file documents the integration contracts and provides
helper functions for building Make.com HTTP module configurations.
"""

# ── Zapier/Make.com → Beauty OS Webhook Contracts ────────────────────

WEBHOOK_CONTRACTS = {
    "instagram_new_dm": {
        "description": "Triggered when a new Instagram DM is received",
        "beauty_os_endpoint": "POST /api/vibe-check",
        "payload_schema": {
            "message": "string — The DM text content",
            "sender_name": "string — Display name of the sender",
            "sender_ig": "string — Instagram handle (without @)",
        },
        "zapier_trigger": "Instagram → New Message in Conversation",
        "make_trigger": "Instagram → Watch Messages",
    },

    "booking_cancelled": {
        "description": "Triggered when a Bookly PRO appointment is cancelled",
        "beauty_os_endpoint": "POST /api/gap-fill/cancel",
        "payload_schema": {
            "booking_id": "string — Bookly appointment ID",
            "service": "string — Service name (e.g., 'Bikini Wax')",
            "scheduled_at": "string — ISO datetime of the appointment",
            "original_price": "number — Price of the cancelled booking",
        },
        "zapier_trigger": "Bookly → Appointment Cancelled",
        "make_trigger": "Bookly → Watch Appointments (filter: status=cancelled)",
    },

    "sms_reply_received": {
        "description": "Triggered when a client replies to an upsell or gap-fill SMS",
        "beauty_os_endpoint": "POST /webhooks/twilio/inbound",
        "payload_schema": {
            "From": "string — Client phone number (E.164)",
            "Body": "string — SMS reply text",
        },
        "zapier_trigger": "Twilio → New SMS Received",
        "make_trigger": "Twilio → Watch Incoming Messages",
    },

    "upsell_accepted": {
        "description": "Beauty OS → Bookly: Update appointment after upsell accepted",
        "beauty_os_endpoint": "POST /api/upsell/reply",
        "payload_schema": {
            "booking_id": "string — Booking to update",
            "reply_text": "string — Client's SMS reply",
        },
        "zapier_action": "Bookly → Update Appointment (add custom field for add-on)",
        "make_action": "Bookly → Update an Appointment",
    },

    "trigger_upsell_cycle": {
        "description": "Scheduled trigger to run the upsell engine",
        "beauty_os_endpoint": "POST /api/upsell/process",
        "payload_schema": {},
        "zapier_trigger": "Schedule by Zapier → Every Hour",
        "make_trigger": "Scheduling → Run a scenario at regular intervals",
    },
}


def generate_make_http_config(contract_key: str, base_url: str = "https://your-beauty-os.com") -> dict:
    """
    Generate a Make.com HTTP module configuration for a given contract.
    Useful for programmatic setup of Make.com scenarios.
    """
    contract = WEBHOOK_CONTRACTS.get(contract_key)
    if not contract:
        return {"error": f"Unknown contract: {contract_key}"}

    endpoint = contract["beauty_os_endpoint"]
    method, path = endpoint.split(" ", 1)

    return {
        "module": "http.makeRequest",
        "url": f"{base_url}{path}",
        "method": method,
        "headers": [
            {"name": "Content-Type", "value": "application/json"},
        ],
        "body": contract["payload_schema"],
        "parse_response": True,
    }


# ── Print all contracts (for documentation) ─────────────────────────

if __name__ == "__main__":
    print("Beauty OS — Webhook Integration Contracts")
    print("=" * 60)
    for key, contract in WEBHOOK_CONTRACTS.items():
        print(f"\n{key}:")
        print(f"  Description: {contract['description']}")
        print(f"  Endpoint:    {contract['beauty_os_endpoint']}")
        print(f"  Payload:     {contract['payload_schema']}")
        if "zapier_trigger" in contract:
            print(f"  Zapier:      {contract['zapier_trigger']}")
        if "make_trigger" in contract:
            print(f"  Make.com:    {contract['make_trigger']}")
