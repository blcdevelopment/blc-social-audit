import json
from datetime import UTC, datetime
from pathlib import Path

from apps.worker.stages.social.extractor import extract_social_facts

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
NOW = datetime(2026, 6, 23, tzinfo=UTC)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _entry(name: str, handle: str) -> dict:
    return {"platform": "instagram", "handle": handle, "raw": _load(name)}


def test_strong_profile_summary() -> None:
    facts = extract_social_facts([_entry("social_instagram_strong.json", "acmestudio")], now=NOW)
    assert facts["status"] == "complete"
    s = facts["summary"]
    assert s["platforms_audited"] == 1
    assert s["total_followers"] == 5000
    assert s["profiles_complete_pct"] == 100
    assert s["avg_posts_per_month"] == 10.0  # 6 posts over an 18-day span
    assert s["days_since_last_post"] == 2
    assert s["avg_engagement_rate_pct"] == 5.33
    assert s["profiles_with_link_in_bio"] == 1
    assert s["profiles_with_cta"] == 1
    assert s["has_video_content"] is True
    assert s["profiles_with_logo_avatar"] == 1


def test_weak_profile_summary() -> None:
    facts = extract_social_facts([_entry("social_instagram_weak.json", "weakco")], now=NOW)
    assert facts["status"] == "complete"
    s = facts["summary"]
    assert s["profiles_complete_pct"] == 0
    assert s["avg_posts_per_month"] == 5.0
    assert s["days_since_last_post"] == 83
    assert s["avg_engagement_rate_pct"] == 3.75
    assert s["profiles_with_link_in_bio"] == 0
    assert s["profiles_with_cta"] == 0
    assert s["has_video_content"] is False


def test_combined_aggregation() -> None:
    facts = extract_social_facts(
        [
            _entry("social_instagram_strong.json", "acmestudio"),
            _entry("social_instagram_weak.json", "weakco"),
        ],
        now=NOW,
    )
    assert facts["status"] == "complete"
    s = facts["summary"]
    assert s["platforms_audited"] == 2
    assert s["profiles_complete_pct"] == 50
    assert s["avg_posts_per_month"] == 7.5
    assert s["days_since_last_post"] == 2
    assert s["avg_engagement_rate_pct"] == 4.54
    assert s["profiles_with_link_in_bio"] == 1
    assert s["has_video_content"] is True


def test_facebook_profile_normalizes() -> None:
    facts = extract_social_facts(
        [
            {
                "platform": "facebook",
                "handle": "acmestudio",
                "raw": _load("social_facebook_strong.json"),
            }
        ],
        now=NOW,
    )
    assert facts["status"] == "complete"
    profile = facts["platforms"][0]
    assert profile["platform"] == "facebook"
    assert profile["followers"] == 4200
    assert profile["profile_complete"] is True
    assert profile["link_in_bio"] == "https://acmestudio.example"
    assert profile["has_cta"] is True
    # No posts from the FB pages actor -> cadence/engagement unknown (skip in scoring).
    assert profile["posts_per_month"] is None
    assert profile["avg_engagement_rate_pct"] is None


def test_facebook_with_posts_computes_cadence_and_engagement() -> None:
    # When the Facebook Posts actor data is merged in (collector adds raw["posts"]), FB gets
    # the same cadence/recency/engagement treatment as Instagram (was None with page-only data).
    raw = {
        "pageName": "Acme Builders",
        "intro": "Custom homes",
        "website": "https://acmebuilders.example",
        "followers": 4000,
        "messenger": "m.me/acme",
        "profilePhoto": "https://x/y.jpg",
        "posts": [
            {"time": "2026-06-03T00:00:00Z", "likes": 100, "comments": 20},
            {"time": "2026-06-09T00:00:00Z", "likes": 100, "comments": 20},
            {"time": "2026-06-15T00:00:00Z", "likes": 100, "comments": 20},
            {"time": "2026-06-21T00:00:00Z", "likes": 100, "comments": 20},
        ],
    }
    facts = extract_social_facts([{"platform": "facebook", "handle": "acme", "raw": raw}], now=NOW)
    p = facts["platforms"][0]
    assert p["platform"] == "facebook"
    assert p["followers"] == 4000
    assert p["posts_sampled"] == 4
    assert p["posts_per_month"] is not None  # 4 posts over an 18-day span
    assert p["days_since_last_post"] == 2  # newest post 2026-06-21 -> now 2026-06-23
    assert p["avg_engagement_rate_pct"] == 3.0  # (100 + 20) / 4000 followers


def test_instagram_plus_facebook_aggregates_both() -> None:
    facts = extract_social_facts(
        [
            {
                "platform": "instagram",
                "handle": "acmestudio",
                "raw": _load("social_instagram_strong.json"),
            },
            {
                "platform": "facebook",
                "handle": "acmestudio",
                "raw": _load("social_facebook_strong.json"),
            },
        ],
        now=NOW,
    )
    assert facts["status"] == "complete"
    summary = facts["summary"]
    assert summary["platforms_audited"] == 2
    assert summary["profiles_with_link_in_bio"] == 2
    # Cadence/engagement come from the IG profile only (FB has no posts).
    assert summary["avg_posts_per_month"] == 10.0
    assert summary["days_since_last_post"] == 2


