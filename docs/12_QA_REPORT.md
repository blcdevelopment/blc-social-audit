# Phase 1 QA Report (P1-23, P1-24)

**Project:** BLC Website Audit Automation
**Scope:** Local end-to-end QA and reproducibility QA
**Date:** 2026-06-02
**Environment:** Conda `social-audit`, Python 3.12, local-first (no PostgreSQL, no
Docker, no paid APIs required for the harness)

---

## 1. How QA Is Run

Two repeatable harness scripts drive the **real** production pipeline end to end:

| Script | Jira task | What it proves |
|---|---|---|
| `scripts/qa_e2e.py` | P1-23 Local End-To-End QA | Every stage runs and persists a result |
| `scripts/qa_reproducibility.py` | P1-24 Reproducibility QA | The same site scores identically on repeat runs |

Both share `scripts/qa_common.py`, which makes the run hermetic and deterministic:

- A localhost HTTP server serves the bundled HTML fixtures, so the **real
  Playwright crawler** renders a real page with no internet access.
- The database is an **ephemeral SQLite file** (the models degrade to portable
  types), so no PostgreSQL is required.
- PageSpeed Insights runs its **real graceful-skip path** (no API key needed).
- Commentary runs its **real local-fallback path** (no OpenAI key needed).

Everything else — crawler, SEO/UX extractors, deterministic scoring, grounding
validation, report-payload composition, and WeasyPrint PDF rendering — is the
exact production code path. Because no live network or LLM call is made, runs are
deterministic, which is what the reproducibility gate requires.

```bash
make qa            # or: python scripts/qa_e2e.py
make qa-repro      # or: python scripts/qa_reproducibility.py
# Override the fixture:  python scripts/qa_e2e.py weak_site.html
```

> The Alembic migration targets PostgreSQL (it creates the `pgcrypto`
> extension). The QA harness uses `Base.metadata.create_all` on SQLite instead,
> so it can run with zero infrastructure. The PostgreSQL migration path is
> exercised by the Docker Compose stack (`alembic upgrade head`).

---

## 2. P1-23 — Local End-To-End QA Results

Command: `python scripts/qa_e2e.py` (strong-site fixture)

| Stage check | Result | Evidence |
|---|---|---|
| Submit audit (job created) | PASS | `audit_jobs` row created with a UUID |
| Worker pipeline completed | PASS | `status=complete`, stage "Audit report complete" |
| Crawler rendered page(s) | PASS | `successful=1 failed=6 skipped=0` (internal 404s recorded, not fatal) |
| SEO extractor produced facts | PASS | `seo_status=complete` |
| UX/UI extractor produced facts | PASS | `uxui_status=complete` |
| PageSpeed collected or gracefully skipped | PASS | `psi_status=skipped` (no API key) |
| Deterministic scoring produced 3 scores | PASS | `seo=100 uxui=100 lead_gen=100` |
| Commentary generated | PASS | `status=fallback_missing_api_key provider=local_fallback` |
| Grounding validation ran | PASS | `validation_status=complete` |
| Branded PDF rendered | PASS | valid `%PDF`, ~41 KB on disk |
| Database result persisted & consistent | PASS | `audit_results` scores match the score breakdown |

**Result: 11/11 stage checks green.**

The same harness against `weak_site.html` also completes 11/11 and exercises the
low-score path (`seo=21 uxui=4 lead_gen=12`), confirming the calibration gate:
the strong sample site scores far higher than the weak one for explainable,
rule-level reasons.

---

## 3. P1-24 — Reproducibility QA Results

Command: `python scripts/qa_reproducibility.py` (runs the same site twice)

### Strong site

| Comparison | Result | Run 1 | Run 2 |
|---|---|---|---|
| SEO score | PASS | 100 | 100 |
| UX/UI score | PASS | 100 | 100 |
| Lead Gen score | PASS | 100 | 100 |
| Rubric version | PASS | `phase1-seo-v1+phase1-uxui-v1+phase1-composite-v1` | (same) |
| SEO rule breakdown | PASS | 13 rules identical | 13 rules identical |
| UX/UI rule breakdown | PASS | 14 rules identical | 14 rules identical |

### Weak site

| Comparison | Result | Run 1 | Run 2 |
|---|---|---|---|
| SEO score | PASS | 21 | 21 |
| UX/UI score | PASS | 4 | 4 |
| Lead Gen score | PASS | 12 | 12 |
| SEO / UX/UI rule breakdowns | PASS | identical | identical |

**Result: scores and every per-rule result are byte-for-byte reproducible.**

This satisfies the scoring gate: identical extracted facts always produce
identical SEO, UX/UI, and Lead Generation Readiness scores. Scores are produced
by the YAML rubric engine only; the LLM never influences a score.

---

## 4. Automated Test Suite

The unit suite covers each stage in isolation against the strong/weak/malformed
HTML fixtures (PSI client, extractors, scoring engine, grounding validator,
commentary, report payload, PDF renderer, report storage, audit API, worker
collection, and audit lifecycle).

```bash
make test     # pytest
```

All tests pass. The QA harness scripts are the integration/E2E layer on top of
that unit coverage.

---

## 5. Notes & Caveats

- **Live providers were intentionally not called** during QA so results are
  deterministic and free. To smoke-test the real OpenAI and PageSpeed paths, set
  `OPENAI_API_KEY` and `GOOGLE_PSI_API_KEY` in `.env` and submit an audit through
  the running stack (see the Operator Guide).
- **Crawled internal pages 404 in the harness** because the fixtures are single
  files; the crawler records them as failed pages without failing the audit,
  which is the intended resilience behavior.
- **A real builder-site smoke test** (live crawl + PSI + OpenAI through Docker
  Compose) is the recommended pre-demo check and is documented as a runbook in
  the Operator Guide; it is not part of the hermetic harness.
