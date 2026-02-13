"""
Beauty OS — FastAPI Server (Multi-Tenant)

Central API that connects all agents, webhooks, onboarding, and the dashboard.
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from backend.database import (
    init_db,
    get_dashboard_metrics,
    get_recent_events,
    create_studio,
    get_studio_by_slug,
    get_studio_by_email,
    get_default_studio,
    update_studio,
    create_service,
    get_services_for_studio,
    update_service,
    delete_service,
    create_addon,
    get_addons_for_service,
    get_addons_for_studio,
    update_addon,
    delete_addon,
    create_magic_token,
    validate_magic_token,
    cleanup_expired_tokens,
    get_social_leads,
)
from backend.auth import get_current_studio, get_optional_studio
from backend.studio_config import get_studio_config, BRAND_VOICE_PROMPTS
from backend.services.email import send_magic_link
from backend.agents.vibe_check import evaluate_lead, evaluate_policy_confirmation
from backend.agents.revenue_engine import process_upsell_window, handle_upsell_reply
from backend.agents.gap_filler import handle_cancellation, handle_gap_fill_reply
from backend.agents.social_hunter import run_social_hunter, approve_and_reply, dismiss_lead

app = FastAPI(title="Beauty OS", version="2.0.0")

# Allow the React dashboard to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://beauty-os.vercel.app",
        "https://web-production-8369d9.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    cleanup_expired_tokens()


# ── Health Check ─────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "beauty-os"}


# ═══════════════════════════════════════════════════════════════════════
# AUTH — Magic Link Login (no auth required)
# ═══════════════════════════════════════════════════════════════════════


class MagicLinkRequest(BaseModel):
    email: str


class VerifyTokenRequest(BaseModel):
    token: str


@app.post("/api/auth/send-magic-link")
def send_magic_link_endpoint(req: MagicLinkRequest):
    """Send a magic link email to the studio owner."""
    email = req.email.strip().lower()
    if not email:
        raise HTTPException(400, "Email is required")

    studio = get_studio_by_email(email)
    if not studio:
        # Don't reveal whether the email exists — always say "check your inbox"
        return {"sent": True}

    token = create_magic_token(studio["id"])
    result = send_magic_link(
        to_email=email,
        token=token,
        studio_name=studio["name"],
    )

    if not result["sent"]:
        raise HTTPException(500, "Failed to send email. Please try again.")

    return {"sent": True}


@app.post("/api/auth/verify-magic-link")
def verify_magic_link_endpoint(req: VerifyTokenRequest):
    """Verify a magic link token and return the studio's API key."""
    if not req.token:
        raise HTTPException(400, "Token is required")

    result = validate_magic_token(req.token)
    if not result:
        raise HTTPException(401, "Invalid or expired link. Please request a new one.")

    return {
        "api_key": result["api_key"],
        "slug": result["slug"],
        "name": result["name"],
    }


# ═══════════════════════════════════════════════════════════════════════
# ONBOARDING API — No auth required (this IS how they get their API key)
# ═══════════════════════════════════════════════════════════════════════


# ── Step 1: Register Studio ──────────────────────────────────────────

class RegisterStudioRequest(BaseModel):
    name: str
    owner_name: str
    phone: str = ""
    ig_handle: str = ""
    email: str = ""


@app.post("/api/onboarding/register")
def register_studio(req: RegisterStudioRequest):
    """Create a new studio and return its slug + API key."""
    if not req.name.strip():
        raise HTTPException(400, "Studio name is required")
    if not req.owner_name.strip():
        raise HTTPException(400, "Owner name is required")

    # Check for duplicate email
    email = req.email.strip().lower()
    if email:
        existing = get_studio_by_email(email)
        if existing:
            raise HTTPException(409, "An account with this email already exists. Try signing in instead.")

    result = create_studio(
        name=req.name.strip(),
        owner_name=req.owner_name.strip(),
        phone=req.phone.strip(),
        ig_handle=req.ig_handle.strip(),
        email=email,
    )
    return result


# ── Step 2: Services CRUD ────────────────────────────────────────────

class AddServiceRequest(BaseModel):
    name: str
    price: float
    duration_min: int


