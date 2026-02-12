"""
Beauty OS — Gap-Filler Agent

Detects cancellations and automatically notifies the waitlist via SMS
to fill the open slot.
"""

from backend.services.sms import send_sms
from backend.database import (
    cancel_booking,
    get_waitlist_for_service,
    mark_waitlist_notified,
    create_booking,
    log_event,
)
from config.settings import STUDIO_NAME, BOOKING_URL


def _build_gap_fill_sms(client_name: str, service: str, time_slot: str) -> str:
    """Build the waitlist notification SMS."""
    first_name = client_name.split()[0]
    return (
        f"Hey {first_name}! A spot just opened up for {service} "
        f"on {time_slot}. Want it? Reply YES to grab it before it's gone! "
        f"— {STUDIO_NAME}"
    )


def handle_cancellation(booking_id: str, service: str, scheduled_at: str, original_price: float) -> dict:
    """
    Process a booking cancellation:
    1. Mark the booking as cancelled.
    2. Find waitlisted clients for the same service.
    3. Notify the top waitlisted client via SMS.

    Returns a summary of the gap-fill attempt.
    """
    # Step 1: Cancel the booking
    cancel_booking(booking_id)
    log_event(
        agent="gap_filler",
        action="cancellation_detected",
        metadata={"booking_id": booking_id, "service": service, "time": scheduled_at},
    )

    # Step 2: Find waitlisted clients
    waitlist = get_waitlist_for_service(service)

    if not waitlist:
        log_event(
            agent="gap_filler",
            action="no_waitlist",
            metadata={"booking_id": booking_id, "service": service},
        )
        return {
            "cancellation_processed": True,
            "waitlist_notified": False,
            "reason": "No one on waitlist for this service.",
        }

    # Step 3: Notify the first person on the waitlist
    next_client = waitlist[0]
    sms_body = _build_gap_fill_sms(
        client_name=next_client["client_name"],
        service=service,
        time_slot=scheduled_at,
    )

    if next_client.get("client_phone"):
        sid = send_sms(to=next_client["client_phone"], body=sms_body)
    else:
        sid = "no_phone"

    mark_waitlist_notified(next_client["id"])

    log_event(
        agent="gap_filler",
        action="waitlist_notified",
        metadata={
            "waitlist_entry_id": next_client["id"],
            "client_id": next_client["client_id"],
            "sms_sid": sid,
        },
    )

    return {
        "cancellation_processed": True,
        "waitlist_notified": True,
        "notified_client": next_client["client_name"],
        "sms_body": sms_body,
        "sms_sid": sid,
    }


def handle_gap_fill_reply(
    client_id: str,
    service: str,
    scheduled_at: str,
    price: float,
    reply_text: str,
) -> dict:
    """
    Handle an inbound SMS reply from a waitlisted client.
    If affirmative, create a new booking for the open slot.
    """
    affirmative = reply_text.strip().lower() in (
        "yes", "yep", "yeah", "y", "sure", "ok", "grab it", "i want it",
        "yes please", "yes!", "book it",
    )

    if affirmative:
        booking_id = create_booking(
            client_id=client_id,
            service=service,
            price=price,
            scheduled_at=scheduled_at,
            source="waitlist",
        )
        log_event(
            agent="gap_filler",
            action="slot_filled",
            metadata={"booking_id": booking_id, "client_id": client_id},
        )
        return {"filled": True, "booking_id": booking_id}
    else:
        log_event(
            agent="gap_filler",
            action="waitlist_declined",
            metadata={"client_id": client_id},
        )
        return {"filled": False}
