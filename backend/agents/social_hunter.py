"""
Beauty OS — Social Hunter Agent (Multi-Tenant)

Scans Reddit for people in the studio's area looking for beauty services.
Uses LLM to evaluate relevance and draft helpful, non-spammy replies.

Output Schema (per post evaluation):
{
    "is_relevant": bool,
    "match_score": float (0.0-1.0),
    "reasoning": str,
    "drafted_reply": str
}
"""

from backend.services.llm import call_llm_json
from backend.services.reddit import search_subreddits, reply_to_post
from backend.database import (
    save_social_lead,
    is_post_already_seen,
    get_social_lead_by_id,
    update_social_lead_status,
    log_event,
)
from backend.studio_config import get_studio_config, get_services_menu


# ── Default Keywords ────────────────────────────────────────────────

DEFAULT_KEYWORDS = [
    "wax recommendation",
    "lash tech",
    "nail salon",
    "beauty salon recommendation",
    "who does waxing",
    "looking for esthetician",
    "need a facial",
    "brow threading",
    "recommend beauty",
]


# ── Prompt Builder ──────────────────────────────────────────────────

def _build_evaluation_prompt(config: dict) -> str:
    """Build the Social Hunter evaluation prompt from studio config."""
    studio = config["studio"]
    voice = config["brand_voice"]
    services_menu = get_services_menu(config)

    return f"""You are the Social Hunter AI for "{studio['name']}".

Your job is to evaluate social media posts to determine if the person is looking
for beauty services that {studio['name']} offers, and if so, draft a helpful reply.

STUDIO SERVICES:
{services_menu}

STUDIO PERSONALITY:
{voice['personality']}

EVALUATION CRITERIA:
1. Is the person asking for or looking for a beauty service that this studio offers?
2. Do they seem to be in or near the studio's area? (If location is unclear, give benefit of the doubt.)
3. Is this a genuine recommendation request (not spam, ads, or self-promotion)?

IMPORTANT RULES FOR THE DRAFTED REPLY:
- Be genuinely helpful FIRST. Answer their question, give useful advice.
- Mention the studio naturally as a recommendation, NOT as a hard sell.
- Do NOT sound like an ad or bot. Sound like a real person who happens to know a great place.
- Keep it concise (2-4 sentences max).
- Include the studio name: "{studio['name']}"
- If the studio has a booking URL, you may include it naturally: {studio.get('booking_url', '')}
- Match the studio's tone: {voice['personality'][:100]}

RESPOND WITH VALID JSON ONLY:
{{
    "is_relevant": true/false,
    "match_score": 0.0-1.0,
    "reasoning": "Brief explanation of why this post is or isn't a match",
    "drafted_reply": "The Reddit comment to post (only if is_relevant is true, otherwise empty string)"
}}

If is_relevant is false, set match_score to the relevance level anyway (for analytics)
and drafted_reply to an empty string."""


# ── Agent Logic ─────────────────────────────────────────────────────

