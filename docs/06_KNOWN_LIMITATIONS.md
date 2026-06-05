# Known Limitations (P1-26)

An honest list of what Phase 1 does **not** do, plus important behavioral
caveats. Phase 1 is a local-first website-audit MVP; several items below are
deliberately deferred to later phases or to production hardening.

---

## 1. Scope (intentionally out)

These are out of scope for Phase 1 by design (see [`docs/01_REQUIREMENTS.md`](01_REQUIREMENTS.md)):

- **Social media audits** (Instagram/Facebook/LinkedIn/YouTube).
- **User accounts, authentication, multi-tenancy.** The UI/API is an internal,
  single-operator tool with no login.
- **Competitor benchmarking** (SEMrush/Ahrefs/Similarweb).
- **Analytics integrations** (Google Analytics, Search Console, Microsoft Clarity).
- **Public share links / white-label self-service.**
- **Hosted/AWS production infrastructure** (packaging is prepared, hosting is not).

---

## 2. Security & Access

- **No API/UI authentication.** Anyone who can reach the API can submit audits and
  read results. Acceptable for local/internal use only. API auth is deferred to
  productionization.
- **SSRF protection is partial.** The crawler blocks private/loopback hosts by
  default (`CRAWLER_ALLOW_PRIVATE_HOSTS=false`) and validates the start URL, but
  request-level interception (e.g. blocking redirects/sub-resources that resolve
  to internal IPs mid-crawl) is **not** fully implemented. Treat submitted URLs as
  untrusted input and harden this before exposing the service publicly.
- Secrets live in `.env`; there is no secrets manager integration yet.

---

## 3. Crawler

- **Page cap:** up to `CRAWLER_MAX_PAGES` (default 10) total pages, homepage plus
  selected same-site internal links. Large sites are sampled, not fully crawled.
- **Same-site only.** External and cross-subdomain links are not followed.
- **Failed internal pages are recorded, not retried.** A page that times out or
  errors is logged and the audit continues on the rest.
- **JavaScript-heavy or bot-protected sites** may render incompletely or be
  blocked; results then reflect what was actually rendered.

---

## 4. PageSpeed Insights

- Requires `GOOGLE_PSI_API_KEY`. Without it, PSI rules are **skipped** (scores
  rescale around them — no penalty).
- PSI is an external service: it can rate-limit, time out, or vary between runs.
  PSI-dependent rules can therefore differ across live runs even for the same
  site. (The hermetic QA harness avoids this by skipping PSI.)

---

## 5. AI Commentary

- Requires `OPENAI_API_KEY`. Without it, commentary uses a **deterministic local
  fallback** that is correct but generic (not site-specific prose).
- The **grounding validator strips unsupported _numeric_ claims** by comparing
  numbers in the commentary against extracted facts. It does not catch every
  possible non-numeric inaccuracy — scores remain the deterministic source of
  truth, and commentary is explanatory only.
- OpenAI output is non-deterministic; commentary wording varies between runs even
  though scores do not.

---

## 6. Reproducibility — the precise guarantee

- **Scores are reproducible given identical extracted facts** (verified by the
  hermetic QA harness — `make qa-repro`). The rubric engine is pure and deterministic.
- **Live sites change over time** and **PSI varies run-to-run**, so re-auditing a
  real site later can produce different facts and therefore different scores. The
  reproducibility guarantee is about the scoring engine, not about the external
  world staying still.

---

## 7. Data & Storage

- **Report storage is local filesystem only.** PDFs are written under
  `storage/reports/`; there is no object-storage backend.
- **Database migrations target PostgreSQL** (they enable `pgcrypto`). SQLite is
  only used by the QA harness via `create_all`, not via Alembic.
- No data retention/cleanup policy: old audit rows, PDFs, and screenshots
  accumulate under `storage/` until manually pruned.

---

## 8. Operations & Observability

- **No monitoring, alerting, or error tracking** (e.g. Sentry) wired up.
- **No retry/dead-letter handling** beyond Celery's task time limits; a job that
  exceeds `CELERY_TASK_SOFT_TIME_LIMIT_SECONDS` is marked `failed`.
- **No horizontal-scale tuning**; a single worker processes audits.
- The local Docker Compose stack uses a dev bind-mount and `--reload`; it is for
  development, not production serving.

---

## 9. Recommended Next Steps (later phases)

1. Add API/UI authentication and complete request-level SSRF interception.
2. Add data retention/cleanup for `storage/` and old audit rows.
3. Begin the deferred scope (social audits, competitor benchmarking, analytics)
   as separate phases.
