#!/usr/bin/env python
"""P1-24 Reproducibility QA.

Runs the same site through the pipeline twice and asserts the SEO, UX/UI, and
Lead Generation Readiness scores - plus every per-rule breakdown result - are
identical. Scoring is deterministic given identical extracted facts, so any
drift here is a real regression.

Run from the repo root:

    python scripts/qa_reproducibility.py

Exits 0 when the two runs match, 1 otherwise.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import qa_common  # noqa: E402


def _score_line(label: str, a: object, b: object) -> tuple[str, bool, str]:
    return (label, a == b, f"run1={a} run2={b}")


def _rule_diff(category: str, s1: qa_common.JsonDict, s2: qa_common.JsonDict) -> tuple[bool, str]:
    r1 = qa_common.rule_results(s1.get("score_breakdown", {}) or {}, category)
    r2 = qa_common.rule_results(s2.get("score_breakdown", {}) or {}, category)
    if r1 == r2:
        return True, f"{len(r1)} rules identical"
    diffs = [
        f"{rule_id}: {r1.get(rule_id)} -> {r2.get(rule_id)}"
        for rule_id in sorted(set(r1) | set(r2))
        if r1.get(rule_id) != r2.get(rule_id)
    ]
    return False, "; ".join(diffs)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="blc-qa-repro-") as tmp:
        tmp_dir = Path(tmp)
        qa_common.configure_local_env(tmp_dir)
        qa_common.create_schema()

        fixture = sys.argv[1] if len(sys.argv) > 1 else qa_common.DEFAULT_FIXTURE
        with qa_common.serve_fixtures() as port:
            url = f"http://127.0.0.1:{port}/{fixture}"
            print(f"[qa-repro] running pipeline twice against {url}\n")
            id1 = qa_common.run_audit_pipeline(url, niche="custom home builder")
            id2 = qa_common.run_audit_pipeline(url, niche="custom home builder")

        s1 = qa_common.snapshot_audit(id1)
        s2 = qa_common.snapshot_audit(id2)

        checks: list[tuple[str, bool, str]] = [
            _score_line("SEO score", s1.get("seo_score"), s2.get("seo_score")),
            _score_line("UX/UI score", s1.get("uxui_score"), s2.get("uxui_score")),
            _score_line("Lead Gen score", s1.get("lead_gen_score"), s2.get("lead_gen_score")),
            _score_line("Rubric version", s1.get("rubric_version"), s2.get("rubric_version")),
        ]
        seo_ok, seo_detail = _rule_diff("seo", s1, s2)
        uxui_ok, uxui_detail = _rule_diff("uxui", s1, s2)
        checks.append(("SEO rule breakdown", seo_ok, seo_detail))
        checks.append(("UX/UI rule breakdown", uxui_ok, uxui_detail))

        width = max(len(name) for name, _, _ in checks)
        all_passed = True
        for name, passed, detail in checks:
            mark = "PASS" if passed else "FAIL"
            all_passed = all_passed and passed
            print(f"  [{mark}] {name.ljust(width)}  {detail}")

        print()
        if all_passed:
            print("[qa-repro] RESULT: PASS - both runs are byte-for-byte reproducible")
            return 0
        print("[qa-repro] RESULT: FAIL - scores or rule breakdowns drifted between runs")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
