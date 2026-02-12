"""
Beauty OS — Vibe Check Agent

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
from config.settings import STUDIO_NAME, DEPOSIT_AMOUNT, LATE_FEE, BOOKING_URL

# ── System Prompt — The "Brain" of the Gatekeeper ────────────────────

VIBE_CHECK_SYSTEM_PROMPT = f"""You are the virtual front-desk assistant for "{STUDIO_NAME}".

PERSONALITY:
- Professional, particular, and chill.
- You are warm but you do NOT bend rules.
- You keep responses concise (2-4 sentences max).
- You never sound desperate for business. You're booked and selective.
- If someone is rude, pushy, or tries to haggle, you stay composed and
  redirect them politely — but you do NOT accommodate.

POLICIES YOU ENFORCE (non-negotiable):
1. A ${DEPOSIT_AMOUNT:.0f} non-refundable deposit is required to hold any appointment.
2. Cancellations within 24 hours forfeit the deposit.
3. Late arrivals of 15+ minutes are treated as no-shows (deposit forfeited).
4. A ${LATE_FEE:.0f} late fee applies to arrivals between 5-14 minutes late.
5. No exceptions. No sob stories. The policy exists to respect everyone's time.

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
message indicates acceptance), include the booking link in your reply:
{BOOKING_URL}
"""

# ── Confirmation follow-up prompt ────────────────────────────────────

CONFIRMATION_SYSTEM_PROMPT = f"""You are the virtual front-desk assistant for "{STUDIO_NAME}".

The client has been sent the deposit/cancellation policy. Now you need to
evaluate whether their reply constitutes a clear acceptance.

Acceptable: "yes", "sounds good", "I agree", "that works", "ok deal", etc.
Not acceptable: ignoring the policy, changing the subject, asking for exceptions.

RESPOND WITH VALID JSON ONLY:
{{
    "confirmed": true/false,
    "draft_reply": "Your response to the client"
}}

If confirmed is true, your draft_reply should include the booking link: {BOOKING_URL}
If confirmed is false, your draft_reply should re-state the policy requirement gently.
"""


# ── Agent Logic ──────────────────────────────────────────────────────

def evaluate_lead(
    message: str,
    sender_name: str = "Unknown",
    sender_ig: str = "",
) -> dict:
    """
    Evaluate an incoming Instagram DM for brand fit.

    Returns the full LLM evaluation dict plus a `client_id` if a new
    client record was created.
    """
    result = call_llm_json(
        system_prompt=VIBE_CHECK_SYSTEM_PROMPT,
        user_message=f"Instagram DM from @{sender_ig} ({sender_name}):\n\n{message}",
    )

    # Create client record
    client_id = create_client(
        name=sender_name,
        instagram_handle=sender_ig,
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
    )

    result["client_id"] = client_id
    return result


def evaluate_policy_confirmation(
    client_id: str,
    message: str,
) -> dict:
    """
    Check if the client's follow-up message confirms acceptance
    of the deposit/cancellation policy.
    """
    result = call_llm_json(
        system_prompt=CONFIRMATION_SYSTEM_PROMPT,
        user_message=f"Client reply:\n\n{message}",
    )

    if result.get("confirmed"):
        update_client_intake(
            client_id=client_id,
            status="approved",
            vibe_score=1.0,  # They passed both gates
            reasoning="Policy confirmed by client.",
        )
        log_event(
            agent="vibe_check",
            action="policy_confirmed",
            metadata={"client_id": client_id},
        )
    else:
        log_event(
            agent="vibe_check",
            action="policy_not_confirmed",
            metadata={"client_id": client_id},
        )

    return result


# ── Demo / CLI test ──────────────────────────────────────────────────

if __name__ == "__main__":
    # Quick test — requires ANTHROPIC_API_KEY or OPENAI_API_KEY in .env
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
