"""
Beauty OS — Studio Configuration Loader

Loads a studio's full config (name, policies, services, add-ons, brand voice)
and provides brand-voice prompt fragments for each agent.
"""

from backend.database import (
    get_studio_by_slug,
    get_studio_by_api_key,
    get_default_studio,
    get_services_for_studio,
    get_addons_for_service,
)


# ── Brand Voice Presets ──────────────────────────────────────────────

BRAND_VOICE_PROMPTS = {
    "professional_chill": {
        "label": "Professional & Chill",
        "personality": (
            "Professional, particular, and chill. "
            "You are warm but you do NOT bend rules. "
            "You keep responses concise (2-4 sentences max). "
            "You never sound desperate for business. You're booked and selective. "
            "If someone is rude, pushy, or tries to haggle, you stay composed and "
            "redirect them politely — but you do NOT accommodate."
        ),
        "sms_tone": "warm and casual, not salesy",
        "emoji_limit": "1-2 emojis max",
    },
    "warm_bubbly": {
        "label": "Warm & Bubbly",
        "personality": (
            "Warm, bubbly, and genuinely excited to help. "
            "You radiate positive energy and make every client feel special. "
            "You keep responses friendly and upbeat (2-4 sentences max). "
            "You still enforce all policies firmly, but with a smile. "
            "If someone pushes back, you stay cheerful and redirect with kindness."
        ),
        "sms_tone": "bubbly and enthusiastic, like texting a friend",
        "emoji_limit": "2-3 emojis",
    },
    "luxury_exclusive": {
        "label": "Luxury & Exclusive",
        "personality": (
            "Refined, elegant, and subtly exclusive. "
            "You speak like a luxury concierge — polished but never stuffy. "
            "You keep responses sophisticated and concise (2-3 sentences max). "
            "You make clients feel they're accessing something special. "
            "Policies are presented as 'standards of our house' rather than rules."
        ),
        "sms_tone": "polished and refined, like a luxury brand",
        "emoji_limit": "1 emoji max, elegant choices only (✨💎)",
    },
}


def get_studio_config(studio_id: str) -> dict:
    """
    Load a studio's full configuration including services + add-ons.

    Returns:
        {
            "studio": { ...studio row... },
            "services": [ { ...service..., "addons": [...] } ],
            "brand_voice": { ...voice preset dict... },
        }
    """
    from backend.database import get_db

    with get_db() as db:
        row = db.execute("SELECT * FROM studios WHERE id=?", (studio_id,)).fetchone()

    if not row:
        return None

    studio = dict(row)

    # Load services with their add-ons
    services = get_services_for_studio(studio_id)
    for svc in services:
        svc["addons"] = get_addons_for_service(svc["id"])

    # Resolve brand voice
    voice_key = studio.get("brand_voice", "professional_chill")
    brand_voice = BRAND_VOICE_PROMPTS.get(voice_key, BRAND_VOICE_PROMPTS["professional_chill"])

    return {
        "studio": studio,
        "services": services,
        "brand_voice": brand_voice,
    }


def get_services_menu(config: dict) -> str:
    """Format the studio's services + add-ons as a readable menu for prompts."""
    if not config or not config.get("services"):
        return "No services configured yet."

    lines = []
    for svc in config["services"]:
        lines.append(f"• {svc['name']} — ${svc['price']:.0f} ({svc['duration_min']} min)")
        for addon in svc.get("addons", []):
            lines.append(f"  ↳ Add-on: {addon['name']} — ${addon['price']:.0f} ({addon['duration_min']} min)")
            if addon.get("pitch"):
                lines.append(f"    Pitch: \"{addon['pitch']}\"")
    return "\n".join(lines)


def get_policies_text(studio: dict) -> str:
    """Format the studio's policies as a readable block for prompts."""
    return (
        f"1. A ${studio.get('deposit_amount', 25):.0f} non-refundable deposit is required to hold any appointment.\n"
        f"2. Cancellations within {studio.get('cancel_window_hours', 24)} hours forfeit the deposit.\n"
        f"3. Late arrivals of 15+ minutes are treated as no-shows (deposit forfeited).\n"
        f"4. A ${studio.get('late_fee', 15):.0f} late fee applies to arrivals between 5-14 minutes late.\n"
        f"5. No exceptions. No sob stories. The policy exists to respect everyone's time."
    )
