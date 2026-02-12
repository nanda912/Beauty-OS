"""
Beauty OS — Vibe Check Agent (Multi-Tenant)

The AI gatekeeper that screens new leads for brand fit,
enforces deposit/late-fee policies, and controls calendar access.

Output Schema:
{
    "is_approved": bool,
    "vibe_score": float (0.0–1.0),
    "reasoning": str,
    "draft_reply": str,
    "requires_policy_confirmation": bool,
    "detected_intent": "service_inquiry" | "pricing" | "policy_bypass" | "spam" | "other"
}
"""

from backend.services.llm import call_llm_json
from backend.database import (
    create_client,
    update_client_intake,
    log_event,
)
from backend.studio_config import (
    get_studio_config,
    get_services_menu,
    get_policies_text,
)


# ── Dynamic Prompt Builders ──────────────────────────────────────────

def _build_vibe_check_prompt(config: dict) -> str:
    """Build the Vibe Check system prompt from a studio's config."""
    studio = config["studio"]
    voice = config["brand_voice"]

    services_menu = get_services_menu(config)
    policies = get_policies_text(studio)
    booking_url = studio.get("booking_url", "")
    booking_line = f"\nBooking link: {booking_url}" if booking_url else ""

    return f"""You are the virtual front-desk assistant for "{studio['name']}".

PERSONALITY:
{voice['personality']}

SERVICES OFFERED:
{services_menu}

POLICIES YOU ENFORCE (non-negotiable):
{policies}

YOUR JOB:
1. Determine what the person wants (service inquiry, pricing, trying to bypass policies, spam, or other).
2. Rate them on brand fit (0.0 = total mismatch, 1.0 = dream client).
   - Dream clients: respectful, clear about what they want, understand policies.
   - Red flags: demanding discounts, refusing deposits, rude tone, "can you just squeeze me in."
3. If they seem like a good fit, confirm they understand and accept the deposit
   policy BEFORE giving them the booking link.
4. If they're not a fit, politely decline or redirect.

RESPOND WITH VALID JSON ONLY — no markdown, no explanation outside the JSON:
{{
    "is_approved": true/false,
    "vibe_score": 0.0-1.0,
    "reasoning": "Brief internal note on why you scored them this way",
    "draft_reply": "The actual message to send back to the client",
    "requires_policy_confirmation": true/false,
    "detected_intent": "service_inquiry" | "pricing" | "policy_bypass" | "spam" | "other"
}}

If requires_policy_confirmation is true, your draft_reply should ask them to
confirm they accept the deposit/cancellation policy before you provide the
booking link.

If is_approved is true AND they've already confirmed the policy (the user
message indicates acceptance), include the booking link in your reply:{booking_line}
"""


def _build_confirmation_prompt(config: dict) -> str:
    """Build the policy confirmation follow-up prompt."""
    studio = config["studio"]
    booking_url = studio.get("booking_url", "")
    booking_line = f" {booking_url}" if booking_url else ""

    return f"""You are the virtual front-desk assistant for "{studio['name']}".

The client has been sent the deposit/cancellation policy. Now you need to
evaluate whether their reply constitutes a clear acceptance.

Acceptable: "yes", "sounds good", "I agree", "that works", "ok deal", etc.
Not acceptable: ignoring the policy, changing the subject, asking for exceptions.

RESPOND WITH VALID JSON ONLY:
{{
    "confirmed": true/false,
    "draft_reply": "Your response to the client"
}}

If confirmed is true, your draft_reply should include the booking link:{booking_line}
If confirmed is false, your draft_reply should re-state the policy requirement gently.
"""


# ── Agent Logic ──────────────────────────────────────────────────────

