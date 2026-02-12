"""
Beauty OS — Simple API Key Authentication

Reads X-API-Key header and returns the studio row or raises 401.
Also supports slug-based public lookups (no auth needed for onboarding).
"""

from fastapi import Header, HTTPException, Depends
from backend.database import get_studio_by_api_key, get_default_studio


async def get_current_studio(x_api_key: str = Header(default="")):
    """
    FastAPI dependency: require a valid API key.
    Returns the studio dict or raises 401.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    studio = get_studio_by_api_key(x_api_key)
    if not studio:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return studio


async def get_optional_studio(x_api_key: str = Header(default="")):
    """
    FastAPI dependency: optionally authenticate.
    Returns the studio dict if key provided, or the default studio, or None.
    """
    if x_api_key:
        studio = get_studio_by_api_key(x_api_key)
        if studio:
            return studio
    # Fall back to default studio for backward compatibility
    return get_default_studio()
