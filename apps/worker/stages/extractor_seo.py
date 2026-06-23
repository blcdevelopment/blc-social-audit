from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

JsonDict = dict[str, Any]

# Useful search-result length ranges (characters). Exposed as facts so the report can
# state the baseline a "length is outside the ideal range" finding was judged against.
TITLE_IDEAL_MIN_LENGTH, TITLE_IDEAL_MAX_LENGTH = 30, 65
META_DESCRIPTION_IDEAL_MIN_LENGTH, META_DESCRIPTION_IDEAL_MAX_LENGTH = 70, 160


def _get_page_value(page: object, key: str, default: Any = None) -> Any:
    if isinstance(page, Mapping):
        return page.get(key, default)
    return getattr(page, key, default)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _pct(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _is_internal_link(page_url: str, href: str) -> bool:
    absolute = urljoin(page_url, href)
    parsed_page = urlparse(page_url)
    parsed_link = urlparse(absolute)
    if parsed_link.scheme not in {"http", "https"}:
        return False
    page_host = (parsed_page.hostname or "").lower().removeprefix("www.")
    link_host = (parsed_link.hostname or "").lower().removeprefix("www.")
    return page_host == link_host


def _meta_content(soup: BeautifulSoup, name: str) -> str | None:
    tag = soup.find("meta", attrs={"name": re.compile(f"^{re.escape(name)}$", re.I)})
    if not isinstance(tag, Tag):
        return None
    return _clean_text(str(tag.get("content", "")))


def _extract_schema_types(soup: BeautifulSoup) -> JsonDict:
    json_ld_types: set[str] = set()
    microdata_types: set[str] = set()

    def collect_jsonld_type(value: Any) -> None:
        if isinstance(value, dict):
            item_type = value.get("@type")
            if isinstance(item_type, str):
                json_ld_types.add(item_type)
            elif isinstance(item_type, list):
                json_ld_types.update(str(entry) for entry in item_type if entry)
            for child in value.values():
                collect_jsonld_type(child)
        elif isinstance(value, list):
            for child in value:
                collect_jsonld_type(child)

    for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        raw = script.string or script.get_text("", strip=True)
        if not raw:
            continue
        try:
            collect_jsonld_type(json.loads(raw))
        except json.JSONDecodeError:
            continue

    for tag in soup.find_all(attrs={"itemscope": True}):
        if not isinstance(tag, Tag):
            continue
        item_type = tag.get("itemtype")
        if isinstance(item_type, str) and item_type.strip():
            microdata_types.add(item_type.strip())

    return {
        "has_schema": bool(json_ld_types or microdata_types),
        "json_ld_types": sorted(json_ld_types),
        "microdata_types": sorted(microdata_types),
    }


def extract_seo_facts_for_page(page: object) -> JsonDict:
    url = str(_get_page_value(page, "final_url", None) or _get_page_value(page, "url", ""))
    html = str(_get_page_value(page, "html", "") or "")
    soup = BeautifulSoup(html, "html.parser")

    title_text = _clean_text(soup.title.string if soup.title and soup.title.string else None)
    description = _meta_content(soup, "description")
    canonical_tag = soup.find("link", attrs={"rel": re.compile("canonical", re.I)})
    canonical = None
    if isinstance(canonical_tag, Tag):
        canonical_href = str(canonical_tag.get("href", "")).strip()
        canonical = urljoin(url, canonical_href) if canonical_href else None

    headings: dict[str, list[str]] = {}
    for level in range(1, 7):
        key = f"h{level}"
        headings[key] = [
            text
            for tag in soup.find_all(key)
            if (text := _clean_text(tag.get_text(" ", strip=True)))
        ]

    anchors = [tag for tag in soup.find_all("a", href=True) if isinstance(tag, Tag)]
    empty_links = 0
    internal_links = 0
    external_links = 0
    for anchor in anchors:
        href = str(anchor.get("href", "")).strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            empty_links += 1
        elif _is_internal_link(url, href):
            internal_links += 1
        else:
            external_links += 1

    images = [tag for tag in soup.find_all("img") if isinstance(tag, Tag)]
    images_with_alt = sum(1 for image in images if _clean_text(str(image.get("alt", ""))))
    robots_content = (_meta_content(soup, "robots") or "").lower()
    robots_directives = {
        directive.strip() for directive in re.split(r"[,\s]+", robots_content) if directive.strip()
    }

    return {
        "url": url,
        "status_code": _get_page_value(page, "status_code", None),
        "title": {
            "text": title_text,
            "length": len(title_text or ""),
            "present": title_text is not None,
            "is_reasonable_length": (
                TITLE_IDEAL_MIN_LENGTH <= len(title_text or "") <= TITLE_IDEAL_MAX_LENGTH
            ),
            "ideal_min_length": TITLE_IDEAL_MIN_LENGTH,
            "ideal_max_length": TITLE_IDEAL_MAX_LENGTH,
        },
        "meta_description": {
            "text": description,
            "length": len(description or ""),
            "present": description is not None,
            "is_reasonable_length": (
                META_DESCRIPTION_IDEAL_MIN_LENGTH
                <= len(description or "")
                <= META_DESCRIPTION_IDEAL_MAX_LENGTH
            ),
            "ideal_min_length": META_DESCRIPTION_IDEAL_MIN_LENGTH,
            "ideal_max_length": META_DESCRIPTION_IDEAL_MAX_LENGTH,
        },
        "canonical": canonical,
        "headings": {
            "counts": {key: len(values) for key, values in headings.items()},
            "h1_texts": headings["h1"],
            "h2_texts": headings["h2"],
        },
        "links": {
            "total": len(anchors),
            "internal_count": internal_links,
            "external_count": external_links,
            "empty_or_non_http_count": empty_links,
        },
        "images": {
            "total": len(images),
            "with_alt": images_with_alt,
            "missing_alt": len(images) - images_with_alt,
            "alt_coverage_pct": _pct(images_with_alt, len(images)),
        },
        "schema": _extract_schema_types(soup),
        "robots": {
            "directives": sorted(robots_directives),
            "noindex": "noindex" in robots_directives,
            "nofollow": "nofollow" in robots_directives,
        },
    }


def extract_seo_facts(pages: Iterable[object]) -> JsonDict:
    page_facts = [extract_seo_facts_for_page(page) for page in pages]
    analyzed = len(page_facts)
    image_total = sum(page["images"]["total"] for page in page_facts)
    images_with_alt = sum(page["images"]["with_alt"] for page in page_facts)

    return {
        "status": "complete" if page_facts else "empty",
        "pages_analyzed": analyzed,
        "summary": {
            "titles_present_pct": _pct(
                sum(1 for page in page_facts if page["title"]["present"]),
                analyzed,
            ),
            "meta_descriptions_present_pct": _pct(
                sum(1 for page in page_facts if page["meta_description"]["present"]),
                analyzed,
            ),
            "h1_present_pct": _pct(
                sum(1 for page in page_facts if page["headings"]["counts"]["h1"] == 1),
                analyzed,
            ),
            "pages_with_schema": sum(1 for page in page_facts if page["schema"]["has_schema"]),
            "image_alt_coverage_pct": _pct(images_with_alt, image_total),
            "total_internal_links": sum(page["links"]["internal_count"] for page in page_facts),
            "total_external_links": sum(page["links"]["external_count"] for page in page_facts),
            "noindex_pages": sum(1 for page in page_facts if page["robots"]["noindex"]),
        },
        "pages": page_facts,
    }
