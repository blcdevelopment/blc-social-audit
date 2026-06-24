"""Social audit collector — orchestrates provider fetch -> extractor.

Graceful by design (matches the PSI / external-SEO pattern): no handles, or no usable
provider credential for any requested platform => ``skipped`` (never penalizes / aborts);
per-platform fetch failures degrade to ``partial``/``failed`` via the extractor. Instagram
and Facebook are fetched via Apify; YouTube via the free YouTube Data API.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from apps.shared.config import Settings
from apps.worker.stages.social.apify_provider import (
    fetch_facebook_page,
    fetch_facebook_posts,
    fetch_instagram_profile,
)
from apps.worker.stages.social.extractor import extract_social_facts
from apps.worker.stages.social.youtube_provider import fetch_youtube_channel

JsonDict = dict[str, Any]

# Platforms fetched through Apify (gated on APIFY_API_TOKEN); YouTube uses its own key.
_APIFY_PLATFORMS = {"instagram", "facebook"}


def _skipped(reason: str) -> JsonDict:
    return {
        "status": "skipped",
        "reason": reason,
        "source": "social",
        "summary": {},
        "platforms": [],
    }


def collect_social_facts(settings: Settings, handles: dict[str, str | None] | None) -> JsonDict:
    active = {platform: handle for platform, handle in (handles or {}).items() if handle}
    if not active:
        return _skipped("no_social_handles")

    apify_token = settings.apify_api_token.get_secret_value() if settings.apify_api_token else ""
    youtube_key = settings.youtube_api_key.get_secret_value() if settings.youtube_api_key else ""

    def _usable(platform: str) -> bool:
        if platform == "youtube":
            return bool(youtube_key)
        return bool(apify_token)

    # Only skip-early when we cannot fetch ANY requested platform (a per-platform missing
    # key just yields a None fetch -> failed, handled by the extractor).
    if not any(_usable(platform) for platform in active):
        reason = (
            "missing_youtube_api_key" if set(active) <= {"youtube"} else "missing_apify_api_token"
        )
        return _skipped(reason)

    fetched: list[JsonDict] = []
    for platform, handle in active.items():
        if platform == "instagram":
            raw = fetch_instagram_profile(handle, settings)
        elif platform == "facebook":
            raw = fetch_facebook_page(handle, settings)
            # The Pages actor has no posts; pull them from the Posts actor so the extractor
            # can derive FB cadence/recency/engagement (graceful: page still scores if absent).
            if raw is not None:
                posts = fetch_facebook_posts(handle, settings)
                if posts:
                    raw = {**raw, "posts": posts}
        elif platform == "youtube":
            raw = fetch_youtube_channel(handle, settings)
        else:
            raw = None  # unknown platform — recorded as failed by the extractor
        fetched.append({"platform": platform, "handle": handle, "raw": raw})

    return extract_social_facts(fetched, now=datetime.now(UTC))
