"""
Beauty OS — Scheduled Tasks

Runs periodic tasks:
- Every hour: check for bookings in the upsell window and send SMS.
- Every 2 hours: run Social Hunter scan for all studios.
- Designed to run as a standalone process or via cron/task scheduler.
"""

import time
import schedule
from backend.database import init_db
from backend.agents.revenue_engine import process_upsell_window
from backend.agents.social_hunter import run_social_hunter_all_studios


def run_upsell_check():
    """Process the upsell window — find upcoming bookings and send offers."""
    print(f"[Scheduler] Running upsell check...")
    results = process_upsell_window()
    print(f"[Scheduler] Sent {len(results)} upsell(s).")
    for r in results:
        print(f"  - {r['client_name']}: {r['addon_offered']} (${r['addon_price']})")


def run_social_hunter_scan():
    """Scan Reddit for beauty service leads across all studios."""
    print("[Scheduler] Running Social Hunter scan...")
    results = run_social_hunter_all_studios()
    for r in results:
        if "error" in r:
            print(f"  - Studio {r['studio_id'][:8]}...: {r['error']}")
        else:
            print(f"  - Studio {r['studio_id'][:8]}...: {r.get('leads_saved', 0)} leads saved")
    print(f"[Scheduler] Social Hunter scan complete. {len(results)} studio(s) processed.")


def main():
    """Start the scheduler loop."""
    init_db()
    print("[Scheduler] Beauty OS scheduler started.")
    print("[Scheduler] Upsell check runs every hour.")
    print("[Scheduler] Social Hunter scan runs every 2 hours.")

    # Run immediately on start, then on schedule
    run_upsell_check()
    schedule.every(1).hours.do(run_upsell_check)

    run_social_hunter_scan()
    schedule.every(2).hours.do(run_social_hunter_scan)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
