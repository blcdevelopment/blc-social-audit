"""Typed common schema for the social-audit fact bundle (P2-22 / SMWA-74).

A single, validated source of truth for the ``social.*`` facts that ``rubrics/social.yaml``
scores. Every provider's normalizer (Instagram / Facebook / YouTube) builds the SAME
``SocialProfileFacts`` shape, and ``summarize_profiles`` builds the SAME ``SocialSummary``;
the rubric ``fact_path`` values map 1:1 onto these field names. ``extra="forbid"`` makes a
typo or a drifted field a hard error instead of a silently-missing fact.

The models are intentionally a *contract*, not behaviour — the normalizers in ``extractor``
compute the values and hand them here; ``.model_dump()`` returns the plain dicts the rest of
the pipeline already expects (scoring navigates them by ``fact_path``), so wrapping them
changes nothing observable while guaranteeing the extractor and the rubric stay in lockstep
(see ``tests/unit/test_social_schema.py``).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

JsonDict = dict[str, Any]


class SocialProfileFacts(BaseModel):
    """One audited social profile, normalized into platform-independent facts.

    Field names are the ``social.platforms[*].*`` contract; the rubric reads the aggregates
    in :class:`SocialSummary`, but per-profile facts feed those aggregates and the report.
    ``None`` (not ``0``) is used for cadence/recency/engagement when a provider can't supply
    them, so the corresponding ``skip_if_missing`` rules rescale instead of unfairly failing.
    """

    model_config = ConfigDict(extra="forbid")

    platform: str
    handle: str
    url: str
    status: str = "complete"
    followers: int = 0
    posts_count: int = 0
    verified: bool = False
    private: bool = False
    is_business: bool = False
    category: str | None = None
    bio_present: bool = False
    link_in_bio: str | None = None
    has_cta: bool = False
    profile_complete: bool = False
    has_logo_avatar: bool = False
    posts_sampled: int = 0
    posts_per_month: float | None = None
    days_since_last_post: int | None = None
    avg_engagement_rate_pct: float | None = None
    has_video: bool = False

    def as_facts(self) -> JsonDict:
        """The plain-dict form the pipeline consumes (scoring reads it by ``fact_path``)."""
        return self.model_dump()


class SocialSummary(BaseModel):
    """Cross-profile aggregates the social rubric scores (``social.summary.*``).

    Defaults are the empty-audit values, so ``SocialSummary().model_dump()`` is the canonical
    "nothing collected" summary. Cadence/recency/engagement are ``None`` when no profile has
    post data, so the ``skip_if_missing`` rules rescale rather than scoring a false zero.
    """

    model_config = ConfigDict(extra="forbid")

    platforms_audited: int = 0
    total_followers: int = 0
    profiles_complete_pct: int = 0
    avg_posts_per_month: float | None = 0.0
    days_since_last_post: int | None = None
    avg_engagement_rate_pct: float | None = 0.0
    profiles_with_link_in_bio: int = 0
    profiles_with_cta: int = 0
    has_video_content: bool = False
    profiles_with_logo_avatar: int = 0

    def as_facts(self) -> JsonDict:
        return self.model_dump()
