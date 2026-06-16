"""Shared vocabulary for technical crawl facts.

Two collectors can fill the ``external_seo.technical_crawl`` slot — the optional
Screaming Frog CLI (licensed desktop tool) and the built-in site health sweep
(``site_health.py``). Both must emit the same summary keys and issue ids so the
rubric (``rubrics/seo.yaml``) and the report guidance
(``report_payload.TECHNICAL_ISSUE_GUIDANCE``) work identically for either tool.
"""

from __future__ import annotations

from typing import Any

JsonDict = dict[str, Any]

ISSUE_LABELS: dict[str, str] = {
    "client_error_internal_urls": "Site URLs returning 'not found' or blocked errors (4xx)",
    "server_error_internal_urls": "Site URLs returning server errors (5xx)",
    "unreachable_internal_urls": "Site URLs that did not respond",
    "client_error_external_urls": "Outbound links returning 'not found' or blocked errors (4xx)",
    "server_error_external_urls": "Outbound links returning server errors (5xx)",
    "non_indexable_internal_urls": "Pages that block Google from indexing them",
    "missing_titles": "Pages missing title tags",
    "duplicate_titles": "Pages with duplicate title tags",
    "missing_meta_descriptions": "Pages missing meta descriptions",
    "duplicate_meta_descriptions": "Pages with duplicate meta descriptions",
    "missing_h1": "Pages missing H1 headings",
    "images_missing_alt": "Images missing alt text",
    "missing_canonicals": "Pages missing canonical URLs",
}

_HIGH_SEVERITY_ISSUES = {
    "client_error_internal_urls",
    "server_error_internal_urls",
}
_MEDIUM_SEVERITY_ISSUES = {
    "unreachable_internal_urls",
    "client_error_external_urls",
    "server_error_external_urls",
    "non_indexable_internal_urls",
    "missing_titles",
    "duplicate_titles",
    "missing_meta_descriptions",
    "duplicate_meta_descriptions",
    "missing_h1",
    "images_missing_alt",
    "missing_canonicals",
}


def empty_summary() -> JsonDict:
    return {
        "urls_crawled": 0,
        "html_urls_crawled": 0,
        "client_error_internal_urls": 0,
        "server_error_internal_urls": 0,
        "unreachable_internal_urls": 0,
        "client_error_external_urls": 0,
        "server_error_external_urls": 0,
        "non_indexable_internal_urls": 0,
        "missing_titles": 0,
        "duplicate_titles": 0,
        "missing_meta_descriptions": 0,
        "duplicate_meta_descriptions": 0,
        "missing_h1": 0,
        "images_missing_alt": 0,
        "missing_canonicals": 0,
    }


def issue_severity(issue_id: str) -> str:
    if issue_id in _HIGH_SEVERITY_ISSUES:
        return "high"
    if issue_id in _MEDIUM_SEVERITY_ISSUES:
        return "medium"
    return "medium"


def issues_from_summary(
    summary: JsonDict,
    examples: dict[str, list[str]],
    *,
    source: str,
) -> list[JsonDict]:
    issues = []
    for key, label in ISSUE_LABELS.items():
        count = int(summary.get(key) or 0)
        if count <= 0:
            continue
        issues.append(
            {
                "id": key,
                "source": source,
                "severity": issue_severity(key),
                "title": label,
                "count": count,
                "examples": examples.get(key, [])[:10],
            }
        )
    return sorted(issues, key=lambda issue: (-int(issue["count"]), issue["id"]))
