"""Niche -> category matcher (SAE-4 / SAE-9-full).

NOTE: the taxonomy in categories.py is a STARTER map pending Elda's confirmed category list;
these tests pin the *behaviour* (conservative, skip-on-unknown), not a final vocabulary.
"""

from apps.worker.stages.social.categories import category_matches_niche, category_relevance


def test_matching_category_for_home_services_niche() -> None:
    assert category_matches_niche("homes", "General Contractor") is True
    assert category_matches_niche("home builder", "Home Builder") is True
    assert category_matches_niche("kitchen remodeling", "Kitchen Remodeler") is True


def test_generic_or_wrong_category_is_false() -> None:
    # A recognized niche + a category that clearly doesn't fit -> False (a real finding).
    assert category_matches_niche("home builder", "Restaurant") is False
    assert category_matches_niche("remodeling", "Local Business") is False


def test_unclassifiable_niche_returns_none() -> None:
    # Conservative: an unknown/blank niche can't be judged -> None -> the rule skips (no guess).
    assert category_matches_niche("crypto newsletter", "Contractor") is None
    assert category_matches_niche("", "Contractor") is None
    assert category_matches_niche(None, "Contractor") is None


def test_missing_category_returns_none() -> None:
    assert category_matches_niche("home builder", None) is None
    assert category_matches_niche("home builder", "") is None


def test_relevance_rollup_any_match_wins() -> None:
    # At least one profile categorized relevantly -> True.
    assert category_relevance("homes", ["Local Business", "General Contractor"]) is True
    # Categories set but none fit -> False.
    assert category_relevance("home builder", ["Restaurant", "Cafe"]) is False
    # Nothing comparable (unknown niche, or no categories) -> None.
    assert category_relevance("mystery niche", ["Contractor"]) is None
    assert category_relevance("homes", [None, ""]) is None