def run_social_hunter(
    studio_id: str,
    dry_run: bool = True,
    subreddits: list[str] | None = None,
    keywords: list[str] | None = None,
    limit_per_search: int = 10,
) -> dict:
    """
    Main Social Hunter scan cycle for a single studio.

    Args:
        studio_id: The studio to hunt for.
        dry_run: If True, draft replies but never post them to Reddit.
        subreddits: Override subreddit list.
        keywords: Override keyword list.
        limit_per_search: Max posts per subreddit-keyword combo from Reddit API.

    Returns:
        Summary dict with counts of found, relevant, and saved leads.
    """
    # Load studio config
    config = get_studio_config(studio_id)
    if not config:
        return {"error": "Studio not found", "studio_id": studio_id}

    # Determine subreddits and keywords
    if not subreddits:
        subreddits = _get_studio_subreddits(config["studio"])
    if not keywords:
        keywords = _get_studio_keywords(config)

    if not subreddits:
        log_event(
            agent="social_hunter",
            action="scan_skipped",
            metadata={"reason": "No subreddits configured"},
            studio_id=studio_id,
        )
        return {"error": "No subreddits configured for this studio."}

    # Step 1: Search Reddit
    raw_posts = search_subreddits(
        subreddits=subreddits,
        keywords=keywords,
        limit=limit_per_search,
        time_filter="week",
    )

    log_event(
        agent="social_hunter",
        action="scan_started",
        metadata={
            "subreddits": subreddits,
            "keywords": keywords[:5],
            "raw_posts_found": len(raw_posts),
        },
        studio_id=studio_id,
    )

    # Step 2: Filter out already-seen posts
    new_posts = []
    for post in raw_posts:
        if not is_post_already_seen(studio_id, post["fullname"]):
            new_posts.append(post)

    if not new_posts:
        log_event(
            agent="social_hunter",
            action="scan_complete",
            metadata={"new_posts": 0, "message": "No new posts to evaluate"},
            studio_id=studio_id,
        )
        return {
            "raw_found": len(raw_posts),
            "new_posts": 0,
            "leads_saved": 0,
        }

    # Step 3: Evaluate each post with LLM
    system_prompt = _build_evaluation_prompt(config)
    leads_saved = 0
    leads_relevant = 0

    for post in new_posts:
        try:
            result = call_llm_json(
                system_prompt=system_prompt,
                user_message=(
                    f"Subreddit: r/{post['subreddit']}\n"
                    f"Title: {post['title']}\n"
                    f"Body: {post['selftext'][:1000]}\n"
                    f"Author: u/{post['author']}\n"
                    f"Score: {post['score']} upvotes, {post['num_comments']} comments"
                ),
            )
        except Exception as e:
            print(f"[Social Hunter] LLM error for post {post['id']}: {e}")
            # Save as dismissed so we don't re-process it
            save_social_lead(
                studio_id=studio_id,
                platform="reddit",
                post_id=post["fullname"],
                post_url=post["url"],
                post_title=post["title"],
                post_body=post["selftext"][:2000],
                subreddit=post["subreddit"],
                author=post["author"],
                match_score=0.0,
                match_reasoning=f"LLM evaluation failed: {e}",
                drafted_reply="",
                status="dismissed",
            )
            continue

        is_relevant = result.get("is_relevant", False)
        match_score = result.get("match_score", 0.0)

        if is_relevant and match_score >= 0.5:
            leads_relevant += 1
            lead_id = save_social_lead(
                studio_id=studio_id,
                platform="reddit",
                post_id=post["fullname"],
                post_url=post["url"],
                post_title=post["title"],
                post_body=post["selftext"][:2000],
                subreddit=post["subreddit"],
                author=post["author"],
                match_score=match_score,
                match_reasoning=result.get("reasoning", ""),
                drafted_reply=result.get("drafted_reply", ""),
                status="new",
            )
            leads_saved += 1

            log_event(
                agent="social_hunter",
                action="lead_found",
                metadata={
                    "lead_id": lead_id,
                    "post_url": post["url"],
                    "subreddit": post["subreddit"],
                    "match_score": match_score,
                    "dry_run": dry_run,
                },
                studio_id=studio_id,
            )
        else:
            # Save as dismissed so we don't re-scan this post
            save_social_lead(
                studio_id=studio_id,
                platform="reddit",
                post_id=post["fullname"],
                post_url=post["url"],
                post_title=post["title"],
                post_body=post["selftext"][:500],
                subreddit=post["subreddit"],
                author=post["author"],
                match_score=match_score,
                match_reasoning=result.get("reasoning", ""),
                drafted_reply="",
                status="dismissed",
            )

    log_event(
        agent="social_hunter",
        action="scan_complete",
        metadata={
            "raw_found": len(raw_posts),
            "new_posts": len(new_posts),
            "leads_relevant": leads_relevant,
            "leads_saved": leads_saved,
        },
        studio_id=studio_id,
    )

    return {
        "raw_found": len(raw_posts),
        "new_posts": len(new_posts),
        "leads_relevant": leads_relevant,
        "leads_saved": leads_saved,
    }


