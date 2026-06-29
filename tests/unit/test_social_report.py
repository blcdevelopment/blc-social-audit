"""Social report builder depth (phase2-social-v2): quantified findings, strengths, content
insights, top posts, and the per-platform scorecard — the data that makes the social audit
substantive rather than a one-line 'engagement is low'."""

import json
from datetime import UTC, datetime
from pathlib import Path

from apps.shared.config import Settings
from apps.worker.stages.scoring import score_social_audit
from apps.worker.stages.social.extractor import extract_social_facts
from apps.worker.stages.social.report import build_social_report_data

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
NOW = datetime(2026, 6, 23, tzinfo=UTC)


def _build(name: str, handle: str) -> dict:
    raw = json.loads((FIXTURES / name).read_text())
    facts = extract_social_facts([{"platform": "instagram", "handle": handle, "raw": raw}], now=NOW)
    breakdown = score_social_audit(facts, Settings())
    return build_social_report_data(
        social_facts=facts,
        social_breakdown=breakdown,
        social_score=breakdown["score"],
        handles={"instagram": handle},
    )


def test_weak_findings_are_quantified_with_targets() -> None:
    report = _build("social_instagram_weak.json", "weak")
    assert report["findings"], "a weak account should surface findings"
    metrics = [f["metric"] for f in report["findings"] if f.get("metric")]
    assert metrics, "findings carry a measured metric line"
    # e.g. "0% (target ≥ 100%)" — the measured value AND the threshold, not a bare label.
    assert any("target" in m for m in metrics)


def test_strong_surfaces_strengths_insights_topposts_and_scorecard() -> None:
    report = _build("social_instagram_strong.json", "acme")
    # A strong account is no longer an empty "no issues" report — passing checks become strengths.
    assert report["strengths"]
    assert all(s.get("label") for s in report["strengths"])

    ci = report["content_insights"]
    assert ci["content_mix"]["video"] == 16.7
    assert ci["avg_hashtags_per_post"] == 5.0
    assert ci["posts_with_cta_caption_pct"] == 100.0

    assert report["top_posts"], "top performing posts are surfaced"
    assert report["top_posts"][0]["views"] == 4000

    assert report["per_platform"] and report["per_platform"][0]["platform"] == "instagram"
    assert report["per_platform"][0]["video_share_pct"] == 16.7


def test_metric_line_handles_percent_and_count_facts() -> None:
    report = _build("social_instagram_weak.json", "weak")
    by_id = {f["id"]: f for f in report["findings"]}
    # profiles_complete_pct -> percent-unit metric
    if "social.profile.complete" in by_id:
        assert "%" in (by_id["social.profile.complete"]["metric"] or "")
    # a count fact (link in bio) -> no spurious unit, still shows the target
    if "social.link_in_bio" in by_id:
        assert "target" in (by_id["social.link_in_bio"]["metric"] or "")