class UpdateServiceRequest(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    duration_min: Optional[int] = None


@app.post("/api/onboarding/services")
def add_service(req: AddServiceRequest, studio: dict = Depends(get_current_studio)):
    """Add a service to the studio's menu."""
    service_id = create_service(
        studio_id=studio["id"],
        name=req.name.strip(),
        price=req.price,
        duration_min=req.duration_min,
    )
    return {"id": service_id, "name": req.name, "price": req.price, "duration_min": req.duration_min}


@app.get("/api/onboarding/services")
def list_services(studio: dict = Depends(get_current_studio)):
    """List all active services for the studio."""
    return get_services_for_studio(studio["id"])


@app.put("/api/onboarding/services/{service_id}")
def edit_service(service_id: str, req: UpdateServiceRequest, studio: dict = Depends(get_current_studio)):
    """Update a service."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    update_service(service_id, **updates)
    return {"updated": True}


@app.delete("/api/onboarding/services/{service_id}")
def remove_service(service_id: str, studio: dict = Depends(get_current_studio)):
    """Delete a service and its add-ons."""
    delete_service(service_id)
    return {"deleted": True}


# ── Step 3: Add-Ons CRUD ────────────────────────────────────────────

class AddAddonRequest(BaseModel):
    service_id: str
    name: str
    price: float
    duration_min: int
    pitch: str = ""


class UpdateAddonRequest(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    duration_min: Optional[int] = None
    pitch: Optional[str] = None


@app.post("/api/onboarding/addons")
def add_addon(req: AddAddonRequest, studio: dict = Depends(get_current_studio)):
    """Add an add-on to a service."""
    addon_id = create_addon(
        service_id=req.service_id,
        studio_id=studio["id"],
        name=req.name.strip(),
        price=req.price,
        duration_min=req.duration_min,
        pitch=req.pitch.strip(),
    )
    return {"id": addon_id, "name": req.name, "price": req.price}


@app.get("/api/onboarding/addons/{service_id}")
def list_addons(service_id: str, studio: dict = Depends(get_current_studio)):
    """List all add-ons for a specific service."""
    return get_addons_for_service(service_id)


@app.put("/api/onboarding/addons/{addon_id}")
def edit_addon(addon_id: str, req: UpdateAddonRequest, studio: dict = Depends(get_current_studio)):
    """Update an add-on."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    update_addon(addon_id, **updates)
    return {"updated": True}


@app.delete("/api/onboarding/addons/{addon_id}")
def remove_addon(addon_id: str, studio: dict = Depends(get_current_studio)):
    """Delete an add-on."""
    delete_addon(addon_id)
    return {"deleted": True}


# ── Step 4: Policies ─────────────────────────────────────────────────

class PoliciesRequest(BaseModel):
    deposit_amount: Optional[float] = None
    late_fee: Optional[float] = None
    cancel_window_hours: Optional[int] = None
    booking_url: Optional[str] = None


@app.put("/api/onboarding/policies")
def set_policies(req: PoliciesRequest, studio: dict = Depends(get_current_studio)):
    """Update studio policies."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    update_studio(studio["id"], **updates)
    return {"updated": True}


@app.get("/api/onboarding/policies")
def get_policies(studio: dict = Depends(get_current_studio)):
    """Get current studio policies."""
    return {
        "deposit_amount": studio["deposit_amount"],
        "late_fee": studio["late_fee"],
        "cancel_window_hours": studio["cancel_window_hours"],
        "booking_url": studio["booking_url"],
    }


# ── Step 5: Brand Voice ─────────────────────────────────────────────

class BrandVoiceRequest(BaseModel):
    brand_voice: str  # "professional_chill" | "warm_bubbly" | "luxury_exclusive"


@app.get("/api/onboarding/brand-voices")
def list_brand_voices():
    """Return available brand voice presets."""
    return [
        {"key": key, "label": val["label"], "personality": val["personality"][:100] + "..."}
        for key, val in BRAND_VOICE_PROMPTS.items()
    ]


@app.put("/api/onboarding/brand-voice")
def set_brand_voice(req: BrandVoiceRequest, studio: dict = Depends(get_current_studio)):
    """Set the studio's brand voice."""
    if req.brand_voice not in BRAND_VOICE_PROMPTS:
        raise HTTPException(400, f"Invalid voice. Choose from: {list(BRAND_VOICE_PROMPTS.keys())}")
    update_studio(studio["id"], brand_voice=req.brand_voice)
    return {"updated": True, "brand_voice": req.brand_voice}


# ── Step 6: Complete Onboarding ──────────────────────────────────────

@app.post("/api/onboarding/complete")
def complete_onboarding(studio: dict = Depends(get_current_studio)):
    """Mark onboarding as complete."""
    update_studio(studio["id"], onboarding_complete=1)
    return {"onboarding_complete": True, "slug": studio["slug"]}


# ── Studio Config (public by slug) ──────────────────────────────────

@app.get("/api/studio/{slug}")
def get_studio_public(slug: str):
    """Get public studio info by slug (for the onboarding wizard)."""
    studio = get_studio_by_slug(slug)
    if not studio:
        raise HTTPException(404, "Studio not found")
    # Return non-sensitive fields only
    return {
        "name": studio["name"],
        "slug": studio["slug"],
        "owner_name": studio["owner_name"],
        "ig_handle": studio["ig_handle"],
        "brand_voice": studio["brand_voice"],
        "onboarding_complete": bool(studio["onboarding_complete"]),
    }


# ── Live Demo ────────────────────────────────────────────────────────

class DemoRequest(BaseModel):
    message: str
    sender_name: str = "Demo User"


@app.post("/api/onboarding/demo")
def run_demo(req: DemoRequest, studio: dict = Depends(get_current_studio)):
    """
    Run a dry-run Vibe Check using the studio's real config.
    No client records are created. Perfect for the onboarding demo step.
    """
    result = evaluate_lead(
        message=req.message,
        sender_name=req.sender_name,
        sender_ig="demo_user",
        studio_id=studio["id"],
        dry_run=True,
    )
    return result


# ═══════════════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS — Now multi-tenant aware
# ═══════════════════════════════════════════════════════════════════════


# ── Dashboard Metrics ────────────────────────────────────────────────

@app.get("/api/dashboard")
def dashboard(studio: dict = Depends(get_optional_studio)):
    """Return aggregated metrics for the owner dashboard."""
    studio_id = studio["id"] if studio else ""
    metrics = get_dashboard_metrics(studio_id)
    metrics["recent_events"] = get_recent_events(studio_id, limit=20)
    return metrics


@app.get("/api/dashboard/{slug}")
def dashboard_by_slug(slug: str):
    """Return dashboard metrics for a specific studio by slug."""
    studio = get_studio_by_slug(slug)
    if not studio:
        raise HTTPException(404, "Studio not found")
    metrics = get_dashboard_metrics(studio["id"])
    metrics["recent_events"] = get_recent_events(studio["id"], limit=20)
    return metrics


@app.get("/api/dashboard/{slug}/events")
def dashboard_events(slug: str, limit: int = 20):
    """Return recent agent events for a studio's growth feed."""
    studio = get_studio_by_slug(slug)
    if not studio:
        raise HTTPException(404, "Studio not found")
    return get_recent_events(studio["id"], limit=limit)


# ── Vibe Check Endpoints ─────────────────────────────────────────────

class LeadMessage(BaseModel):
    message: str
    sender_name: str = "Unknown"
    sender_ig: str = ""


class PolicyConfirmation(BaseModel):
    client_id: str
    message: str


@app.post("/api/vibe-check")
def vibe_check(lead: LeadMessage, studio: dict = Depends(get_optional_studio)):
    """Evaluate a new lead (e.g., from Instagram DM webhook)."""
    studio_id = studio["id"] if studio else ""
    result = evaluate_lead(
        message=lead.message,
        sender_name=lead.sender_name,
        sender_ig=lead.sender_ig,
        studio_id=studio_id,
    )
    return result


@app.post("/api/vibe-check/confirm")
def vibe_check_confirm(confirmation: PolicyConfirmation, studio: dict = Depends(get_optional_studio)):
    """Evaluate a policy confirmation reply."""
    studio_id = studio["id"] if studio else ""
    result = evaluate_policy_confirmation(
        client_id=confirmation.client_id,
        message=confirmation.message,
        studio_id=studio_id,
    )
    return result


# ── Revenue Engine Endpoints ─────────────────────────────────────────

class UpsellReply(BaseModel):
    booking_id: str
    reply_text: str


@app.post("/api/upsell/process")
def run_upsell_cycle(studio: dict = Depends(get_optional_studio)):
    """Trigger the upsell cycle manually."""
    studio_id = studio["id"] if studio else ""
    results = process_upsell_window(studio_id=studio_id)
    return {"upsells_sent": len(results), "details": results}


@app.post("/api/upsell/reply")
def upsell_reply(reply: UpsellReply, studio: dict = Depends(get_optional_studio)):
    """Handle an inbound SMS reply to an upsell offer."""
    studio_id = studio["id"] if studio else ""
    result = handle_upsell_reply(
        booking_id=reply.booking_id,
        reply_text=reply.reply_text,
        studio_id=studio_id,
    )
    return result


# ── Gap-Filler Endpoints ────────────────────────────────────────────

class CancellationEvent(BaseModel):
    booking_id: str
    service: str
    scheduled_at: str
    original_price: float


class GapFillReply(BaseModel):
    client_id: str
    service: str
    scheduled_at: str
    price: float
    reply_text: str


@app.post("/api/gap-fill/cancel")
def gap_fill_cancel(event: CancellationEvent, studio: dict = Depends(get_optional_studio)):
    """Process a booking cancellation and notify the waitlist."""
    studio_id = studio["id"] if studio else ""
    result = handle_cancellation(
        booking_id=event.booking_id,
        service=event.service,
        scheduled_at=event.scheduled_at,
        original_price=event.original_price,
        studio_id=studio_id,
    )
    return result


@app.post("/api/gap-fill/reply")
def gap_fill_reply(reply: GapFillReply, studio: dict = Depends(get_optional_studio)):
    """Handle an inbound SMS reply from a waitlisted client."""
    studio_id = studio["id"] if studio else ""
    result = handle_gap_fill_reply(
        client_id=reply.client_id,
        service=reply.service,
        scheduled_at=reply.scheduled_at,
        price=reply.price,
        reply_text=reply.reply_text,
        studio_id=studio_id,
    )
    return result


# ── Social Hunter Endpoints ─────────────────────────────────────────

class SocialHunterRunRequest(BaseModel):
    subreddits: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    dry_run: bool = True


@app.get("/api/social-leads")
def list_social_leads(
    status: str = "",
    limit: int = 50,
    studio: dict = Depends(get_current_studio),
):
    """List social leads found by the Social Hunter."""
    return get_social_leads(studio["id"], status=status, limit=limit)


@app.post("/api/social-leads/{lead_id}/approve")
def approve_social_lead(lead_id: str, studio: dict = Depends(get_current_studio)):
    """Approve a social lead and post the drafted reply to Reddit."""
    result = approve_and_reply(lead_id, studio_id=studio["id"])
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@app.post("/api/social-leads/{lead_id}/dismiss")
def dismiss_social_lead(lead_id: str, studio: dict = Depends(get_current_studio)):
    """Dismiss a social lead (don't reply)."""
    result = dismiss_lead(lead_id, studio_id=studio["id"])
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@app.post("/api/social-hunter/run")
def trigger_social_hunter(
    req: SocialHunterRunRequest,
    studio: dict = Depends(get_current_studio),
):
    """Manually trigger a Social Hunter scan for this studio."""
    result = run_social_hunter(
        studio_id=studio["id"],
        dry_run=req.dry_run,
        subreddits=req.subreddits,
        keywords=req.keywords,
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


# ── Twilio Inbound SMS Webhook ───────────────────────────────────────

@app.post("/webhooks/twilio/inbound")
async def twilio_inbound(request: Request):
    """
    Twilio sends POST requests here when an SMS is received.
    Route the reply to the correct agent based on context.
    """
    form = await request.form()
    from_number = form.get("From", "")
    body = form.get("Body", "")
    return {"received": True, "from": from_number, "body": body}


# ── Instagram Webhook ────────────────────────────────────────────────

@app.post("/webhooks/instagram")
async def instagram_webhook(request: Request):
    """Instagram sends webhook events here for new DMs."""
    payload = await request.json()
    entries = payload.get("entry", [])
    for entry in entries:
        messaging = entry.get("messaging", [])
        for msg_event in messaging:
            sender_id = msg_event.get("sender", {}).get("id", "")
            message_text = msg_event.get("message", {}).get("text", "")
            if message_text:
                result = evaluate_lead(
                    message=message_text,
                    sender_name="Instagram User",
                    sender_ig=sender_id,
                )
    return {"status": "ok"}


@app.get("/webhooks/instagram")
async def instagram_webhook_verify(request: Request):
    """Instagram webhook verification (GET request)."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")
