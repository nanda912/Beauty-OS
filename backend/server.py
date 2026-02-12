"""
Beauty OS — FastAPI Server

Central API that connects all agents, webhooks, and the dashboard.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from backend.database import init_db, get_dashboard_metrics
from backend.agents.vibe_check import evaluate_lead, evaluate_policy_confirmation
from backend.agents.revenue_engine import process_upsell_window, handle_upsell_reply
from backend.agents.gap_filler import handle_cancellation, handle_gap_fill_reply

app = FastAPI(title="Beauty OS", version="1.0.0")

# Allow the React dashboard to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ── Health Check ─────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "beauty-os"}


# ── Dashboard Metrics ────────────────────────────────────────────────

@app.get("/api/dashboard")
def dashboard():
    """Return aggregated metrics for the owner dashboard."""
    return get_dashboard_metrics()


# ── Vibe Check Endpoints ─────────────────────────────────────────────

class LeadMessage(BaseModel):
    message: str
    sender_name: str = "Unknown"
    sender_ig: str = ""


class PolicyConfirmation(BaseModel):
    client_id: str
    message: str


@app.post("/api/vibe-check")
def vibe_check(lead: LeadMessage):
    """Evaluate a new lead (e.g., from Instagram DM webhook)."""
    result = evaluate_lead(
        message=lead.message,
        sender_name=lead.sender_name,
        sender_ig=lead.sender_ig,
    )
    return result


@app.post("/api/vibe-check/confirm")
def vibe_check_confirm(confirmation: PolicyConfirmation):
    """Evaluate a policy confirmation reply."""
    result = evaluate_policy_confirmation(
        client_id=confirmation.client_id,
        message=confirmation.message,
    )
    return result


# ── Revenue Engine Endpoints ─────────────────────────────────────────

class UpsellReply(BaseModel):
    booking_id: str
    reply_text: str


@app.post("/api/upsell/process")
def run_upsell_cycle():
    """
    Trigger the upsell cycle manually (or call from scheduler).
    Finds all bookings in the 24h window and sends upsell SMS.
    """
    results = process_upsell_window()
    return {"upsells_sent": len(results), "details": results}


@app.post("/api/upsell/reply")
def upsell_reply(reply: UpsellReply):
    """Handle an inbound SMS reply to an upsell offer."""
    result = handle_upsell_reply(
        booking_id=reply.booking_id,
        reply_text=reply.reply_text,
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
def gap_fill_cancel(event: CancellationEvent):
    """Process a booking cancellation and notify the waitlist."""
    result = handle_cancellation(
        booking_id=event.booking_id,
        service=event.service,
        scheduled_at=event.scheduled_at,
        original_price=event.original_price,
    )
    return result


@app.post("/api/gap-fill/reply")
def gap_fill_reply(reply: GapFillReply):
    """Handle an inbound SMS reply from a waitlisted client."""
    result = handle_gap_fill_reply(
        client_id=reply.client_id,
        service=reply.service,
        scheduled_at=reply.scheduled_at,
        price=reply.price,
        reply_text=reply.reply_text,
    )
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
    # In production, look up the pending context for this phone number
    # to determine if this is an upsell reply or gap-fill reply.
    return {"received": True, "from": from_number, "body": body}


# ── Instagram Webhook ────────────────────────────────────────────────

@app.post("/webhooks/instagram")
async def instagram_webhook(request: Request):
    """
    Instagram sends webhook events here for new DMs.
    """
    payload = await request.json()
    # Extract message from Instagram webhook payload
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
                # In production, send the draft_reply back via Instagram API
    return {"status": "ok"}


@app.get("/webhooks/instagram")
async def instagram_webhook_verify(request: Request):
    """Instagram webhook verification (GET request)."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    # Verify against your configured verify token
    if mode == "subscribe" and token:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")
