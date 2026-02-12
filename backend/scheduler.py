"""
Beauty OS — Scheduled Tasks

Runs periodic tasks:
- Every hour: check for bookings in the upsell window and send SMS.
- Designed to run as a standalone process or via cron/task scheduler.
"""

import time
import schedule
from backend.database import init_db
from backend.agents.revenue_engine import process_upsell_window


def run_upsell_check():
    """Process the upsell window — find upcoming bookings and send offers."""
    print(f"[Scheduler] Running upsell check...")
    results = process_upsell_window()
    print(f"[Scheduler] Sent {len(results)} upsell(s).")
    for r in results:
        print(f"  - {r['client_name']}: {r['addon_offered']} (${r['addon_price']})")


def main():
    """Start the scheduler loop."""
    init_db()
    print("[Scheduler] Beauty OS scheduler started.")
    print(f"[Scheduler] Upsell check runs every hour.")

    # Run immediately on start, then every hour
    run_upsell_check()
    schedule.every(1).hours.do(run_upsell_check)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
