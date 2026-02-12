"""
Beauty OS — Revenue Engine Agent (The Upsell Bot)

Triggers 24 hours before an appointment, analyzes the booked service,
cross-references the add-on catalog, and sends a personalized upsell SMS.
"""

from backend.services.llm import call_llm_json
from backend.services.sms import send_sms
from backend.database import (
    get_upcoming_bookings_in_window,
    add_upsell_to_booking,
    log_event,
)
from config.settings import UPSELL_LEAD_TIME_HOURS, STUDIO_NAME

# ── Add-On Catalog ───────────────────────────────────────────────────
# Maps a primary service → list of logical add-ons with price and duration.

ADDON_CATALOG = {
    "bikini wax": [
        {"name": "Quick-Flick Nose Wax", "price": 10.00, "duration_min": 3,
         "pitch": "Since we're getting you vacation-ready, I saved a spot for a 3-minute nose wax"},
        {"name": "Underarm Wax", "price": 15.00, "duration_min": 5,
         "pitch": "Want to go all-in? Add an underarm wax while you're here"},
    ],
    "brazilian wax": [
        {"name": "Quick-Flick Nose Wax", "price": 10.00, "duration_min": 3,
         "pitch": "Since we're already going bare, toss in a quick nose wax"},
        {"name": "Underarm Wax", "price": 15.00, "duration_min": 5,
         "pitch": "Add an underarm wax for the full smooth experience"},
        {"name": "Brow Shape", "price": 20.00, "duration_min": 10,
         "pitch": "Want your brows done too? I can shape them up real quick"},
    ],
    "brow shape": [
        {"name": "Brow Tint", "price": 12.00, "duration_min": 5,
         "pitch": "Want them tinted too? It makes such a difference"},
        {"name": "Lip Wax", "price": 8.00, "duration_min": 3,
         "pitch": "Add a quick lip wax while I'm already up there"},
    ],
    "facial": [
        {"name": "Lip Wax", "price": 8.00, "duration_min": 3,
         "pitch": "Want a lip wax added? Perfect time since we're already on your face"},
        {"name": "Brow Shape", "price": 20.00, "duration_min": 10,
         "pitch": "Add a brow shape while you're being pampered"},
    ],
    "full leg wax": [
        {"name": "Bikini Line", "price": 20.00, "duration_min": 10,
         "pitch": "Since we're doing legs, add a bikini line touch-up"},
        {"name": "Underarm Wax", "price": 15.00, "duration_min": 5,
         "pitch": "Toss in underarms for the full smooth package"},
    ],
}

# Default add-on for services not in the catalog
DEFAULT_ADDON = {
    "name": "Quick-Flick Nose Wax",
    "price": 10.00,
    "duration_min": 3,
    "pitch": "Add a quick nose wax while you're here — only takes 3 minutes",
}

# ── SMS Drafting Prompt ──────────────────────────────────────────────

UPSELL_SMS_SYSTEM_PROMPT = f"""You are the SMS assistant for "{STUDIO_NAME}".

Write a SHORT, cheeky, friendly upsell text message (under 160 characters if possible,
max 320 characters). The message should:
1. Greet the client by first name.
2. Mention their booked service and confirm the appointment is tomorrow.
3. Pitch the add-on naturally using the provided pitch line.
4. End with "Reply YES to add it!" or similar CTA.

Use 1-2 emojis max. Keep the tone warm and casual, not salesy.

RESPOND WITH VALID JSON ONLY:
{{
    "sms_body": "The full SMS text"
}}
"""


def _find_best_addon(service: str) -> dict:
    """Look up the best add-on for a given service."""
    service_lower = service.lower().strip()
    for key, addons in ADDON_CATALOG.items():
        if key in service_lower or service_lower in key:
            return addons[0]  # Return top recommendation
    return DEFAULT_ADDON


def generate_upsell_sms(client_name: str, service: str, addon: dict) -> str:
    """Use the LLM to draft a personalized upsell SMS."""
    result = call_llm_json(
        system_prompt=UPSELL_SMS_SYSTEM_PROMPT,
        user_message=(
            f"Client: {client_name}\n"
            f"Booked service: {service}\n"
            f"Add-on: {addon['name']} — ${addon['price']:.0f}, {addon['duration_min']} min\n"
            f"Pitch angle: {addon['pitch']}"
        ),
    )
    return result["sms_body"]


def process_upsell_window():
    """
    Main scheduled task: find all bookings within the upsell window
    and send an upsell SMS for each.

    Returns a list of results for logging / dashboard display.
    """
    bookings = get_upcoming_bookings_in_window(hours_from_now=UPSELL_LEAD_TIME_HOURS)
    results = []

    for booking in bookings:
        addon = _find_best_addon(booking["service"])
        client_name = booking["client_name"].split()[0]  # First name only

        # Generate SMS
        sms_body = generate_upsell_sms(client_name, booking["service"], addon)

        # Send SMS (skip if no phone number)
        if booking.get("client_phone"):
            sid = send_sms(to=booking["client_phone"], body=sms_body)
        else:
            sid = "no_phone"

        log_event(
            agent="revenue",
            action="upsell_sent",
            metadata={
                "booking_id": booking["id"],
                "addon": addon["name"],
                "addon_price": addon["price"],
                "sms_sid": sid,
            },
        )

        results.append({
            "booking_id": booking["id"],
            "client_name": client_name,
            "service": booking["service"],
            "addon_offered": addon["name"],
            "addon_price": addon["price"],
            "sms_body": sms_body,
            "sms_sid": sid,
        })

    return results


def handle_upsell_reply(booking_id: str, reply_text: str) -> dict:
    """
    Handle an inbound SMS reply to an upsell.
    If the reply is affirmative, add the upsell to the booking.
    """
    affirmative = reply_text.strip().lower() in (
        "yes", "yep", "yeah", "y", "sure", "ok", "add it", "do it",
        "yes please", "yes!", "yesss",
    )

    if affirmative:
        # Look up what add-on was offered (from the most recent upsell event)
        # In production, this would be stored in the event metadata
        addon = DEFAULT_ADDON  # Simplified; production queries the event log
        add_upsell_to_booking(booking_id, addon["name"], addon["price"])
        log_event(
            agent="revenue",
            action="upsell_accepted",
            metadata={"booking_id": booking_id, "addon": addon["name"], "revenue": addon["price"]},
        )
        return {"accepted": True, "addon": addon["name"], "added_revenue": addon["price"]}
    else:
        log_event(
            agent="revenue",
            action="upsell_declined",
            metadata={"booking_id": booking_id, "reply": reply_text},
        )
        return {"accepted": False}


# ── Demo / CLI test ──────────────────────────────────────────────────

if __name__ == "__main__":
    # Test the SMS generation (requires LLM API key)
    addon = _find_best_addon("Bikini Wax")
    print(f"Best addon for 'Bikini Wax': {addon['name']} (${addon['price']})")

    sms = generate_upsell_sms("Sarah", "Bikini Wax", addon)
    print(f"\nGenerated SMS:\n{sms}")
