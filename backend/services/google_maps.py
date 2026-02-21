"""
Beauty OS -- Google Maps Service (Social Hunter)

Searches for competing beauty businesses near a location and pulls
their negative reviews using the Google Places API (New).
Free tier: $200/month credit (~40,000 place detail requests).
"""

import requests
from config.settings import (
    GOOGLE_MAPS_API_KEY,
    GOOGLE_MAPS_SEARCH_RADIUS,
    GOOGLE_MAPS_BUSINESS_TYPES,
)

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


# ── Geocoding ────────────────────────────────────────────────────────

def geocode_location(location: str) -> dict | None:
    """
    Convert a location string (zip code, city name) to lat/lng.

    Args:
        location: e.g., "30301" or "Atlanta, GA"

    Returns:
        {"lat": float, "lng": float} or None if geocoding fails.
    """
    if not GOOGLE_MAPS_API_KEY:
        print("[Google Maps] GOOGLE_MAPS_API_KEY not configured -- skipping.")
        return None

    try:
        resp = requests.get(GEOCODE_URL, params={
            "address": location,
            "key": GOOGLE_MAPS_API_KEY,
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("results"):
            geo = data["results"][0]["geometry"]["location"]
            return {"lat": geo["lat"], "lng": geo["lng"]}
        return None
    except Exception as e:
        print(f"[Google Maps] Geocode error for '{location}': {e}")
        return None


# ── Place Search ─────────────────────────────────────────────────────

def search_nearby_businesses(
    lat: float,
    lng: float,
    business_types: list[str] | None = None,
    radius: int | None = None,
    max_results: int = 20,
) -> list[dict]:
    """
    Search for beauty businesses near a location using Places API (New).

    Args:
        lat, lng: Center coordinates.
        business_types: e.g., ["beauty_salon", "hair_salon"]
        radius: Search radius in meters.
        max_results: Max number of places to return (max 20).

    Returns:
        List of dicts: {"place_id", "name", "address", "rating", "user_ratings_total"}
    """
    if not GOOGLE_MAPS_API_KEY:
        print("[Google Maps] GOOGLE_MAPS_API_KEY not configured -- skipping.")
        return []

    types = business_types or GOOGLE_MAPS_BUSINESS_TYPES
    search_radius = radius or GOOGLE_MAPS_SEARCH_RADIUS

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount",
    }

    body = {
        "includedTypes": types,
        "maxResultCount": min(max_results, 20),
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(search_radius),
            }
        },
    }

    try:
        resp = requests.post(PLACES_SEARCH_URL, json=body, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[Google Maps] Nearby search error: {e}")
        return []

    results = []
    for place in data.get("places", []):
        results.append({
            "place_id": place.get("id", ""),
            "name": place.get("displayName", {}).get("text", ""),
            "address": place.get("formattedAddress", ""),
            "rating": place.get("rating", 0),
            "user_ratings_total": place.get("userRatingCount", 0),
        })

    return results


# ── Place Reviews ────────────────────────────────────────────────────

def get_place_reviews(place_id: str) -> list[dict]:
    """
    Get reviews for a specific place using Place Details (New).
    Google returns up to 5 most recent reviews.

    Args:
        place_id: Google Places ID (e.g., "places/ChIJ...")

    Returns:
        List of dicts: {"author", "rating", "text", "time", "relative_time"}
    """
    if not GOOGLE_MAPS_API_KEY:
        return []

    url = PLACE_DETAILS_URL.format(place_id=place_id)
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "reviews",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[Google Maps] Place details error for {place_id}: {e}")
        return []

    reviews = []
    for review in data.get("reviews", []):
        reviews.append({
            "author": review.get("authorAttribution", {}).get("displayName", "Anonymous"),
            "rating": review.get("rating", 0),
            "text": review.get("text", {}).get("text", ""),
            "time": review.get("publishTime", ""),
            "relative_time": review.get("relativePublishTimeDescription", ""),
        })

    return reviews


# ── Main Entry Point ─────────────────────────────────────────────────

def get_negative_reviews(
    lat: float,
    lng: float,
    max_rating: int = 2,
    exclude_place_name: str = "",
    business_types: list[str] | None = None,
) -> list[dict]:
    """
    Main entry point: find competing businesses and return their negative reviews.

    Args:
        lat, lng: Center of search.
        max_rating: Include reviews with this rating or lower (1-2 stars).
        exclude_place_name: Skip this business (the studio itself).
        business_types: Override business types to search.

    Returns:
        List of dicts with review info + place context:
        {
            "place_id", "place_name", "place_address",
            "author", "rating", "text", "time", "relative_time",
            "review_id" (synthesized for dedup)
        }
    """
    businesses = search_nearby_businesses(
        lat=lat, lng=lng, business_types=business_types,
    )

    all_negative = []
    for biz in businesses:
        # Skip the studio's own listing
        if exclude_place_name and exclude_place_name.lower() in biz["name"].lower():
            continue

        reviews = get_place_reviews(biz["place_id"])
        for review in reviews:
            if review["rating"] <= max_rating and review["text"].strip():
                # Synthesize a unique review ID for dedup
                review_id = f"gmaps_{biz['place_id']}_{review['author']}_{review['rating']}"
                all_negative.append({
                    "place_id": biz["place_id"],
                    "place_name": biz["name"],
                    "place_address": biz["address"],
                    "author": review["author"],
                    "rating": review["rating"],
                    "text": review["text"],
                    "time": review["time"],
                    "relative_time": review["relative_time"],
                    "review_id": review_id,
                })

    return all_negative
