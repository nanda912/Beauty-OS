"""
Beauty OS — Email Service (Resend)

Sends magic link emails for passwordless authentication.
Free tier: 100 emails/day — more than enough for MVP.
"""

import resend
from config.settings import RESEND_API_KEY, FRONTEND_URL, STUDIO_NAME


def send_magic_link(to_email: str, token: str, studio_name: str = "") -> dict:
    """
    Send a magic link email via Resend.

    Returns {"sent": True} on success or {"sent": False, "error": "..."} on failure.
    """
    if not RESEND_API_KEY:
        return {"sent": False, "error": "RESEND_API_KEY not configured"}

    resend.api_key = RESEND_API_KEY

    verify_url = f"{FRONTEND_URL}/auth/verify?token={token}"
    display_name = studio_name or STUDIO_NAME

    try:
        resend.Emails.send({
            "from": f"Beauty OS <onboarding@resend.dev>",
            "to": [to_email],
            "subject": f"Sign in to {display_name} — Beauty OS",
            "html": _magic_link_html(verify_url, display_name),
        })
        return {"sent": True}
    except Exception as e:
        return {"sent": False, "error": str(e)}


def _magic_link_html(verify_url: str, studio_name: str) -> str:
    """Minimal, branded magic link email template."""
    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 480px; margin: 0 auto; padding: 40px 20px;">
        <h2 style="color: #2D2D2D; font-size: 24px; margin-bottom: 8px;">
            Beauty <span style="color: #C9A96E;">OS</span>
        </h2>
        <p style="color: #666; font-size: 14px; margin-bottom: 32px;">
            {studio_name}
        </p>

        <p style="color: #333; font-size: 16px; line-height: 1.5;">
            Click the button below to sign in to your dashboard. This link expires in 15 minutes.
        </p>

        <div style="text-align: center; margin: 32px 0;">
            <a href="{verify_url}"
               style="display: inline-block; padding: 14px 32px; background: #C9A96E;
                      color: #fff; text-decoration: none; border-radius: 12px;
                      font-weight: 600; font-size: 16px;">
                Sign In to Dashboard
            </a>
        </div>

        <p style="color: #999; font-size: 13px; line-height: 1.5;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{verify_url}" style="color: #C9A96E; word-break: break-all;">{verify_url}</a>
        </p>

        <hr style="border: none; border-top: 1px solid #F5C6C6; margin: 32px 0;">

        <p style="color: #bbb; font-size: 12px;">
            If you didn't request this email, you can safely ignore it.
        </p>
    </div>
    """
