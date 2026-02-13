"""
Beauty OS — Database Layer (SQLite, upgradeable to Postgres)

Multi-tenant: every record belongs to a studio via studio_id.
"""

import sqlite3
import json
import uuid
import secrets
import re
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager

from config.settings import DB_PATH, STUDIO_NAME, DEPOSIT_AMOUNT, LATE_FEE


def _ensure_db_dir():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db():
    """Yield a SQLite connection with row_factory set."""
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def new_id() -> str:
    return str(uuid.uuid4())


def _generate_slug(name: str) -> str:
    """Turn 'Nails by Nina' into 'nails-by-nina'."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "studio"


def _generate_api_key() -> str:
    return secrets.token_hex(24)


# ── Schema & Migration ───────────────────────────────────────────────

def init_db():
    """Create all tables. Safe to call multiple times."""
    with get_db() as db:
        db.executescript("""
            -- ── Studios (the tenant) ────────────────────────────
            CREATE TABLE IF NOT EXISTS studios (
                id                  TEXT PRIMARY KEY,
                slug                TEXT UNIQUE NOT NULL,
                api_key             TEXT UNIQUE NOT NULL,
                name                TEXT NOT NULL,
                owner_name          TEXT NOT NULL DEFAULT '',
                phone               TEXT DEFAULT '',
                ig_handle           TEXT DEFAULT '',
                brand_voice         TEXT DEFAULT 'professional_chill'
                                        CHECK(brand_voice IN (
                                            'professional_chill',
                                            'warm_bubbly',
                                            'luxury_exclusive'
                                        )),
                deposit_amount      REAL DEFAULT 25.00,
                late_fee            REAL DEFAULT 15.00,
                cancel_window_hours INTEGER DEFAULT 24,
                booking_url         TEXT DEFAULT '',
                onboarding_complete INTEGER DEFAULT 0,
                created_at          TEXT DEFAULT (datetime('now'))
            );

            -- ── Services per studio ─────────────────────────────
            CREATE TABLE IF NOT EXISTS services (
                id          TEXT PRIMARY KEY,
                studio_id   TEXT NOT NULL REFERENCES studios(id),
                name        TEXT NOT NULL,
                price       REAL NOT NULL,
                duration_min INTEGER NOT NULL,
                active      INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_services_studio ON services(studio_id);

            -- ── Add-ons per service ─────────────────────────────
            CREATE TABLE IF NOT EXISTS service_addons (
                id          TEXT PRIMARY KEY,
                service_id  TEXT NOT NULL REFERENCES services(id),
                studio_id   TEXT NOT NULL REFERENCES studios(id),
                name        TEXT NOT NULL,
                price       REAL NOT NULL,
                duration_min INTEGER NOT NULL,
                pitch       TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_addons_service ON service_addons(service_id);
            CREATE INDEX IF NOT EXISTS idx_addons_studio ON service_addons(studio_id);

            -- ── Clients ─────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS clients (
                id              TEXT PRIMARY KEY,
                studio_id       TEXT REFERENCES studios(id),
                name            TEXT,
                phone           TEXT,
                instagram_handle TEXT,
                intake_status   TEXT DEFAULT 'pending'
                                    CHECK(intake_status IN ('pending','approved','declined')),
                vibe_score      REAL DEFAULT 0.0,
                intake_reasoning TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_clients_studio ON clients(studio_id);

            -- ── Bookings ────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS bookings (
                id              TEXT PRIMARY KEY,
                studio_id       TEXT REFERENCES studios(id),
                client_id       TEXT REFERENCES clients(id),
                service         TEXT NOT NULL,
                add_ons         TEXT DEFAULT '[]',
                original_price  REAL NOT NULL,
                final_price     REAL NOT NULL,
                scheduled_at    TEXT NOT NULL,
                status          TEXT DEFAULT 'confirmed'
                                    CHECK(status IN ('confirmed','cancelled','completed')),
                source          TEXT DEFAULT 'instagram'
                                    CHECK(source IN ('instagram','web','referral','waitlist')),
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_bookings_scheduled ON bookings(scheduled_at);
            CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
            CREATE INDEX IF NOT EXISTS idx_bookings_studio ON bookings(studio_id);

            -- ── Waitlist ────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS waitlist (
                id          TEXT PRIMARY KEY,
                studio_id   TEXT REFERENCES studios(id),
                client_id   TEXT REFERENCES clients(id),
                service     TEXT NOT NULL,
                preferred_at TEXT,
                notified    INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_waitlist_service ON waitlist(service, notified);
            CREATE INDEX IF NOT EXISTS idx_waitlist_studio ON waitlist(studio_id);

            -- ── Agent Events ────────────────────────────────────
            CREATE TABLE IF NOT EXISTS agent_events (
                id          TEXT PRIMARY KEY,
                studio_id   TEXT REFERENCES studios(id),
                agent       TEXT NOT NULL
                                CHECK(agent IN ('vibe_check','revenue','gap_filler','social_hunter','system')),
                action      TEXT NOT NULL,
                metadata    TEXT DEFAULT '{}',
                created_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_events_studio ON agent_events(studio_id);

            -- ── Magic Link Tokens ─────────────────────────────────
            CREATE TABLE IF NOT EXISTS magic_tokens (
                id          TEXT PRIMARY KEY,
                studio_id   TEXT NOT NULL REFERENCES studios(id),
                token       TEXT UNIQUE NOT NULL,
                expires_at  TEXT NOT NULL,
                used        INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            -- ── Social Leads (Social Hunter) ─────────────────────
            CREATE TABLE IF NOT EXISTS social_leads (
                id              TEXT PRIMARY KEY,
                studio_id       TEXT NOT NULL REFERENCES studios(id),
                platform        TEXT NOT NULL DEFAULT 'reddit'
                                    CHECK(platform IN ('reddit','instagram','twitter')),
                post_id         TEXT NOT NULL,
                post_url        TEXT DEFAULT '',
                post_title      TEXT DEFAULT '',
                post_body       TEXT DEFAULT '',
                subreddit       TEXT DEFAULT '',
                author          TEXT DEFAULT '',
                match_score     REAL DEFAULT 0.0,
                match_reasoning TEXT DEFAULT '',
                drafted_reply   TEXT DEFAULT '',
                status          TEXT DEFAULT 'new'
                                    CHECK(status IN ('new','approved','replied','dismissed','failed')),
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_social_leads_studio ON social_leads(studio_id);
            CREATE INDEX IF NOT EXISTS idx_social_leads_status ON social_leads(studio_id, status);
            CREATE INDEX IF NOT EXISTS idx_social_leads_post_id ON social_leads(post_id);
        """)

    # ── Migrations (safe to re-run) ────────────────────────────────
    _migrate_add_email_column()
    _migrate_add_social_hunter()

    # Seed default studio if none exist
    _seed_default_studio()


def _migrate_add_email_column():
    """Add email column to studios if it doesn't exist yet."""
    with get_db() as db:
        # Check if column exists
        cols = [row[1] for row in db.execute("PRAGMA table_info(studios)").fetchall()]
        if "email" not in cols:
            db.execute("ALTER TABLE studios ADD COLUMN email TEXT DEFAULT ''")
            db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_studios_email ON studios(email) WHERE email != ''"
            )


def _migrate_add_social_hunter():
    """Create social_leads table if it doesn't exist yet (for existing databases)."""
    with get_db() as db:
        tables = [row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        if "social_leads" not in tables:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS social_leads (
                    id              TEXT PRIMARY KEY,
                    studio_id       TEXT NOT NULL REFERENCES studios(id),
                    platform        TEXT NOT NULL DEFAULT 'reddit'
                                        CHECK(platform IN ('reddit','instagram','twitter')),
                    post_id         TEXT NOT NULL,
                    post_url        TEXT DEFAULT '',
                    post_title      TEXT DEFAULT '',
                    post_body       TEXT DEFAULT '',
                    subreddit       TEXT DEFAULT '',
                    author          TEXT DEFAULT '',
                    match_score     REAL DEFAULT 0.0,
                    match_reasoning TEXT DEFAULT '',
                    drafted_reply   TEXT DEFAULT '',
                    status          TEXT DEFAULT 'new'
                                        CHECK(status IN ('new','approved','replied','dismissed','failed')),
                    created_at      TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_social_leads_studio ON social_leads(studio_id);
                CREATE INDEX IF NOT EXISTS idx_social_leads_status ON social_leads(studio_id, status);
                CREATE INDEX IF NOT EXISTS idx_social_leads_post_id ON social_leads(post_id);
            """)


def _seed_default_studio():
    """Create a default studio from .env values if no studios exist."""
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) AS c FROM studios").fetchone()["c"]
        if count == 0:
            studio_id = new_id()
            slug = _generate_slug(STUDIO_NAME)
            api_key = _generate_api_key()
            db.execute(
                """INSERT INTO studios
                   (id, slug, api_key, name, owner_name, deposit_amount, late_fee, onboarding_complete)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                (studio_id, slug, api_key, STUDIO_NAME, "Owner", DEPOSIT_AMOUNT, LATE_FEE),
            )


# ── Studio CRUD ──────────────────────────────────────────────────────

def create_studio(name: str, owner_name: str, phone: str = "", ig_handle: str = "", email: str = "") -> dict:
    studio_id = new_id()
    base_slug = _generate_slug(name)
    api_key = _generate_api_key()

    # Handle slug collisions
    slug = base_slug
    with get_db() as db:
        existing = db.execute("SELECT COUNT(*) AS c FROM studios WHERE slug=?", (slug,)).fetchone()["c"]
        if existing > 0:
            slug = f"{base_slug}-{secrets.token_hex(3)}"

        db.execute(
            """INSERT INTO studios (id, slug, api_key, name, owner_name, phone, ig_handle, email)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (studio_id, slug, api_key, name, owner_name, phone, ig_handle, email),
        )

    return {"id": studio_id, "slug": slug, "api_key": api_key, "name": name}


def get_studio_by_slug(slug: str) -> dict | None:
    with get_db() as db:
        row = db.execute("SELECT * FROM studios WHERE slug=?", (slug,)).fetchone()
    return dict(row) if row else None


def get_studio_by_api_key(api_key: str) -> dict | None:
    with get_db() as db:
        row = db.execute("SELECT * FROM studios WHERE api_key=?", (api_key,)).fetchone()
    return dict(row) if row else None


def get_default_studio() -> dict | None:
    with get_db() as db:
        row = db.execute("SELECT * FROM studios ORDER BY created_at ASC LIMIT 1").fetchone()
    return dict(row) if row else None


def update_studio(studio_id: str, **fields):
    allowed = {"name", "owner_name", "phone", "ig_handle", "brand_voice",
               "deposit_amount", "late_fee", "cancel_window_hours", "booking_url",
               "onboarding_complete", "email"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [studio_id]
    with get_db() as db:
        db.execute(f"UPDATE studios SET {set_clause} WHERE id=?", values)


# ── Service CRUD ─────────────────────────────────────────────────────

def create_service(studio_id: str, name: str, price: float, duration_min: int) -> str:
    service_id = new_id()
    with get_db() as db:
        db.execute(
            "INSERT INTO services (id, studio_id, name, price, duration_min) VALUES (?, ?, ?, ?, ?)",
            (service_id, studio_id, name, price, duration_min),
        )
    return service_id


def get_services_for_studio(studio_id: str) -> list[dict]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM services WHERE studio_id=? AND active=1 ORDER BY created_at",
            (studio_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_service(service_id: str, **fields):
    allowed = {"name", "price", "duration_min", "active"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [service_id]
    with get_db() as db:
        db.execute(f"UPDATE services SET {set_clause} WHERE id=?", values)


def delete_service(service_id: str):
    with get_db() as db:
        db.execute("DELETE FROM service_addons WHERE service_id=?", (service_id,))
        db.execute("DELETE FROM services WHERE id=?", (service_id,))


# ── Add-on CRUD ──────────────────────────────────────────────────────

def create_addon(service_id: str, studio_id: str, name: str, price: float, duration_min: int, pitch: str = "") -> str:
    addon_id = new_id()
    with get_db() as db:
        db.execute(
            """INSERT INTO service_addons (id, service_id, studio_id, name, price, duration_min, pitch)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (addon_id, service_id, studio_id, name, price, duration_min, pitch),
        )
    return addon_id


def get_addons_for_service(service_id: str) -> list[dict]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM service_addons WHERE service_id=? ORDER BY created_at",
            (service_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_addons_for_studio(studio_id: str) -> list[dict]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM service_addons WHERE studio_id=? ORDER BY created_at",
            (studio_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_addon(addon_id: str, **fields):
    allowed = {"name", "price", "duration_min", "pitch"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [addon_id]
    with get_db() as db:
        db.execute(f"UPDATE service_addons SET {set_clause} WHERE id=?", values)


def delete_addon(addon_id: str):
    with get_db() as db:
        db.execute("DELETE FROM service_addons WHERE id=?", (addon_id,))


# ── Client helpers (now with studio_id) ──────────────────────────────

def create_client(name: str, phone: str = "", instagram_handle: str = "", studio_id: str = "") -> str:
    client_id = new_id()
    with get_db() as db:
        db.execute(
            "INSERT INTO clients (id, studio_id, name, phone, instagram_handle) VALUES (?, ?, ?, ?, ?)",
            (client_id, studio_id or None, name, phone, instagram_handle),
        )
    return client_id


def update_client_intake(client_id: str, status: str, vibe_score: float, reasoning: str):
    with get_db() as db:
        db.execute(
            "UPDATE clients SET intake_status=?, vibe_score=?, intake_reasoning=? WHERE id=?",
            (status, vibe_score, reasoning, client_id),
        )


# ── Booking helpers (now with studio_id) ─────────────────────────────

def create_booking(
    client_id: str,
    service: str,
    price: float,
    scheduled_at: str,
    source: str = "instagram",
    studio_id: str = "",
) -> str:
    booking_id = new_id()
    with get_db() as db:
        db.execute(
            """INSERT INTO bookings
               (id, studio_id, client_id, service, original_price, final_price, scheduled_at, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (booking_id, studio_id or None, client_id, service, price, price, scheduled_at, source),
        )
    return booking_id


def add_upsell_to_booking(booking_id: str, add_on_name: str, add_on_price: float):
    with get_db() as db:
        row = db.execute("SELECT add_ons, final_price FROM bookings WHERE id=?", (booking_id,)).fetchone()
        if not row:
            return
        current_addons = json.loads(row["add_ons"])
        current_addons.append({"name": add_on_name, "price": add_on_price})
        new_price = row["final_price"] + add_on_price
        db.execute(
            "UPDATE bookings SET add_ons=?, final_price=? WHERE id=?",
            (json.dumps(current_addons), new_price, booking_id),
        )


def cancel_booking(booking_id: str):
    with get_db() as db:
        db.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,))


def get_upcoming_bookings_in_window(hours_from_now: int = 24, studio_id: str = ""):
    with get_db() as db:
        if studio_id:
            rows = db.execute(
                """SELECT b.*, c.name AS client_name, c.phone AS client_phone
                   FROM bookings b JOIN clients c ON c.id = b.client_id
                   WHERE b.studio_id=? AND b.status = 'confirmed'
                     AND b.scheduled_at BETWEEN datetime('now') AND datetime('now', ? || ' hours')""",
                (studio_id, str(hours_from_now)),
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT b.*, c.name AS client_name, c.phone AS client_phone
                   FROM bookings b JOIN clients c ON c.id = b.client_id
                   WHERE b.status = 'confirmed'
                     AND b.scheduled_at BETWEEN datetime('now') AND datetime('now', ? || ' hours')""",
                (str(hours_from_now),),
            ).fetchall()
    return [dict(r) for r in rows]


# ── Waitlist helpers (now with studio_id) ────────────────────────────

def add_to_waitlist(client_id: str, service: str, preferred_at: str = "", studio_id: str = "") -> str:
    entry_id = new_id()
    with get_db() as db:
        db.execute(
            "INSERT INTO waitlist (id, studio_id, client_id, service, preferred_at) VALUES (?, ?, ?, ?, ?)",
            (entry_id, studio_id or None, client_id, service, preferred_at),
        )
    return entry_id


def get_waitlist_for_service(service: str, studio_id: str = ""):
    with get_db() as db:
        if studio_id:
            rows = db.execute(
                """SELECT w.*, c.name AS client_name, c.phone AS client_phone
                   FROM waitlist w JOIN clients c ON c.id = w.client_id
                   WHERE w.studio_id=? AND w.service = ? AND w.notified = 0
                   ORDER BY w.created_at ASC""",
                (studio_id, service),
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT w.*, c.name AS client_name, c.phone AS client_phone
                   FROM waitlist w JOIN clients c ON c.id = w.client_id
                   WHERE w.service = ? AND w.notified = 0
                   ORDER BY w.created_at ASC""",
                (service,),
            ).fetchall()
    return [dict(r) for r in rows]


def mark_waitlist_notified(entry_id: str):
    with get_db() as db:
        db.execute("UPDATE waitlist SET notified=1 WHERE id=?", (entry_id,))


# ── Event logging (now with studio_id) ───────────────────────────────

def log_event(agent: str, action: str, metadata: dict | None = None, studio_id: str = ""):
    with get_db() as db:
        db.execute(
            "INSERT INTO agent_events (id, studio_id, agent, action, metadata) VALUES (?, ?, ?, ?, ?)",
            (new_id(), studio_id or None, agent, action, json.dumps(metadata or {})),
        )


# ── Dashboard metrics (now filterable by studio) ─────────────────────

def get_recent_events(studio_id: str = "", limit: int = 20) -> list[dict]:
    """Get recent agent events for the growth activity feed."""
    with get_db() as db:
        if studio_id:
            rows = db.execute(
                """SELECT id, agent, action, metadata, created_at
                   FROM agent_events WHERE studio_id=?
                   ORDER BY created_at DESC LIMIT ?""",
                (studio_id, limit),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT id, agent, action, metadata, created_at FROM agent_events ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    result = []
    for r in rows:
        entry = dict(r)
        entry["metadata"] = json.loads(entry["metadata"]) if entry["metadata"] else {}
        result.append(entry)
    return result


# ── Magic Link Auth ──────────────────────────────────────────────────

def get_studio_by_email(email: str) -> dict | None:
    """Look up a studio by its owner's email address."""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM studios WHERE email=? AND email != ''", (email.lower().strip(),)
        ).fetchone()
    return dict(row) if row else None


def create_magic_token(studio_id: str) -> str:
    """Generate a magic link token with 15-minute expiry. Returns the token string."""
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as db:
        db.execute(
            "INSERT INTO magic_tokens (id, studio_id, token, expires_at) VALUES (?, ?, ?, ?)",
            (new_id(), studio_id, token, expires_at),
        )
    return token


def validate_magic_token(token: str) -> dict | None:
    """
    Check a magic link token. If valid (exists, not used, not expired),
    mark it used and return the studio dict. Otherwise return None.
    """
    with get_db() as db:
        row = db.execute(
            """SELECT mt.*, s.api_key, s.slug, s.name AS studio_name, s.id AS sid
               FROM magic_tokens mt
               JOIN studios s ON s.id = mt.studio_id
               WHERE mt.token=? AND mt.used=0 AND mt.expires_at > datetime('now')""",
            (token,),
        ).fetchone()
        if not row:
            return None
        # Mark token as used
        db.execute("UPDATE magic_tokens SET used=1 WHERE id=?", (row["id"],))
    return {
        "studio_id": row["sid"],
        "api_key": row["api_key"],
        "slug": row["slug"],
        "name": row["studio_name"],
    }


def cleanup_expired_tokens():
    """Delete magic tokens that are expired or already used. Safe to call on startup."""
    with get_db() as db:
        db.execute(
            "DELETE FROM magic_tokens WHERE used=1 OR expires_at < datetime('now')"
        )


# ── Social Leads (Social Hunter) ─────────────────────────────────

def save_social_lead(
    studio_id: str,
    platform: str,
    post_id: str,
    post_url: str = "",
    post_title: str = "",
    post_body: str = "",
    subreddit: str = "",
    author: str = "",
    match_score: float = 0.0,
    match_reasoning: str = "",
    drafted_reply: str = "",
    status: str = "new",
) -> str:
    """Save a social lead found by the Social Hunter."""
    lead_id = new_id()
    with get_db() as db:
        db.execute(
            """INSERT INTO social_leads
               (id, studio_id, platform, post_id, post_url, post_title, post_body,
                subreddit, author, match_score, match_reasoning, drafted_reply, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (lead_id, studio_id, platform, post_id, post_url, post_title, post_body,
             subreddit, author, match_score, match_reasoning, drafted_reply, status),
        )
    return lead_id


def get_social_leads(studio_id: str, status: str = "", limit: int = 50) -> list[dict]:
    """Get social leads for a studio, optionally filtered by status."""
    with get_db() as db:
        if status:
            rows = db.execute(
                """SELECT * FROM social_leads
                   WHERE studio_id=? AND status=?
                   ORDER BY created_at DESC LIMIT ?""",
                (studio_id, status, limit),
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT * FROM social_leads
                   WHERE studio_id=?
                   ORDER BY created_at DESC LIMIT ?""",
                (studio_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def get_social_lead_by_id(lead_id: str) -> dict | None:
    """Get a single social lead by its ID."""
    with get_db() as db:
        row = db.execute("SELECT * FROM social_leads WHERE id=?", (lead_id,)).fetchone()
    return dict(row) if row else None


def update_social_lead_status(lead_id: str, status: str):
    """Update the status of a social lead."""
    with get_db() as db:
        db.execute(
            "UPDATE social_leads SET status=? WHERE id=?",
            (status, lead_id),
        )


def is_post_already_seen(studio_id: str, post_id: str) -> bool:
    """Check if a Reddit post has already been processed for a studio."""
    with get_db() as db:
        count = db.execute(
            "SELECT COUNT(*) AS c FROM social_leads WHERE studio_id=? AND post_id=?",
            (studio_id, post_id),
        ).fetchone()["c"]
    return count > 0


# ── Dashboard metrics (now filterable by studio) ─────────────────────

def get_dashboard_metrics(studio_id: str = "") -> dict:
    with get_db() as db:
        where = "WHERE studio_id=?" if studio_id else ""
        params = (studio_id,) if studio_id else ()

        found_money = db.execute(
            f"SELECT COALESCE(SUM(final_price - original_price), 0) AS total FROM bookings {where}",
            params,
        ).fetchone()["total"]

        evt_where = f"WHERE studio_id=? AND agent='vibe_check'" if studio_id else "WHERE agent='vibe_check'"
        ai_chats = db.execute(
            f"SELECT COUNT(*) AS total FROM agent_events {evt_where}",
            params,
        ).fetchone()["total"]

        cl_where = f"WHERE studio_id=? AND intake_status='approved'" if studio_id else "WHERE intake_status='approved'"
        approved = db.execute(
            f"SELECT COUNT(*) AS total FROM clients {cl_where}",
            params,
        ).fetchone()["total"]

        cl_dec_where = f"WHERE studio_id=? AND intake_status='declined'" if studio_id else "WHERE intake_status='declined'"
        declined = db.execute(
            f"SELECT COUNT(*) AS total FROM clients {cl_dec_where}",
            params,
        ).fetchone()["total"]

        gf_where = f"WHERE studio_id=? AND agent='gap_filler' AND action='slot_filled'" if studio_id else "WHERE agent='gap_filler' AND action='slot_filled'"
        gap_fills = db.execute(
            f"SELECT COUNT(*) AS total FROM agent_events {gf_where}",
            params,
        ).fetchone()["total"]

        sh_where = f"WHERE studio_id=? AND agent='social_hunter' AND action='lead_found'" if studio_id else "WHERE agent='social_hunter' AND action='lead_found'"
        social_leads_found = db.execute(
            f"SELECT COUNT(*) AS total FROM agent_events {sh_where}",
            params,
        ).fetchone()["total"]

    return {
        "found_money": round(found_money, 2),
        "ai_chats": ai_chats,
        "hours_reclaimed": round(ai_chats * 10 / 60, 1),
        "leads_approved": approved,
        "leads_filtered": declined,
        "gap_fills": gap_fills,
        "social_leads_found": social_leads_found,
    }