def evaluate_lead(
    message: str,
    sender_name: str = "Unknown",
    sender_ig: str = "",
    studio_id: str = "",
    dry_run: bool = False,
) -> dict:
    """
    Evaluate an incoming Instagram DM for brand fit.

    Args:
        studio_id: The studio to evaluate for. Falls back to default if empty.
        dry_run: If True, run the AI but don't create client records.

    Returns the full LLM evaluation dict plus a `client_id` if a new
    client record was created.
    """
    # Load studio config
    if studio_id:
        config = get_studio_config(studio_id)
    else:
        from backend.database import get_default_studio
        default = get_default_studio()
        config = get_studio_config(default["id"]) if default else None

    if not config:
        return {
            "is_approved": False,
            "vibe_score": 0.0,
            "reasoning": "No studio configured.",
            "draft_reply": "Sorry, this studio isn't set up yet!",
            "requires_policy_confirmation": False,
            "detected_intent": "other",
        }

    system_prompt = _build_vibe_check_prompt(config)

    result = call_llm_json(
        system_prompt=system_prompt,
        user_message=f"Instagram DM from @{sender_ig} ({sender_name}):\n\n{message}",
    )

    if dry_run:
        result["dry_run"] = True
        return result

    # Create client record
    client_id = create_client(
        name=sender_name,
        instagram_handle=sender_ig,
        studio_id=studio_id,
    )

    # Determine intake status
    if result.get("is_approved") and not result.get("requires_policy_confirmation"):
        status = "approved"
    elif not result.get("is_approved"):
        status = "declined"
    else:
        status = "pending"  # Awaiting policy confirmation

    update_client_intake(
        client_id=client_id,
        status=status,
        vibe_score=result.get("vibe_score", 0.0),
        reasoning=result.get("reasoning", ""),
    )

    log_event(
        agent="vibe_check",
        action="lead_evaluated",
        metadata={
            "client_id": client_id,
            "is_approved": result.get("is_approved"),
            "vibe_score": result.get("vibe_score"),
            "detected_intent": result.get("detected_intent"),
        },
        studio_id=studio_id,
    )

    result["client_id"] = client_id
    return result


def evaluate_policy_confirmation(
    client_id: str,
    message: str,
    studio_id: str = "",
) -> dict:
    """
    Check if the client's follow-up message confirms acceptance
    of the deposit/cancellation policy.
    """
    # Load studio config
    if studio_id:
        config = get_studio_config(studio_id)
    else:
        from backend.database import get_default_studio
        default = get_default_studio()
        config = get_studio_config(default["id"]) if default else None

    if not config:
        return {"confirmed": False, "draft_reply": "Studio not configured."}

    system_prompt = _build_confirmation_prompt(config)

    result = call_llm_json(
        system_prompt=system_prompt,
        user_message=f"Client reply:\n\n{message}",
    )

    if result.get("confirmed"):
        update_client_intake(
            client_id=client_id,
            status="approved",
            vibe_score=1.0,
            reasoning="Policy confirmed by client.",
        )
        log_event(
            agent="vibe_check",
            action="policy_confirmed",
            metadata={"client_id": client_id},
            studio_id=studio_id,
        )
    else:
        log_event(
            agent="vibe_check",
            action="policy_not_confirmed",
            metadata={"client_id": client_id},
            studio_id=studio_id,
        )

    return result


# ── Demo / CLI test ──────────────────────────────────────────────────

if __name__ == "__main__":
    from backend.database import init_db
    init_db()

    test_messages = [
        ("Hey! I'm looking to get a Brazilian wax next week. What days are you available?",
         "Sarah", "sarah_glow"),
        ("how much for a bikini wax? can I get a discount if I bring my friend?",
         "Jessica", "jess_deals"),
        ("I need an appointment NOW. I don't care about your deposit, just book me in.",
         "Karen", "karen_wants_manager"),
    ]

    for msg, name, ig in test_messages:
        print(f"\n{'='*60}")
        print(f"From @{ig}: {msg}")
        print(f"{'='*60}")
        result = evaluate_lead(msg, sender_name=name, sender_ig=ig)
        for k, v in result.items():
            print(f"  {k}: {v}")
