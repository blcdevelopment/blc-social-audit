"""Google Places (New) normalizer + graceful-skip collector (SAE-12)."""

import json
from pathlib import Path

from pydantic import SecretStr

from apps.shared.config import Settings
from apps.worker.stages.social.places_provider import (
    collect_google_business_facts,
    normalize_google_business,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_normalizer_flattens_place_details() -> None:
    raw = json.loads((FIXTURES / "google_places_details.json").read_text())
    gbp = normalize_google_business(raw)
    assert gbp["name"] == "Acme Studio"
    assert gbp["address"] == "123 Main St, Austin, TX 78701, USA"
    assert gbp["phone"] == "(555) 100-2000"  # national preferred over international
    assert gbp["category"] == "General Contractor"  # primaryTypeDisplayName.text
    assert gbp["types"][0] == "general_contractor"
    assert gbp["rating"] == 4.7
    assert gbp["review_count"] == 128
    assert gbp["website"] == "https://acmestudio.example"
    assert gbp["business_status"] == "OPERATIONAL"


def test_normalizer_is_none_safe_on_sparse_payload() -> None:
    gbp = normalize_google_business({})
    assert gbp["name"] is None
    assert gbp["phone"] is None
    assert gbp["rating"] is None
    assert gbp["review_count"] is None
    assert gbp["types"] == []


def test_collector_skips_without_api_key() -> None:
    # _env_file=None isolates from the local .env (which now carries a real Places key).
    result = collect_google_business_facts(Settings(_env_file=None), query="Acme Studio Austin")
    assert result["status"] == "skipped"
    assert result["reason"] == "missing_google_places_api_key"


def test_collector_skips_without_query() -> None:
    settings = Settings(google_places_api_key=SecretStr("test-key"))
    result = collect_google_business_facts(settings, query="   ")
    assert result["status"] == "skipped"
    assert result["reason"] == "no_business_query"


def _ig_facts_with_reviews(review_count):
    from datetime import UTC, datetime

    from apps.worker.stages.social.extractor import extract_social_facts

    raw = json.loads((FIXTURES / "social_instagram_strong.json").read_text())
    facts = extract_social_facts(
        [{"platform": "instagram", "handle": "acme", "raw": raw}],
        now=datetime(2026, 6, 23, tzinfo=UTC),
    )
    if review_count is not None:
        facts["summary"]["google_review_count"] = review_count
    return facts


def test_google_reviews_rule_scores_when_present() -> None:
    from apps.worker.stages.scoring import score_social_audit

    result = score_social_audit(_ig_facts_with_reviews(128), Settings())
    by_id = {r["rule_id"]: r for r in result["category"]["rules"]}
    assert by_id["social.reputation.google_reviews"]["result"] == "pass"


def test_google_reviews_rule_skips_when_absent() -> None:
    # No Google listing (keyless/standalone) -> review count None -> the rule skip-rescales,
    # so a v3-equivalent audit scores identically (no calibration drift).
    from apps.worker.stages.scoring import score_social_audit

    result = score_social_audit(_ig_facts_with_reviews(None), Settings())
    by_id = {r["rule_id"]: r for r in result["category"]["rules"]}
    assert by_id["social.reputation.google_reviews"]["result"] == "skipped"
