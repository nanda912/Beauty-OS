"""
Beauty OS — Central Configuration

All secrets are loaded from environment variables.
Copy .env.example to .env and fill in your keys.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "beauty_os.db"

# ── LLM ──────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # "gemini", "anthropic", or "openai"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")

# ── Twilio (SMS) ─────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# ── Instagram Graph API ──────────────────────────────────────────────
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
IG_PAGE_ID = os.getenv("IG_PAGE_ID", "")

# ── Bookly PRO ───────────────────────────────────────────────────────
BOOKLY_API_URL = os.getenv("BOOKLY_API_URL", "https://yourdomain.com/wp-json/bookly/v1")
BOOKLY_API_KEY = os.getenv("BOOKLY_API_KEY", "")

# ── Business Rules ───────────────────────────────────────────────────
DEPOSIT_AMOUNT = float(os.getenv("DEPOSIT_AMOUNT", "25.00"))
LATE_FEE = float(os.getenv("LATE_FEE", "15.00"))
UPSELL_LEAD_TIME_HOURS = int(os.getenv("UPSELL_LEAD_TIME_HOURS", "24"))
BOOKING_URL = os.getenv("BOOKING_URL", "https://yourdomain.com/book")

# ── Brand Voice ──────────────────────────────────────────────────────
STUDIO_NAME = os.getenv("STUDIO_NAME", "The Beauty Studio")
STUDIO_VIBE = os.getenv("STUDIO_VIBE", "professional, particular, chill")

# ── Email (Magic Link Auth) ─────────────────────────────────────────
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://beauty-os.vercel.app")
