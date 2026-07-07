"""Niche -> acceptable-business-category taxonomy + matcher (SAE-4 / completes SAE-9).

Elda's review asks us to check a business is listed under the RIGHT category on Facebook/
Instagram/Google (contractor, remodeler, interior designer, ...), not merely that *a* category
is set. This maps the audit's free-text ``niche`` to a family of acceptable category strings and
answers "does this profile's category fit the niche?".

Design for safety (this is client-facing): the matcher returns ``None`` — meaning "can't tell,
skip the rule" — whenever the niche can't be confidently classified, so a vague niche never
produces a false "wrong category" finding. Only a niche we recognize AND a category we can compare
yields True/False.

>>> STARTER TAXONOMY — pending sign-off from Elda. The home-services family below is a reasonable
default for BLC's builder/remodeler audience; confirm/extend ``NICHE_CATEGORY_FAMILIES`` with the
real category strings Elda's team uses before treating category-relevance findings as authoritative.
"""

from __future__ import annotations

JsonDict = dict[str, object]

# family -> {niche keyword fragments that select it, acceptable category substrings}.
# Matching is case-insensitive substring containment on both sides (categories differ across
# Instagram businessCategoryName / Facebook category / Google types, so exact equality is brittle).
NICHE_CATEGORY_FAMILIES: dict[str, dict[str, tuple[str, ...]]] = {
    "home_services": {
        "niche_keywords": (
            "home",
            "house",
            "build",
            "construct",
            "contractor",
            "remodel",
            "renovat",
            "roof",
            "kitchen",
            "bath",
            "interior",
            "deck",
            "landscap",
            "hvac",
            "plumb",
            "electric",
            "concrete",
            "fenc",
            "flooring",
            "cabinet",
        ),
        "acceptable_categories": (
            "contractor",
            "builder",
            "construction",
            "remodel",
            "renovation",
            "interior design",
            "home improvement",
            "roofing",
            "landscap",
            "architect",
            "kitchen",
            "bathroom",
            "handyman",
            "carpenter",
            "hvac",
            "plumb",
            "electric",
            "flooring",
            "cabinet",
            "deck",
            "fence",
        ),
    },
}


def _classify_niche(niche: str | None) -> str | None:
    """The category family a niche belongs to, or None when we can't confidently classify it."""
    text = (niche or "").lower()
    if not text.strip():
        return None
    for family, spec in NICHE_CATEGORY_FAMILIES.items():
        if any(keyword in text for keyword in spec["niche_keywords"]):
            return family
    return None


def category_matches_niche(niche: str | None, category: str | None) -> bool | None:
    """Whether ``category`` fits the business ``niche``.

    None (=> the rule skips) when the niche is unclassifiable or the category is empty — so we never
    guess a "wrong category" finding on a vague niche or a profile with no category set.
    """
    family = _classify_niche(niche)
    if family is None or not category or not category.strip():
        return None
    cat = category.lower()
    return any(token in cat for token in NICHE_CATEGORY_FAMILIES[family]["acceptable_categories"])


def category_relevance(niche: str | None, categories: list[str | None]) -> bool | None:
    """Roll up per-category matches for a business: True if any declared category fits the niche,
    False if categories are set but none fit, None if nothing is comparable (rule skips)."""
    verdicts = [category_matches_niche(niche, c) for c in categories]
    verdicts = [v for v in verdicts if v is not None]
    if not verdicts:
        return None
    return any(verdicts)
