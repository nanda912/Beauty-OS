"""
Beauty OS — Bookly PRO Integration

Communicates with the Bookly PRO WordPress plugin via its REST API
to create/update/cancel appointments.
"""

import requests
from config.settings import BOOKLY_API_URL, BOOKLY_API_KEY


def _headers():
    return {
        "Authorization": f"Bearer {BOOKLY_API_KEY}",
        "Content-Type": "application/json",
    }


def get_available_slots(service_id: str, date: str) -> list[dict]:
    """
    Fetch available time slots for a given service and date.
    Date format: YYYY-MM-DD
    """
    url = f"{BOOKLY_API_URL}/slots"
    params = {"service_id": service_id, "date": date}
    resp = requests.get(url, headers=_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def create_appointment(
    client_name: str,
    client_email: str,
    client_phone: str,
    service_id: str,
    staff_id: str,
    datetime_slot: str,
) -> dict:
    """
    Create a new appointment in Bookly PRO.
    datetime_slot format: YYYY-MM-DD HH:MM:SS
    """
    url = f"{BOOKLY_API_URL}/appointments"
    payload = {
        "client": {
            "name": client_name,
            "email": client_email,
            "phone": client_phone,
        },
        "service_id": service_id,
        "staff_id": staff_id,
        "datetime": datetime_slot,
    }
    resp = requests.post(url, headers=_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()


def update_appointment_price(appointment_id: str, new_price: float, add_ons: list[dict]) -> dict:
    """
    Update an appointment's price and add-ons after an upsell is accepted.
    """
    url = f"{BOOKLY_API_URL}/appointments/{appointment_id}"
    payload = {
        "custom_fields": {
            "add_ons": add_ons,
            "adjusted_price": new_price,
        },
    }
    resp = requests.patch(url, headers=_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()


def cancel_appointment(appointment_id: str) -> dict:
    """Cancel an appointment in Bookly PRO."""
    url = f"{BOOKLY_API_URL}/appointments/{appointment_id}"
    payload = {"status": "cancelled"}
    resp = requests.patch(url, headers=_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()


# ── Dry-run versions for testing ─────────────────────────────────────

def create_appointment_dry_run(**kwargs) -> dict:
    print(f"[DRY RUN BOOKLY] Create appointment: {kwargs}")
    return {"id": "dry_run_appt_001", **kwargs}


def update_appointment_price_dry_run(appointment_id: str, new_price: float, add_ons: list) -> dict:
    print(f"[DRY RUN BOOKLY] Update {appointment_id}: price={new_price}, add_ons={add_ons}")
    return {"id": appointment_id, "price": new_price}
