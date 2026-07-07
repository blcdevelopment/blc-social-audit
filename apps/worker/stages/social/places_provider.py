"""Google Places API (New) backend — public Google Business Profile data (SAE-12).

Pulls a business's public Google listing (address, phone, category, rating, review count,
website) for the combined audit's business-identity enrichment. PUBLIC data: a plain API key,
no owner consent (contrast the owner-only Google Business Profile API). Two calls, per Google's
model: Text Search (New) resolves a query to a place id, then Place Details (New) returns the
fields. Network-only fetchers return the raw payload or ``None`` so the collector degrades
gracefully (the missing-key pattern shared with Apify / PSI); the token is read from Settings
and never logged. ``normalize_google_business`` is pure and unit-testable from a fixture.
"""

from __future__ import annotations

from typing import Any

import httpx

from apps.shared.config import Settings

JsonDict = dict[str, Any]

_SEARCH_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
_DETAILS_ENDPOINT = "https://places.googleapis.com/v1/places"
# Fields we bill for on the Details call (Enterprise SKU); a minimal mask keeps cost down.
_DETAILS_FIELD_MASK = ",".join(
    (
        "displayName",
        "formattedAddress",
        "nationalPhoneNumber",
        "internationalPhoneNumber",
        "types",
        "primaryTypeDisplayName",
        "rating",
        "userRatingCount",
        "websiteUri",
        "businessStatus",
    )
)


def _api_key(settings: Settings) -> str:
    key = settings.google_places_api_key
    return key.get_secret_value() if key else ""


def _text(value: Any) -> str:
    """A Places display field is often ``{"text": "...", "languageCode": "en"}`` — flatten it."""
    if isinstance(value, dict):
        value = value.get("text")
    return " ".join(str(value).split()) if isinstance(value, str) else ""


def fetch_place_id(query: str, settings: Settings) -> str | None:
    """Resolve a business name / website query to a Places place id (Text Search, New)."""
    key = _api_key(settings)
    if not key or not query.strip():
        return None
    try:
        response = httpx.post(
            _SEARCH_ENDPOINT,
            headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": "places.id"},
            json={"textQuery": query.strip()},
            timeout=settings.google_places_timeout_seconds,
        )
        if response.status_code >= 400:
            return None
        places = response.json().get("places")
    except Exception:
        return None
    if not isinstance(places, list) or not places:
        return None
    first = places[0]
    place_id = first.get("id") if isinstance(first, dict) else None
    return place_id if isinstance(place_id, str) and place_id else None


def fetch_place_details(place_id: str, settings: Settings) -> JsonDict | None:
    """Fetch Place Details (New) for a place id with the minimal billed field mask."""
    key = _api_key(settings)
    if not key or not place_id:
        return None
    try:
        response = httpx.get(
            f"{_DETAILS_ENDPOINT}/{place_id}",
            headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": _DETAILS_FIELD_MASK},
            timeout=settings.google_places_timeout_seconds,
        )
        if response.status_code >= 400:
            return None
        payload = response.json()
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def normalize_google_business(raw: JsonDict) -> JsonDict:
    """Pure normalization of a Place Details payload into flat GBP facts (deterministic)."""
    phone = _text(raw.get("nationalPhoneNumber")) or _text(raw.get("internationalPhoneNumber"))
    types = raw.get("types")
    types = [t for t in types if isinstance(t, str)] if isinstance(types, list) else []
    rating = raw.get("rating")
    review_count = raw.get("userRatingCount")
    return {
        "name": _text(raw.get("displayName")) or None,
        "address": _text(raw.get("formattedAddress")) or None,
        "phone": phone or None,
        "category": _text(raw.get("primaryTypeDisplayName")) or (types[0] if types else None),
        "types": types,
        "rating": float(rating) if isinstance(rating, (int, float)) else None,
        "review_count": int(review_count) if isinstance(review_count, (int, float)) else None,
        "website": _text(raw.get("websiteUri")) or None,
        "business_status": _text(raw.get("businessStatus")) or None,
    }


def collect_google_business_facts(settings: Settings, *, query: str) -> JsonDict:
    """Resolve + fetch + normalize a business's public Google listing.

    Graceful at every not-ready state (mirrors the social/benchmark collectors): no key or no
    query => ``skipped``; a failed lookup => ``failed``; success => ``complete`` with ``business``.
    Never raises; a missing/failed Google listing leaves the combined report unchanged.
    """
    if not _api_key(settings):
        return {
            "status": "skipped",
            "reason": "missing_google_places_api_key",
            "source": "google_business",
        }
    if not query or not query.strip():
        return {"status": "skipped", "reason": "no_business_query", "source": "google_business"}
    place_id = fetch_place_id(query, settings)
    if not place_id:
        return {"status": "failed", "reason": "place_not_found", "source": "google_business"}
    raw = fetch_place_details(place_id, settings)
    if raw is None:
        return {"status": "failed", "reason": "details_unavailable", "source": "google_business"}
    return {
        "status": "complete",
        "source": "google_business",
        "business": normalize_google_business(raw),
    }