def test_youtube_channel_normalizes() -> None:
    facts = extract_social_facts(
        [
            {
                "platform": "youtube",
                "handle": "acmebuilders",
                "raw": _load("social_youtube_strong.json"),
            }
        ],
        now=NOW,
    )
    assert facts["status"] == "complete"
    p = facts["platforms"][0]
    assert p["platform"] == "youtube"
    assert p["followers"] == 5000  # subscriberCount
    assert p["posts_count"] == 120  # videoCount
    assert p["profile_complete"] is True
    assert p["link_in_bio"] == "https://acmebuilders.example"  # parsed from description
    assert p["has_cta"] is True
    assert p["has_video"] is True
    assert p["posts_per_month"] == 10.0  # 6 uploads over an 18-day span
    assert p["days_since_last_post"] == 2
    assert p["avg_engagement_rate_pct"] == 5.0  # (220 likes + 30 comments) / 5000 followers


def test_instagram_plus_youtube_aggregates_two_platforms() -> None:
    facts = extract_social_facts(
        [
            {
                "platform": "instagram",
                "handle": "acmestudio",
                "raw": _load("social_instagram_strong.json"),
            },
            {
                "platform": "youtube",
                "handle": "acmebuilders",
                "raw": _load("social_youtube_strong.json"),
            },
        ],
        now=NOW,
    )
    assert facts["status"] == "complete"
    summary = facts["summary"]
    assert summary["platforms_audited"] == 2  # boosts the social.coverage.platforms rule
    assert summary["has_video_content"] is True


def test_youtube_hidden_engagement_skips_instead_of_zero() -> None:
    # The live API omits likeCount/commentCount when a channel hides them. They must be
    # treated as UNKNOWN (rate None -> rule skip_if_missing-rescales), NOT scored as zero
    # engagement (which would falsely fail the engagement rule and dock ~14 points).
    facts = extract_social_facts(
        [
            {
                "platform": "youtube",
                "handle": "hiddenco",
                "raw": _load("social_youtube_hidden.json"),
            }
        ],
        now=NOW,
    )
    assert facts["status"] == "complete"
    p = facts["platforms"][0]
    assert p["followers"] == 2000
    assert p["avg_engagement_rate_pct"] is None  # hidden -> unknown, not 0
    assert p["posts_per_month"] is not None  # cadence still derived from publishedAt
    assert facts["summary"]["avg_engagement_rate_pct"] is None


def test_instagram_content_and_performance_detail() -> None:
    facts = extract_social_facts([_entry("social_instagram_strong.json", "acme")], now=NOW)
    p = facts["platforms"][0]
    # 1 of 6 sampled posts is a Video -> content mix.
    assert p["video_share_pct"] == 16.7
    assert p["image_share_pct"] == 83.3
    assert p["carousel_share_pct"] == 0.0
    assert p["follows_count"] == 310
    assert p["follower_following_ratio"] == 16.1  # 5000 / 310
    assert p["avg_hashtags_per_post"] == 5.0
    assert p["posts_with_cta_caption_pct"] == 100.0  # every caption has a "book a consult" CTA
    assert p["max_posting_gap_days"] is not None
    assert len(p["top_posts"]) == 3
    assert p["top_posts"][0]["views"] == 4000  # the video has the most views
    s = facts["summary"]
    assert s["profiles_business_account"] == 1
    assert s["video_share_pct"] == 16.7
    assert s["avg_hashtags_per_post"] == 5.0


def test_weak_instagram_has_no_hashtags_or_cta() -> None:
    facts = extract_social_facts([_entry("social_instagram_weak.json", "weak")], now=NOW)
    s = facts["summary"]
    assert (
        s["avg_hashtags_per_post"] == 0.0
    )  # present-but-zero -> the hashtag rule fails (not skip)
    assert s["posts_with_cta_caption_pct"] == 0.0
    assert s["profiles_business_account"] == 0


def test_youtube_surfaces_lifetime_views_and_titles() -> None:
    facts = extract_social_facts(
        [
            {
                "platform": "youtube",
                "handle": "acmebuilders",
                "raw": _load("social_youtube_strong.json"),
            }
        ],
        now=NOW,
    )
    p = facts["platforms"][0]
    assert p["total_views"] is not None and p["total_views"] > 0  # channel lifetime views
    assert p["avg_views_per_post"] is not None
    assert p["video_share_pct"] == 100.0
    assert p["top_posts"] and p["top_posts"][0]["title"]  # YouTube videos carry titles
    assert facts["summary"]["total_views"] == p["total_views"]


def test_no_handles_is_skipped() -> None:
    facts = extract_social_facts([], now=NOW)
    assert facts["status"] == "skipped"
    assert facts["platforms"] == []


def test_failed_fetch_is_failed() -> None:
    facts = extract_social_facts([{"platform": "instagram", "handle": "x", "raw": None}], now=NOW)
    assert facts["status"] == "failed"


def test_partial_when_one_profile_fails() -> None:
    facts = extract_social_facts(
        [
            _entry("social_instagram_strong.json", "acmestudio"),
            {"platform": "instagram", "handle": "x", "raw": None},
        ],
        now=NOW,
    )
    assert facts["status"] == "partial"
    assert facts["summary"]["platforms_audited"] == 1
