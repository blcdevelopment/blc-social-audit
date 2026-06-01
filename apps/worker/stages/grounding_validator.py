from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from apps.worker.stages.commentary import validate_commentary_content

JsonDict = dict[str, Any]
NUMERIC_RE = re.compile(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?%?")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def validate_commentary_grounding(
    commentary: JsonDict,
    *,
    fact_sources: JsonDict,
) -> tuple[JsonDict, JsonDict]:
    sanitized = deepcopy(commentary)
    content = sanitized.get("content")
    if not isinstance(content, dict):
        return sanitized, {
            "status": "failed",
            "unsupported_claims": [],
            "reason": "commentary content missing",
        }

    known_values = _known_numeric_values(fact_sources)
    unsupported: list[JsonDict] = []
    sanitized["content"] = _sanitize_value(
        content,
        path="content",
        known_values=known_values,
        unsupported=unsupported,
    )
    validate_commentary_content(sanitized["content"])

    return sanitized, {
        "status": "complete",
        "numeric_claims_checked": sum(item["claim_count"] for item in unsupported)
        + _supported_claim_count(content, known_values),
        "unsupported_claims": unsupported,
        "unsupported_claim_count": sum(item["claim_count"] for item in unsupported),
        "action": "stripped_unsupported_numeric_sentences" if unsupported else "none",
    }


def _sanitize_value(
    value: Any,
    *,
    path: str,
    known_values: set[float],
    unsupported: list[JsonDict],
) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize_value(
                child,
                path=f"{path}.{key}",
                known_values=known_values,
                unsupported=unsupported,
            )
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [
            _sanitize_value(
                child,
                path=f"{path}[{index}]",
                known_values=known_values,
                unsupported=unsupported,
            )
            for index, child in enumerate(value)
        ]
    if isinstance(value, str):
        return _sanitize_text(value, path=path, known_values=known_values, unsupported=unsupported)
    return value


def _sanitize_text(
    text: str,
    *,
    path: str,
    known_values: set[float],
    unsupported: list[JsonDict],
) -> str:
    sentences = SENTENCE_RE.split(text)
    kept: list[str] = []
    removed: list[JsonDict] = []
    for sentence in sentences:
        claims = _numeric_claims(sentence)
        unsupported_values = [claim for claim in claims if claim not in known_values]
        if unsupported_values:
            removed.append(
                {
                    "text": sentence.strip(),
                    "values": unsupported_values,
                }
            )
        else:
            kept.append(sentence)

    if removed:
        unsupported.append(
            {
                "path": path,
                "claim_count": sum(len(item["values"]) for item in removed),
                "removed_sentences": removed,
            }
        )

    cleaned = " ".join(sentence.strip() for sentence in kept if sentence.strip()).strip()
    return cleaned or "Unsupported numeric claim removed by grounding validator."


def _known_numeric_values(payload: Any) -> set[float]:
    values: set[float] = set()
    _collect_numeric_values(payload, values)
    return values


def _collect_numeric_values(payload: Any, values: set[float]) -> None:
    if isinstance(payload, bool) or payload is None:
        return
    if isinstance(payload, int | float):
        values.add(_normalize_number(payload))
        return
    if isinstance(payload, str):
        values.update(_numeric_claims(payload))
        return
    if isinstance(payload, dict):
        for child in payload.values():
            _collect_numeric_values(child, values)
        return
    if isinstance(payload, list | tuple | set):
        for child in payload:
            _collect_numeric_values(child, values)


def _numeric_claims(text: str) -> list[float]:
    claims: list[float] = []
    for match in NUMERIC_RE.finditer(text):
        raw = match.group(0).replace(",", "").removesuffix("%")
        try:
            claims.append(_normalize_number(float(raw)))
        except ValueError:
            continue
    return claims


def _normalize_number(value: int | float) -> float:
    return round(float(value), 4)


def _supported_claim_count(payload: Any, known_values: set[float]) -> int:
    if isinstance(payload, str):
        return sum(1 for claim in _numeric_claims(payload) if claim in known_values)
    if isinstance(payload, dict):
        return sum(_supported_claim_count(value, known_values) for value in payload.values())
    if isinstance(payload, list):
        return sum(_supported_claim_count(value, known_values) for value in payload)
    return 0
