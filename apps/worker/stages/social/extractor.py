"""Deterministic normalization of raw social provider payloads into ``social.*`` facts.

Pure functions only (no network) so the social score is reproducible and unit-testable
from fixtures — mirroring extractor_seo / extractor_uxui. Output keys match the
``fact_path`` values in ``rubrics/social.yaml``.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from apps.worker.stages.social.schema import SocialProfileFacts, SocialSummary

JsonDict = dict[str, Any]


def _profile_facts(values: JsonDict) -> JsonDict:
    """Validate a normalized profile against the common schema, return plain facts.

    The single source of truth for the per-profile fact shape; ``extra="forbid"`` turns a
    drifted/typo'd key into a hard error instead of a silently-missing rubric fact.
    """
    return SocialProfileFacts(**values).as_facts()


def _summary_facts(values: JsonDict) -> JsonDict:
    return SocialSummary(**values).as_facts()


# Bio phrases that signal a call-to-action when a profile isn't a flagged business account.
_CTA_RE = re.compile(
    r"\b(call|book|booking|dm|message|quote|estimate|contact|hire|schedule|enquire|inquire|"
    r"get in touch|free consult)\b",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"https?://[^\s)]+", re.IGNORECASE)


def _clean(value: Any) -> str:
    return " ".join(str(value).split()) if isinstance(value, str) else ""


def _first(payload: JsonDict, keys: tuple[str, ...]) -> Any:
    """First non-None value among candidate keys (provider field names vary)."""
    for key in keys:
        if payload.get(key) is not None:
            return payload[key]
    return None


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _posts_per_month(times: list[datetime]) -> float | None:
    if len(times) < 2:
        return None
    span_days = (times[-1] - times[0]).total_seconds() / 86400
    if span_days < 1:
        return float(len(times))
    return round(len(times) / span_days * 30, 1)


def _avg_engagement(posts: list[JsonDict], followers: int) -> float | None:
    if followers <= 0:
        return None
    rates: list[float] = []
    for post in posts:
        likes_raw = post.get("likesCount")
        comments_raw = post.get("commentsCount")
        # Both absent => engagement is hidden/unknown for this post (e.g. a YouTube video
        # with likes AND comments hidden). Skip it rather than scoring it as zero, so the
        # rate stays None and the engagement rule skip_if_missing-rescales instead of failing.
        if likes_raw is None and comments_raw is None:
            continue
        likes = max(_int(likes_raw), 0)
        comments = max(_int(comments_raw), 0)
        rates.append((likes + comments) / followers * 100)
    if not rates:
        return None
    return round(sum(rates) / len(rates), 2)


def _has_video(raw: JsonDict, posts: list[JsonDict]) -> bool:
    if _int(raw.get("igtvVideoCount")) > 0:
        return True
    for post in posts:
        if str(post.get("type", "")).lower() == "video" or _int(post.get("videoViewCount")) > 0:
            return True
    return False


def normalize_instagram_profile(raw: JsonDict, handle: str, *, now: datetime) -> JsonDict:
    bio = _clean(raw.get("biography"))
    external = _clean(raw.get("externalUrl"))
    full_name = _clean(raw.get("fullName"))
    followers = _int(raw.get("followersCount"))
    is_business = bool(raw.get("isBusinessAccount"))
    posts = raw.get("latestPosts")
    posts = [p for p in posts if isinstance(p, dict)] if isinstance(posts, list) else []
    times = sorted(t for t in (_parse_ts(p.get("timestamp")) for p in posts) if t)

    return _profile_facts(
        {
            "platform": "instagram",
            "handle": handle,
            "url": _clean(raw.get("url")) or f"https://www.instagram.com/{handle.lstrip('@')}/",
            "status": "complete",
            "followers": followers,
            "posts_count": _int(raw.get("postsCount")),
            "verified": bool(raw.get("verified")),
            "private": bool(raw.get("private")),
            "is_business": is_business,
            "category": _clean(raw.get("businessCategoryName")) or None,
            "bio_present": bool(bio),
            "link_in_bio": external or None,
            "has_cta": is_business or bool(_CTA_RE.search(bio)),
            "profile_complete": bool(bio and external and full_name),
            "has_logo_avatar": bool(raw.get("profilePicUrl") or raw.get("profilePicUrlHD")),
            "posts_sampled": len(posts),
            "posts_per_month": _posts_per_month(times),
            "days_since_last_post": (now - times[-1]).days if times else None,
            "avg_engagement_rate_pct": _avg_engagement(posts, followers),
            "has_video": _has_video(raw, posts),
        }
    )


def normalize_facebook_profile(raw: JsonDict, handle: str, *, now: datetime) -> JsonDict:
    # Page metadata comes from the Pages actor. Posts (when present) are merged in by the
    # collector from the Facebook Posts actor; without them, cadence/recency/engagement stay
    # None and the corresponding social.yaml rules skip_if_missing (rescale, never penalize).
    intro = _clean(raw.get("intro")) or _clean(raw.get("about"))
    website = _clean(raw.get("website"))
    name = _clean(raw.get("pageName")) or _clean(raw.get("title"))
    followers = _int(raw.get("followers")) or _int(raw.get("likes"))
    messenger = _clean(raw.get("messenger"))
    email = _clean(raw.get("email"))

    raw_posts = [p for p in (raw.get("posts") or []) if isinstance(p, dict)]
    posts = [
        {
            "likesCount": _first(p, ("likes", "likesCount", "reactionsCount", "reactions")),
            "commentsCount": _first(p, ("comments", "commentsCount")),
            "videoViewCount": _first(p, ("viewsCount", "videoViewCount", "videoViews")),
            "timestamp": _first(p, ("time", "timestamp", "date", "publishedAt", "postedAt")),
            "type": "video"
            if (p.get("video") or p.get("videoUrl") or p.get("isVideo"))
            else "post",
        }
        for p in raw_posts
    ]
    times = sorted(t for t in (_parse_ts(p.get("timestamp")) for p in posts) if t)

    return _profile_facts(
        {
            "platform": "facebook",
            "handle": handle,
            "url": _clean(raw.get("facebookUrl"))
            or _clean(raw.get("pageUrl"))
            or f"https://www.facebook.com/{handle.lstrip('@')}/",
            "status": "complete",
            "followers": followers,
            "posts_count": len(raw_posts),
            "verified": bool(raw.get("verified")),
            "private": False,
            "is_business": True,
            "category": _clean(raw.get("category")) or None,
            "bio_present": bool(intro),
            "link_in_bio": website or None,
            "has_cta": bool(messenger or email),
            "profile_complete": bool(intro and website and name),
            "has_logo_avatar": bool(raw.get("profilePhoto") or raw.get("profilePictureUrl")),
            "posts_sampled": len(posts),
            "posts_per_month": _posts_per_month(times),
            "days_since_last_post": (now - times[-1]).days if times else None,
            "avg_engagement_rate_pct": _avg_engagement(posts, followers),
            "has_video": any(p.get("type") == "video" for p in posts),
        }
    )


def normalize_youtube_channel(raw: JsonDict, handle: str, *, now: datetime) -> JsonDict:
    # YouTube Data API v3 payload: {"channel": <channels item>, "videos": [<videos items>]}.
    # Recent uploads are mapped into the same post shape IG uses so the cadence/recency/
    # engagement helpers are reused. subscriberCount can be hidden -> 0 (rules skip/rescale).
    channel = raw.get("channel") if isinstance(raw.get("channel"), dict) else {}
    snippet = channel.get("snippet") if isinstance(channel.get("snippet"), dict) else {}
    stats = channel.get("statistics") if isinstance(channel.get("statistics"), dict) else {}
    branding = (
        channel.get("brandingSettings") if isinstance(channel.get("brandingSettings"), dict) else {}
    )
    videos = [v for v in (raw.get("videos") or []) if isinstance(v, dict)]

    description = _clean(snippet.get("description"))
    title = _clean(snippet.get("title"))
    link_match = _URL_RE.search(description)
    link = link_match.group(0).rstrip(".,);") if link_match else ""
    banner = _clean((branding.get("image") or {}).get("bannerExternalUrl"))
    followers = _int(stats.get("subscriberCount"))
    video_count = _int(stats.get("videoCount"))
    custom_url = _clean(snippet.get("customUrl")).lstrip("@").strip("/")

    posts = [
        {
            "likesCount": (v.get("statistics") or {}).get("likeCount"),
            "commentsCount": (v.get("statistics") or {}).get("commentCount"),
            "videoViewCount": (v.get("statistics") or {}).get("viewCount"),
            "timestamp": (v.get("snippet") or {}).get("publishedAt"),
            "type": "video",
        }
        for v in videos
    ]
    times = sorted(t for t in (_parse_ts(p.get("timestamp")) for p in posts) if t)

    bare_handle = handle.strip().lstrip("@").strip("/")
    if custom_url:
        channel_url = f"https://www.youtube.com/@{custom_url}"
    elif bare_handle.startswith("UC") and len(bare_handle) == 24:
        # Channel IDs use the /channel/UC… form, not /@…
        channel_url = f"https://www.youtube.com/channel/{bare_handle}"
    else:
        channel_url = f"https://www.youtube.com/@{bare_handle}"

    return _profile_facts(
        {
            "platform": "youtube",
            "handle": handle,
            "url": channel_url,
            "status": "complete",
            "followers": followers,
            "posts_count": video_count,
            "verified": False,
            "private": False,
            "is_business": False,
            "category": None,
            "bio_present": bool(description),
            "link_in_bio": link or None,
            "has_cta": bool(link) or bool(_CTA_RE.search(description)),
            "profile_complete": bool(description and title and (link or banner)),
            "has_logo_avatar": bool(snippet.get("thumbnails")),
            "posts_sampled": len(posts),
            "posts_per_month": _posts_per_month(times),
            "days_since_last_post": (now - times[-1]).days if times else None,
            "avg_engagement_rate_pct": _avg_engagement(posts, followers),
            "has_video": bool(videos) or video_count > 0,
        }
    )


def _empty_summary() -> JsonDict:
    # The schema's defaults ARE the empty-audit summary (single source of truth).
    return SocialSummary().as_facts()


def summarize_profiles(profiles: list[JsonDict]) -> JsonDict:
    count = len(profiles)
    if count == 0:
        return _empty_summary()
    ppm = [p["posts_per_month"] for p in profiles if p.get("posts_per_month") is not None]
    dsp = [p["days_since_last_post"] for p in profiles if p.get("days_since_last_post") is not None]
    eng = [
        p["avg_engagement_rate_pct"]
        for p in profiles
        if p.get("avg_engagement_rate_pct") is not None
    ]
    return _summary_facts(
        {
            "platforms_audited": count,
            "total_followers": sum(_int(p.get("followers")) for p in profiles),
            "profiles_complete_pct": round(
                sum(1 for p in profiles if p.get("profile_complete")) / count * 100
            ),
            # None (not 0) when no profile has post data, so the cadence/recency/engagement
            # rules skip_if_missing and rescale out instead of unfairly failing (e.g. the
            # Facebook pages actor returns no posts).
            "avg_posts_per_month": round(sum(ppm) / len(ppm), 1) if ppm else None,
            "days_since_last_post": min(dsp) if dsp else None,
            "avg_engagement_rate_pct": round(sum(eng) / len(eng), 2) if eng else None,
            "profiles_with_link_in_bio": sum(1 for p in profiles if p.get("link_in_bio")),
            "profiles_with_cta": sum(1 for p in profiles if p.get("has_cta")),
            "has_video_content": any(p.get("has_video") for p in profiles),
            "profiles_with_logo_avatar": sum(1 for p in profiles if p.get("has_logo_avatar")),
        }
    )


def extract_social_facts(fetched: list[JsonDict], *, now: datetime | None = None) -> JsonDict:
    """Normalize a list of fetched provider payloads into the social fact bundle.

    Each entry is ``{"platform", "handle", "raw"}`` where ``raw`` is the provider payload
    (or ``None`` when that fetch failed). Status follows the external-source vocabulary:
    skipped (nothing fetched) / failed (all fetches failed) / partial / complete.
    """
    now = now or datetime.now(UTC)
    if not fetched:
        return {
            "status": "skipped",
            "source": "social",
            "summary": _empty_summary(),
            "platforms": [],
        }

    platforms: list[JsonDict] = []
    for entry in fetched:
        raw = entry.get("raw")
        platform = entry.get("platform", "instagram")
        handle = entry.get("handle", "")
        if not raw:
            platforms.append({"platform": platform, "handle": handle, "status": "failed"})
        elif platform == "instagram":
            platforms.append(normalize_instagram_profile(raw, handle, now=now))
        elif platform == "facebook":
            platforms.append(normalize_facebook_profile(raw, handle, now=now))
        elif platform == "youtube":
            platforms.append(normalize_youtube_channel(raw, handle, now=now))
        else:
            # Unknown platform — don't penalize the score.
            platforms.append({"platform": platform, "handle": handle, "status": "unsupported"})

    complete = [p for p in platforms if p.get("status") == "complete"]
    attempted = [p for p in platforms if p.get("status") in {"complete", "failed"}]
    if not complete:
        status = "failed" if any(p.get("status") == "failed" for p in platforms) else "skipped"
    elif len(complete) < len(attempted):
        status = "partial"
    else:
        status = "complete"

    summary = summarize_profiles(complete) if complete else _empty_summary()
    return {"status": status, "source": "social", "summary": summary, "platforms": platforms}