def approve_and_reply(lead_id: str, studio_id: str = "") -> dict:
    """
    Approve a social lead and post the drafted reply to Reddit.
    Called when the studio owner clicks "Approve" in the dashboard.
    """
    lead = get_social_lead_by_id(lead_id)
    if not lead:
        return {"error": "Lead not found"}
    if lead["status"] != "new":
        return {"error": f"Lead status is '{lead['status']}', expected 'new'"}

    # Update status to approved first
    update_social_lead_status(lead_id, "approved")

    # Post the reply to Reddit
    post_id = lead["post_id"].replace("t3_", "")  # PRAW expects ID without prefix
    result = reply_to_post(post_id, lead["drafted_reply"])

    if result.get("posted"):
        update_social_lead_status(lead_id, "replied")
        log_event(
            agent="social_hunter",
            action="reply_posted",
            metadata={
                "lead_id": lead_id,
                "comment_id": result.get("comment_id"),
                "post_url": lead["post_url"],
            },
            studio_id=studio_id or lead["studio_id"],
        )
        return {"replied": True, "comment_id": result.get("comment_id")}
    else:
        update_social_lead_status(lead_id, "failed")
        log_event(
            agent="social_hunter",
            action="reply_failed",
            metadata={
                "lead_id": lead_id,
                "error": result.get("error", "Unknown"),
            },
            studio_id=studio_id or lead["studio_id"],
        )
        return {"replied": False, "error": result.get("error")}


def dismiss_lead(lead_id: str, studio_id: str = "") -> dict:
    """Dismiss a social lead (owner decided not to reply)."""
    lead = get_social_lead_by_id(lead_id)
    if not lead:
        return {"error": "Lead not found"}

    update_social_lead_status(lead_id, "dismissed")
    log_event(
        agent="social_hunter",
        action="lead_dismissed",
        metadata={"lead_id": lead_id},
        studio_id=studio_id or lead["studio_id"],
    )
    return {"dismissed": True}


# ── Config Helpers ──────────────────────────────────────────────────

def _get_studio_subreddits(studio: dict) -> list[str]:
    """
    Get the subreddit list for a studio.
    For MVP: returns empty (must be passed via API).
    Future: stored in studio config column.
    """
    import json
    raw = studio.get("target_subreddits", "[]")
    try:
        subs = json.loads(raw) if isinstance(raw, str) else raw
        return subs if subs else []
    except Exception:
        return []


def _get_studio_keywords(config: dict) -> list[str]:
    """
    Build keyword list from the studio's services + defaults.
    E.g., if they offer "Brazilian Wax", keywords include "brazilian wax", "waxing", etc.
    """
    keywords = list(DEFAULT_KEYWORDS)
    for svc in config.get("services", []):
        svc_name = svc["name"].lower()
        if svc_name not in keywords:
            keywords.append(svc_name)
        # Also add individual words for broader matching
        for word in svc_name.split():
            if len(word) > 3 and word not in keywords:
                keywords.append(word)
    return keywords


# ── Scheduled Runner ────────────────────────────────────────────────

def run_social_hunter_all_studios():
    """
    Run Social Hunter for ALL studios that have onboarding complete.
    Called by the scheduler every 2 hours.
    """
    from backend.database import get_db

    with get_db() as db:
        rows = db.execute(
            "SELECT id FROM studios WHERE onboarding_complete=1"
        ).fetchall()

    results = []
    for row in rows:
        studio_id = row["id"]
        try:
            result = run_social_hunter(studio_id=studio_id, dry_run=True)
            results.append({"studio_id": studio_id, **result})
        except Exception as e:
            print(f"[Social Hunter] Error for studio {studio_id}: {e}")
            results.append({"studio_id": studio_id, "error": str(e)})

    return results
