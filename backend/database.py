"""
Beauty OS — Database Layer (SQLite, upgradeable to Postgres)

Provides async-friendly data access for all agents.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

from config.settings import DB_PATH


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


def init_db():
    """Create all tables if they don't exist."""
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS clients (
                id              TEXT PRIMARY KEY,
                name            TEXT,
                phone           TEXT,
                instagram_handle TEXT,
                intake_status   TEXT DEFAULT 'pending'
                                    CHECK(intake_status IN ('pending','approved','declined')),
                vibe_score      REAL DEFAULT 0.0,
                intake_reasoning TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id              TEXT PRIMARY KEY,
                client_id       TEXT REFERENCES clients(id),
                service         TEXT NOT NULL,
                add_ons         TEXT DEFAULT '[]',
                original_price  REAL NOT NULL,
                final_price     REAL NOT NULL,
                scheduled_at    TEXT NOT NULL,
                status          TEXT DEFAULT 'confirmed'
                                    CHECK(status IN ('confirmed','cancelled','completed')),
                source          TEXT DEFAULT 'instagram'
                                    CHECK(source IN ('instagram','web','referral')),
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS waitlist (
                id              TEXT PRIMARY KEY,
                client_id       TEXT REFERENCES clients(id),
                service         TEXT NOT NULL,
                preferred_at    TEXT,
                notified        INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS agent_events (
                id              TEXT PRIMARY KEY,
                agent           TEXT NOT NULL
                                    CHECK(agent IN ('vibe_check','revenue','gap_filler','system')),
                action          TEXT NOT NULL,
                metadata        TEXT DEFAULT '{}',
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_bookings_scheduled
                ON bookings(scheduled_at);
            CREATE INDEX IF NOT EXISTS idx_bookings_status
                ON bookings(status);
            CREATE INDEX IF NOT EXISTS idx_waitlist_service
                ON waitlist(service, notified);
        """)


# ── Helper functions ─────────────────────────────────────────────────

def new_id() -> str:
    return str(uuid.uuid4())


def create_client(name: str, phone: str = "", instagram_handle: str = "") -> str:
    client_id = new_id()
    with get_db() as db:
        db.execute(
            "INSERT INTO clients (id, name, phone, instagram_handle) VALUES (?, ?, ?, ?)",
            (client_id, name, phone, instagram_handle),
        )
    return client_id


def update_client_intake(client_id: str, status: str, vibe_score: float, reasoning: str):
    with get_db() as db:
        db.execute(
            "UPDATE clients SET intake_status=?, vibe_score=?, intake_reasoning=? WHERE id=?",
            (status, vibe_score, reasoning, client_id),
        )


def create_booking(
    client_id: str,
    service: str,
    price: float,
    scheduled_at: str,
    source: str = "instagram",
) -> str:
    booking_id = new_id()
    with get_db() as db:
        db.execute(
            """INSERT INTO bookings
               (id, client_id, service, original_price, final_price, scheduled_at, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (booking_id, client_id, service, price, price, scheduled_at, source),
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


def get_upcoming_bookings_in_window(hours_from_now: int = 24):
    """Return bookings scheduled within `hours_from_now` hours that are confirmed."""
    with get_db() as db:
        rows = db.execute(
            """SELECT b.*, c.name AS client_name, c.phone AS client_phone
               FROM bookings b
               JOIN clients c ON c.id = b.client_id
               WHERE b.status = 'confirmed'
                 AND b.scheduled_at BETWEEN datetime('now')
                     AND datetime('now', ? || ' hours')""",
            (str(hours_from_now),),
        ).fetchall()
    return [dict(r) for r in rows]


def add_to_waitlist(client_id: str, service: str, preferred_at: str = "") -> str:
    entry_id = new_id()
    with get_db() as db:
        db.execute(
            "INSERT INTO waitlist (id, client_id, service, preferred_at) VALUES (?, ?, ?, ?)",
            (entry_id, client_id, service, preferred_at),
        )
    return entry_id


def get_waitlist_for_service(service: str):
    with get_db() as db:
        rows = db.execute(
            """SELECT w.*, c.name AS client_name, c.phone AS client_phone
               FROM waitlist w
               JOIN clients c ON c.id = w.client_id
               WHERE w.service = ? AND w.notified = 0
               ORDER BY w.created_at ASC""",
            (service,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_waitlist_notified(entry_id: str):
    with get_db() as db:
        db.execute("UPDATE waitlist SET notified=1 WHERE id=?", (entry_id,))


def log_event(agent: str, action: str, metadata: dict | None = None):
    with get_db() as db:
        db.execute(
            "INSERT INTO agent_events (id, agent, action, metadata) VALUES (?, ?, ?, ?)",
            (new_id(), agent, action, json.dumps(metadata or {})),
        )


def get_dashboard_metrics() -> dict:
    """Aggregate metrics for the owner dashboard."""
    with get_db() as db:
        # Found Money: sum of (final_price - original_price) for all bookings with add-ons
        found_money = db.execute(
            "SELECT COALESCE(SUM(final_price - original_price), 0) AS total FROM bookings"
        ).fetchone()["total"]

        # AI-handled chats
        ai_chats = db.execute(
            "SELECT COUNT(*) AS total FROM agent_events WHERE agent='vibe_check'"
        ).fetchone()["total"]

        # Leads approved vs filtered
        approved = db.execute(
            "SELECT COUNT(*) AS total FROM clients WHERE intake_status='approved'"
        ).fetchone()["total"]
        declined = db.execute(
            "SELECT COUNT(*) AS total FROM clients WHERE intake_status='declined'"
        ).fetchone()["total"]

        # Gap fills
        gap_fills = db.execute(
            "SELECT COUNT(*) AS total FROM agent_events WHERE agent='gap_filler' AND action='slot_filled'"
        ).fetchone()["total"]

    return {
        "found_money": round(found_money, 2),
        "ai_chats": ai_chats,
        "hours_reclaimed": round(ai_chats * 10 / 60, 1),  # 10 min per chat → hours
        "leads_approved": approved,
        "leads_filtered": declined,
        "gap_fills": gap_fills,
    }
