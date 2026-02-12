# Beauty OS — System Architecture

## Agentic Architecture Overview

Beauty OS is an autonomous "Studio Manager" that proactively manages a beauty
professional's business. It uses four AI agents coordinated by a central
orchestrator.

```mermaid
flowchart TD
    subgraph TRIGGERS["External Triggers"]
        IG["Instagram DM / Web Form"]
        SMS_IN["Inbound SMS (Twilio)"]
        CAL["Calendar Event (Bookly PRO)"]
        CRON["Scheduler (24h pre-service)"]
    end

    subgraph ORCHESTRATOR["Beauty OS Orchestrator"]
        ROUTER["Message Router"]
        STATE["State Manager (SQLite/Postgres)"]
    end

    subgraph AGENTS["AI Agent Layer"]
        VC["Vibe Check Agent"]
        RE["Revenue Engine Agent"]
        GF["Gap-Filler Agent"]
        BI["Business Intelligence Agent"]
    end

    subgraph SERVICES["Service Layer"]
        LLM["LLM API (Claude / GPT)"]
        TWILIO["Twilio SMS"]
        BOOKLY["Bookly PRO API"]
        IGAPI["Instagram Graph API"]
    end

    subgraph OUTPUT["Owner Interface"]
        DASH["React Dashboard"]
    end

    %% Trigger → Router
    IG -->|"New DM webhook"| ROUTER
    SMS_IN -->|"Twilio webhook"| ROUTER
    CAL -->|"Booking event"| ROUTER
    CRON -->|"Scheduled tick"| ROUTER

    %% Router → Agents
    ROUTER -->|"New lead"| VC
    ROUTER -->|"24h pre-service"| RE
    ROUTER -->|"Cancellation"| GF
    ROUTER -->|"Dashboard request"| BI

    %% Agents ↔ Services
    VC <-->|"Evaluate lead"| LLM
    VC -->|"Send reply"| IGAPI
    VC -->|"Create booking"| BOOKLY
    VC -->|"Log event"| STATE

    RE <-->|"Draft upsell"| LLM
    RE -->|"Send SMS"| TWILIO
    RE -->|"Update booking"| BOOKLY
    RE -->|"Log revenue"| STATE

    GF -->|"Notify waitlist"| TWILIO
    GF -->|"Fill slot"| BOOKLY
    GF -->|"Log fill"| STATE

    BI -->|"Read metrics"| STATE
    BI -->|"Render"| DASH
```

## Data Flow: Instagram DM → Booking

```mermaid
sequenceDiagram
    participant Client
    participant Instagram
    participant Router as Beauty OS Router
    participant VibeCheck as Vibe Check Agent
    participant LLM as Claude API
    participant Bookly as Bookly PRO
    participant DB as State DB

    Client->>Instagram: Sends DM asking about service
    Instagram->>Router: Webhook fires (new message)
    Router->>VibeCheck: Route to intake agent
    VibeCheck->>LLM: Evaluate message (brand fit + intent)
    LLM-->>VibeCheck: {is_approved, reasoning, draft_reply}

    alt Lead Approved
        VibeCheck->>Instagram: Send policy agreement message
        Client->>Instagram: Confirms deposit policy
        VibeCheck->>LLM: Verify confirmation
        LLM-->>VibeCheck: {confirmed: true}
        VibeCheck->>Bookly: Generate booking link
        VibeCheck->>Instagram: Send booking link
        VibeCheck->>DB: Log approved lead
    else Lead Filtered
        VibeCheck->>Instagram: Send polite decline / redirect
        VibeCheck->>DB: Log filtered lead + reason
    end
```

## Data Models

### Client Record
| Field            | Type     | Description                        |
|------------------|----------|------------------------------------|
| id               | UUID     | Primary key                        |
| name             | string   | Client display name                |
| phone            | string   | For SMS (E.164 format)             |
| instagram_handle | string   | IG username                        |
| intake_status    | enum     | pending / approved / declined      |
| vibe_score       | float    | 0.0–1.0 brand-fit score            |
| intake_reasoning | text     | LLM explanation                    |
| created_at       | datetime | First contact                      |

### Booking Record
| Field          | Type     | Description                          |
|----------------|----------|--------------------------------------|
| id             | UUID     | Primary key                          |
| client_id      | UUID     | FK → Client                          |
| service        | string   | Primary service booked               |
| add_ons        | json     | Array of upsell add-ons accepted     |
| original_price | decimal  | Base price                           |
| final_price    | decimal  | After add-ons                        |
| scheduled_at   | datetime | Appointment time                     |
| status         | enum     | confirmed / cancelled / completed    |
| source         | enum     | instagram / web / referral           |

### Waitlist Entry
| Field        | Type     | Description                         |
|--------------|----------|-------------------------------------|
| id           | UUID     | Primary key                         |
| client_id    | UUID     | FK → Client                         |
| service      | string   | Desired service                     |
| preferred_at | datetime | Preferred time window               |
| notified     | boolean  | Already contacted for a gap?        |

### Agent Event Log
| Field      | Type     | Description                           |
|------------|----------|---------------------------------------|
| id         | UUID     | Primary key                           |
| agent      | enum     | vibe_check / revenue / gap_filler     |
| action     | string   | What the agent did                    |
| metadata   | json     | Context (client_id, revenue, etc.)    |
| created_at | datetime | Timestamp                             |
