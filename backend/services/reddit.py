"""
Beauty OS — Reddit Service (Social Hunter)

Searches subreddits for beauty service recommendations using PRAW.
Free tier: unlimited reads, rate-limited writes.
"""

import praw
from config.settings import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    REDDIT_USERNAME,
    REDDIT_PASSWORD,
)


def _get_reddit_client(read_only: bool = True) -> praw.Reddit:
    """Initialize and return a PRAW Reddit instance."""
    if read_only or not REDDIT_USERNAME:
        return praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
    else:
        return praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            username=REDDIT_USERNAME,
            password=REDDIT_PASSWORD,
        )


def search_subreddits(
    subreddits: list[str],
    keywords: list[str],
    limit: int = 25,
    time_filter: str = "week",
) -> list[dict]:
    """
    Search multiple subreddits for posts matching beauty service keywords.

    Args:
        subreddits: List of subreddit names (e.g., ["Atlanta", "atlbeauty"])
        keywords: List of search terms (e.g., ["wax", "lash", "nail salon"])
        limit: Max results per subreddit per keyword
        time_filter: "hour", "day", "week", "month", "year", "all"

    Returns:
        List of dicts with post info.
    """
    if not REDDIT_CLIENT_ID:
        print("[Social Hunter] REDDIT_CLIENT_ID not configured — skipping Reddit search.")
        return []

    reddit = _get_reddit_client(read_only=True)
    results = []
    seen_ids = set()

    for sub_name in subreddits:
        try:
            subreddit = reddit.subreddit(sub_name)
            for keyword in keywords:
                for post in subreddit.search(keyword, limit=limit, time_filter=time_filter):
                    if post.id in seen_ids:
                        continue
                    seen_ids.add(post.id)
                    results.append({
                        "id": post.id,
                        "fullname": post.fullname,  # e.g., "t3_abc123"
                        "title": post.title,
                        "selftext": post.selftext[:2000],  # Truncate long posts
                        "url": f"https://reddit.com{post.permalink}",
                        "subreddit": sub_name,
                        "author": str(post.author) if post.author else "[deleted]",
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "created_utc": post.created_utc,
                    })
        except Exception as e:
            print(f"[Social Hunter] Error searching r/{sub_name}: {e}")
            continue

    return results


def reply_to_post(post_id: str, reply_text: str) -> dict:
    """
    Post a reply to a Reddit submission.
    Requires REDDIT_USERNAME and REDDIT_PASSWORD to be set.

    Args:
        post_id: The Reddit post ID (without prefix, e.g., "abc123")
        reply_text: The comment body to post

    Returns:
        Dict with comment_id and permalink on success, or error info.
    """
    if not REDDIT_USERNAME or not REDDIT_PASSWORD:
        return {"posted": False, "error": "Reddit credentials not configured for posting."}

    try:
        reddit = _get_reddit_client(read_only=False)
        submission = reddit.submission(id=post_id)
        comment = submission.reply(reply_text)
        return {
            "posted": True,
            "comment_id": comment.id,
            "permalink": f"https://reddit.com{comment.permalink}",
        }
    except Exception as e:
        return {"posted": False, "error": str(e)}


def reply_to_post_dry_run(post_id: str, reply_text: str) -> dict:
    """Simulate posting a Reddit reply (for testing without credentials)."""
    print(f"[DRY RUN Reddit] Post ID: {post_id}")
    print(f"[DRY RUN Reddit] Reply: {reply_text[:200]}")
    return {"posted": False, "dry_run": True, "post_id": post_id}
