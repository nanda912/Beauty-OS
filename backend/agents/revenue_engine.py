"""
Beauty OS — Revenue Engine Agent (Multi-Tenant)

Triggers 24 hours before an appointment, analyzes the booked service,
cross-references the studio's add-on catalog from DB, and sends a
personalized upsell SMS.
"""

from backend.services.llm import call_llm_json
from backend.services.sms import send_sms
from backend.database import (
    get_upcoming_bookings_in_window,
    get_addons_for_studio,
    get_services_for_studio,
    get_addons_for_service,
    add_upsell_to_booking,
    log_event,
)
from backend.studio_config import get_studio_config
from config.settings import UPSELL_LEAD_TIME_HOURS


# ── Dynamic Prompt Builder ───────────────────────────────────────────

def _build_upsell_prompt(config: dict) -> str:
    """Build the SMS drafting prompt from studio config."""
    studio = config["studio"]
    voice = config["brand_voice"]

    return f"""You are the SMS assistant for "{studio['name']}".

Write a SHORT, cheeky, friendly upsell text message (under 160 characters if possible,
max 320 characters). The message should:
1. Greet the client by first name.
2. Mention their booked service and confirm the appointment is tomorrow.
3. Pitch the add-on naturally using the provided pitch line.
4. End with "Reply YES to add it!" or similar CTA.

Tone: {voice['sms_tone']}. Use {voice['emoji_limit']}.

RESPOND WITH VALID JSON ONLY:
{{
    "sms_body": "The full SMS text"
}}
"""


def _find_best_addon(service_name: str, studio_id: str) -> dict | None:
    """Look up the best add-on for a given service from the DB."""
    services = get_services_for_studio(studio_id)

    # Find the matching service
    service_name_lower = service_name.lower().strip()
    for svc in services:
        if svc["name"].lower() in service_name_lower or service_name_lower in svc["name"].lower():
            addons = get_addons_for_service(svc["id"])
            if addons:
                return addons[0]  # Top recommendation

    # Check all addons for the studio as fallback
    all_addons = get_addons_for_studio(studio_id)
    if all_addons:
        return all_addons[0]

    return None


def generate_upsell_sms(client_name: str, service: str, addon: dict, config: dict) -> str:
    """Use the LLM to draft a personalized upsell SMS."""
    system_prompt = _build_upsell_prompt(config)

    result = call_llm_json(
        system_prompt=system_prompt,
        user_message=(
            f"Client: {client_name}\n"
            f"Booked service: {service}\n"
            f"Add-on: {addon['name']} — ${addon['price']:.0f}, {addon['duration_min']} min\n"
            f"Pitch angle: {addon.get('pitch', 'Add this while youre here!')}"
        ),
    )
    return result["sms_body"]


def process_upsell_window(studio_id: str = ""):
    """
    Main scheduled task: find all bookings within the upsell window
    and send an upsell SMS for each.

    Returns a list of results for logging / dashboard display.
    """
    bookings = get_upcoming_bookings_in_window(
        hours_from_now=UPSELL_LEAD_TIME_HOURS,
        studio_id=studio_id,
    )
    results = []

    # Load config once if we have a studio_id
    config = get_studio_config(studio_id) if studio_id else None

    for booking in bookings:
        bid_studio = booking.get("studio_id", studio_id)
        if not config and bid_studio:
            config = get_studio_config(bid_studio)

        addon = _find_best_addon(booking["service"], bid_studio or "")
        if not addon:
            continue  # No add-ons configured for this studio

        client_name = booking["client_name"].split()[0]  # First name only

        # Generate SMS
        if config:
            sms_body = generate_upsell_sms(client_name, booking["service"], addon, config)
        else:
            sms_body = f"Hey {client_name}! Add a {addon['name']} (${addon['price']:.0f}) to tomorrow's {booking['service']}? Reply YES!"

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
            studio_id=bid_studio,
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


def handle_upsell_reply(booking_id: str, reply_text: str, studio_id: str = "") -> dict:
    """
    Handle an inbound SMS reply to an upsell.
    If the reply is affirmative, add the upsell to the booking.
    """
    affirmative = reply_text.strip().lower() in (
        "yes", "yep", "yeah", "y", "sure", "ok", "add it", "do it",
        "yes please", "yes!", "yesss",
    )

    if affirmative:
        # In production, look up what was offered from event metadata
        addon = None
        if studio_id:
            all_addons = get_addons_for_studio(studio_id)
            if all_addons:
                addon = all_addons[0]

        if not addon:
            addon = {"name": "Add-on", "price": 10.00}

        add_upsell_to_booking(booking_id, addon["name"], addon["price"])
        log_event(
            agent="revenue",
            action="upsell_accepted",
            metadata={"booking_id": booking_id, "addon": addon["name"], "revenue": addon["price"]},
            studio_id=studio_id,
        )
        return {"accepted": True, "addon": addon["name"], "added_revenue": addon["price"]}
    else:
        log_event(
            agent="revenue",
            action="upsell_declined",
            metadata={"booking_id": booking_id, "reply": reply_text},
            studio_id=studio_id,
        )
        return {"accepted": False}
