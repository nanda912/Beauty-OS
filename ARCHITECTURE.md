# Beauty OS — Architecture Diagram

```
                            beauty-os.vercel.app
                         +-----------------------+
                         |    VERCEL (Frontend)   |
                         |   React + Vite + TW    |
                         +-----------+-----------+
                                     |
                           /api/* rewrites
                                     |
                                     v
                    web-production-8369d9.up.railway.app
              +------------------------------------------+
              |         RAILWAY (Backend)                 |
              |         FastAPI + SQLite                  |
              |         Python 3.11                       |
              +------------------------------------------+
              |                                          |
              |   server.py (39 routes)                  |
              |      |                                   |
              |      +--- Auth (magic link)              |
              |      +--- Onboarding (6-step wizard)     |
              |      +--- Dashboard (metrics + events)   |
              |      +--- Vibe Check (lead screening)    |
              |      +--- Revenue Engine (upselling)     |
              |      +--- Gap-Filler (waitlist)          |
              |      +--- Social Hunter (Reddit leads)   |
              |      +--- Webhooks (Twilio, Instagram)   |
              |                                          |
              +------------------------------------------+


============================================================
                   SYSTEM ARCHITECTURE
============================================================


   +-------------------+     +-------------------+     +-------------------+
   |   LANDING PAGE    |     |   LOGIN PAGE      |     |   AUTH VERIFY     |
   |   /               |     |   /login          |     |   /auth/verify    |
   |                   |     |                   |     |                   |
   | Registration form |     | Email input       |     | Token validation  |
   | -> POST /register |     | -> Magic link     |     | -> Store API key  |
   | -> Get API key    |     |    via Resend     |     | -> Redirect       |
   +--------+----------+     +-------------------+     +-------------------+
            |
            v
   +-------------------+
   |  ONBOARDING       |
   |  /onboard/:slug   |
   |                   |
   | Step 1: Services  |
   | Step 2: Add-ons   |
   | Step 3: Policies  |
   | Step 4: Voice     |
   | Step 5: Demo      |
   | Step 6: Complete  |
   +--------+----------+
            |
            v
   +----------------------------------------------+
   |           DASHBOARD  /dashboard/:slug         |
   |                                               |
   |  +----------+ +----------+ +-------+ +------+ |
   |  | Clients  | | Found $  | | Hours | |Growth| |
   |  | Acquired | | (upsell) | | Saved | |Score | |
   |  +----------+ +----------+ +-------+ +------+ |
   |                                               |
   |  +-------------------+ +--------------------+ |
   |  | Acquisition       | | AI Growth Activity | |
   |  | Funnel            | | Feed (real-time)   | |
   |  | (approved vs      | | - Lead events      | |
   |  |  filtered chart)  | | - Upsell events    | |
   |  +-------------------+ | - Gap fill events  | |
   |                        | - Social leads     | |
   |  +-------------------+ +--------------------+ |
   |  | Social Leads      |                        |
   |  | Panel             |                        |
   |  | - Filter tabs     |                        |
   |  | - Lead cards      |                        |
   |  | - Approve/Dismiss |                        |
   |  +-------------------+                        |
   +-----------------------------------------------+


============================================================
              THE 4 AI AGENTS — Data Flow
============================================================


  AGENT 1: SOCIAL HUNTER (Lead Generation)
  =========================================

  Reddit (PRAW)                    Gemini LLM
       |                               |
       v                               v
  +-----------+    keywords     +-------------+
  | Search    |  ------------> | Evaluate     |
  | r/Atlanta |  "wax", "lash" | Relevance    |
  | r/Beauty  |                | Score 0-1    |
  +-----------+                | Draft Reply  |
       |                       +------+------+
       | raw posts                    |
       v                              v
  +------------------+         +------------------+
  | Filter duplicates|         | Save to          |
  | (seen post IDs)  |         | social_leads     |
  +------------------+         | status = 'new'   |
                               +--------+---------+
                                        |
                               Owner reviews in Dashboard
                                        |
                          +-------------+-------------+
                          |                           |
                    [Approve]                    [Dismiss]
                          |                           |
                    Post reply                  status = 'dismissed'
                    to Reddit
                          |
                    status = 'replied'

  Schedule: Every 2 hours (dry_run = true, never auto-posts)


  AGENT 2: VIBE CHECK (Lead Screening / Gatekeeper)
  ===================================================

  Instagram DM                     Gemini LLM
  (webhook)                            |
       |                               v
       v                        +-------------+
  +-----------+   message  -->  | Evaluate     |
  | Incoming  |                 | Vibe Score   |
  | DM from   |                 | 0.0 - 1.0   |
  | prospect  |                 | Intent type  |
  +-----------+                 | Draft reply  |
                                +------+------+
                                       |
                           +-----------+-----------+
                           |                       |
                     vibe >= 0.7              vibe < 0.7
                     is_approved              is_declined
                           |                       |
                           v                       v
                   +---------------+       +---------------+
                   | Create client |       | Create client |
                   | status=       |       | status=       |
                   | 'approved'    |       | 'declined'    |
                   +-------+-------+       +---------------+
                           |
                   Require deposit
                   policy confirmation?
                           |
                     +-----+-----+
                     |           |
                   [Yes]       [No]
                     |           |
              Ask to confirm   Send booking
              deposit policy   link directly
                     |
              Client confirms
                     |
              Send booking link

  Trigger: Instagram webhook POST /webhooks/instagram
           or manual POST /api/vibe-check


  AGENT 3: REVENUE ENGINE (Upselling)
  =====================================

  Bookings DB                      Gemini LLM
       |                               |
       v                               v
  +-----------+                 +-------------+
  | Find      |   booking +    | Draft SMS    |
  | bookings  |   best addon   | personalized |
  | in 24-hr  |  ----------->  | upsell pitch |
  | window    |                 | < 160 chars  |
  +-----------+                 | brand voice  |
                                +------+------+
                                       |
                                       v
                                +-------------+
                                | Send SMS    |
                                | via Twilio  |
                                +------+------+
                                       |
                             Client replies via SMS
                                       |
                          +------------+------------+
                          |                         |
                      "YES"                      "NO"
                          |                         |
                   +------+-------+          Log decline
                   | Add add-on   |
                   | to booking   |
                   | final_price  |
                   | += addon $   |
                   +--------------+

  Schedule: Every 1 hour via scheduler.py
  Example: "Hey Sarah! Add a $15 nose wax to tomorrow's Brazilian? YES/NO"


  AGENT 4: GAP-FILLER (Cancellation Recovery)
  =============================================

  Cancellation Event               Waitlist DB
       |                               |
       v                               v
  +-----------+                 +-------------+
  | Booking   |   same service  | Find people |
  | cancelled |  ------------> | waiting for  |
  | by client |                 | this service |
  +-----------+                 +------+------+
                                       |
                                       v
                                +-------------+
                                | Send SMS    |
                                | "Slot open! |
                                |  Want it?"  |
                                | via Twilio  |
                                +------+------+
                                       |
                             Client replies via SMS
                                       |
                          +------------+------------+
                          |                         |
                      "YES"                      "NO"
                          |                         |
                   +------+-------+          Try next person
                   | Create new   |          on waitlist
                   | booking for  |
                   | open slot    |
                   +--------------+

  Trigger: POST /api/gap-fill/cancel (from booking system)


============================================================
                  DATABASE SCHEMA
============================================================

  studios ──────< services ──────< service_addons
     |
     +──────< clients ──────< bookings
     |
     +──────< waitlist
     |
     +──────< agent_events
     |
     +──────< magic_tokens
     |
     +──────< social_leads


  9 Tables:
  +-----------------+----------------------------------------------+
  | studios         | Tenant: name, slug, api_key, brand_voice,    |
  |                 | deposit, late_fee, booking_url, email         |
  +-----------------+----------------------------------------------+
  | services        | Menu: name, price, duration (per studio)     |
  +-----------------+----------------------------------------------+
  | service_addons  | Upsells: name, price, duration, pitch        |
  +-----------------+----------------------------------------------+
  | clients         | Leads: name, phone, IG, vibe_score, status   |
  +-----------------+----------------------------------------------+
  | bookings        | Appts: service, price, scheduled_at, status  |
  +-----------------+----------------------------------------------+
  | waitlist        | Queue: client + service + preferred time      |
  +-----------------+----------------------------------------------+
  | agent_events    | Audit: agent, action, metadata (JSON)        |
  +-----------------+----------------------------------------------+
  | magic_tokens    | Auth: token, 15-min expiry, used flag        |
  +-----------------+----------------------------------------------+
  | social_leads    | Reddit: post, score, reply draft, status     |
  +-----------------+----------------------------------------------+


============================================================
               EXTERNAL SERVICES
============================================================

  +------------------+     +------------------+     +------------------+
  | Google Gemini    |     | Twilio           |     | Resend           |
  | 2.0 Flash Lite   |     | SMS Gateway      |     | Email Service    |
  |                  |     |                  |     |                  |
  | - Vibe scoring   |     | - Upsell texts   |     | - Magic link     |
  | - Reply drafting |     | - Gap-fill SMS   |     |   login emails   |
  | - Upsell copy    |     | - Inbound SMS    |     |                  |
  | - Lead eval      |     |   webhook        |     | Free: 100/day    |
  |                  |     |                  |     |                  |
  | Free tier        |     | Pay-per-use      |     +------------------+
  +------------------+     +------------------+
                                                    +------------------+
  +------------------+     +------------------+     | UptimeRobot      |
  | Reddit (PRAW)    |     | Instagram        |     | Health Monitor   |
  | API              |     | Graph API        |     |                  |
  |                  |     |                  |     | Pings /health    |
  | - Subreddit      |     | - DM webhooks    |     | every 5 min to   |
  |   search         |     | - Reply to DMs   |     | prevent Railway  |
  | - Post replies   |     |                  |     | cold starts      |
  |                  |     |                  |     |                  |
  | Free, unlimited  |     | Free tier        |     | Free: 50 monitors|
  +------------------+     +------------------+     +------------------+


============================================================
           AUTHENTICATION & MULTI-TENANCY
============================================================

  New User:
    Register -> API key generated -> stored in localStorage
                                     stored in studios.api_key (DB)

  Returning User:
    Enter email -> Magic link (15-min token via Resend)
               -> Click link -> Token validated
               -> API key returned -> stored in localStorage

  Every API call:
    Header: X-API-Key: {api_key}
       |
       v
    get_current_studio() -> lookup studios WHERE api_key=?
       |
       v
    studio_id used to filter ALL queries (multi-tenant isolation)


============================================================
            SCHEDULER (Background Jobs)
============================================================

  +----------------------------------------------------------+
  |  scheduler.py (runs as separate process)                  |
  |                                                          |
  |  on startup:                                             |
  |    -> run_upsell_check()      immediately                |
  |    -> run_social_hunter_scan() immediately               |
  |                                                          |
  |  then loop:                                              |
  |    every 1 hour  -> run_upsell_check()                   |
  |                     (find bookings in window, send SMS)  |
  |                                                          |
  |    every 2 hours -> run_social_hunter_scan()              |
  |                     (scan Reddit for all studios)        |
  |                                                          |
  |  while True:                                             |
  |    schedule.run_pending()                                |
  |    time.sleep(60)                                        |
  +----------------------------------------------------------+


============================================================
              FILE TREE (Key Files)
============================================================

  Beauty OS/
  +-- backend/
  |   +-- server.py            # FastAPI app, 39 routes
  |   +-- database.py          # SQLite, 9 tables, all CRUD
  |   +-- auth.py              # API key auth middleware
  |   +-- scheduler.py         # Background jobs (hourly + 2hr)
  |   +-- studio_config.py     # Brand voice presets + config loader
  |   +-- agents/
  |   |   +-- vibe_check.py    # Lead screening (Gatekeeper)
  |   |   +-- revenue_engine.py # Upsell SMS agent
  |   |   +-- gap_filler.py    # Waitlist recovery agent
  |   |   +-- social_hunter.py # Reddit lead generation agent
  |   +-- services/
  |       +-- llm.py           # Gemini/Claude/GPT wrapper
  |       +-- sms.py           # Twilio SMS
  |       +-- email.py         # Resend magic links
  |       +-- reddit.py        # PRAW Reddit API
  |       +-- instagram.py     # Instagram Graph API
  |       +-- bookly.py        # Bookly PRO (future)
  +-- config/
  |   +-- settings.py          # All env vars
  +-- dashboard/
  |   +-- src/
  |   |   +-- App.jsx          # Router (5 routes)
  |   |   +-- pages/
  |   |       +-- LandingPage.jsx      # Marketing + registration
  |   |       +-- LoginPage.jsx        # Passwordless login
  |   |       +-- AuthVerify.jsx       # Magic link verify
  |   |       +-- OnboardingWizard.jsx # 6-step setup
  |   |       +-- Dashboard.jsx        # Analytics + Social Leads
  |   +-- vercel.json          # Vercel deploy config
  +-- data/
  |   +-- beauty_os.db         # SQLite database
  +-- railway.json             # Railway deploy config
  +-- Dockerfile               # Backend container
  +-- requirements.txt         # Python deps (13 packages)
  +-- .env.example             # Template for env vars
```
