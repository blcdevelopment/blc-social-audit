# Known Limitations (P1-26)

An honest list of what Phase 1 does **not** do, plus important behavioral
caveats. Phase 1 is a local-first website-audit MVP; several items below are
deliberately deferred to later phases or to production hardening.

_Last reconciled: 2026-06-16._

---

## 1. Scope (intentionally out)

These were out of scope for **Phase 1** by design (see [`docs/01_REQUIREMENTS.md`](01_REQUIREMENTS.md)).

> **Phase-2 as-built update (2026-06-25):** several items below have since SHIPPED — the
> standalone **Social audit** (Instagram + Facebook via Apify, YouTube via the YouTube Data API),
> **public token-gated share links**, **white-label brand overrides** on the PDF, and **production
> hosting** (Linode + Caddy + CI/CD). They are annotated below; the rest remain out of scope.
> Trust [`CLAUDE.md`](../CLAUDE.md) for as-built truth.

- ~~**Social media audits** (Instagram/Facebook/LinkedIn/YouTube).~~ **SHIPPED (Phase 2)** as a
  standalone audit type — Instagram + Facebook + YouTube (LinkedIn still out of scope). See
  `CLAUDE.md` §5.
- **Multi-tenancy.** The UI/API is still an internal shared tool, not a tenant-aware
  SaaS product.
- **Competitor benchmarking** (SEMrush/Ahrefs/Similarweb).
- **Full analytics integrations** (GA4, Microsoft Clarity, CRM attribution). Search
  Console enrichment exists, but only for verified properties connected through Google OAuth.
- ~~**Public share links / white-label self-service.**~~ **SHIPPED (Phase 2):** token-gated
  `/shared/{token}` report links + per-client white-label brand overrides on the PDF.
- ~~**Hosted/AWS production infrastructure.**~~ **SHIPPED (Phase 2):** live on Linode + Caddy +
  CI/CD (AWS specifically was not used). See `DEPLOYMENT.md`.

---

## 2. Security & Access

- **Authentication is live but optional by environment.** Clerk UI/API auth is wired in:
  the whole `/audits/*` router is gated with `Depends(require_user)`, and the frontend
  forwards a fresh Clerk bearer token on every API call. Auth is **opt-in** — when
  `CLERK_ISSUER` is empty, `require_user()` returns `None` and the API is **open**, which is
  exactly how local dev, the unit tests, and the QA harness run unauthenticated. Production
  sets `CLERK_ISSUER` (the prod compose has a fail-fast `${CLERK_ISSUER:?}` guard) along with
  `CLERK_AUTHORIZED_PARTIES` and the frontend Clerk keys. The Google OAuth callback
  (`GET /google/search-console/callback`) is intentionally unauthenticated because Google
  calls it; it is protected instead by an HMAC-signed, time-limited CSRF `state`.
- **Clerk is currently a DEV instance** (`pk_test_…`). **Open sign-up is a known security
  gap**: anyone can self-register on the dev instance, so invitation-only access is a manual
  operator step today. Switching to a Clerk production instance and locking down sign-up is
  productionization work.
- **SSRF protection is partial.** The page crawler blocks private/loopback hosts by
  default (`CRAWLER_ALLOW_PRIVATE_HOSTS=false`), validates the start URL, and re-validates the
  post-redirect host — but mid-crawl request-level interception (blocking sub-resources or
  redirect hops that resolve to internal IPs while a page is rendering) is **not** fully
  implemented for the page crawler. By contrast, the **site-health sweep re-validates every
  redirect hop** through the same SSRF guard, so its redirect-SSRF gap is closed. Treat
  submitted URLs as untrusted input and harden the page crawler before exposing the service
  publicly.
- Secrets live in `.env`; there is no secrets manager integration yet.
- Google Search Console refresh tokens are stored in the application database for the
  local-first implementation. Production should encrypt these fields or move them into a
  managed secrets store before connecting real client accounts.

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

## 5. External SEO Enrichment

- The **technical crawl** slot is filled by the built-in **site health sweep** by default
  (plain-HTTP status checks over discovered internal/outbound links + sitemap.xml, plus
  duplicate/missing-metadata checks over the rendered pages). It is deterministic given the
  site's state, runs in Docker, and needs no licence. Coverage limits (`SITE_HEALTH_MAX_*`,
  time budget) are recorded as coverage notes in the report rather than silently truncated.
- The sweep's URL discovery is bounded by what the rendered pages link to plus the sitemap;
  it does not do a full-site BFS crawl, so deep orphaned sections may not be checked.
- On an **enrichment rerun**, page HTML is no longer in memory, so outbound links are not
  rechecked (noted in the report); run a fresh audit for full outbound coverage.
- **Screaming Frog is optional and deliberately NOT installed in the Docker images**: its
  CLI/headless mode is licence-gated, licences are per-individual-user (a shared server key
  for several operators violates Screaming Frog's terms and risks the key being blocked),
  and the JVM wants 2–4 GB RAM — more than the production box can spare. It remains
  supported for a licensed operator machine via `SCREAMING_FROG_ENABLED` + binary path;
  when it completes, its data fills the technical crawl slot instead of the sweep, and its
  subprocess timeout is clamped under the Celery soft time limit.
- Search Console data is available only for Google properties the connected account can
  access. No matching property means GSC and URL Inspection facts are skipped.
- The app uses official Google APIs. It does not scrape the Search Console Insights UI.
- URL Inspection is quota-limited and only runs for a small priority URL set; runs with
  per-URL failures are reported as `partial` and never count toward the score.
- Google OAuth/refresh tokens are stored **unencrypted** in the `google_search_console_connections`
  table (single-tenant internal DB). Encrypting them at rest is open productionization work.

---

## 6. Commentary

- **Phase 1 commentary is fully deterministic — there is no LLM call at all.**
  `generate_commentary()` always builds a deterministic content plan
  (`build_content_plan()`) from the extracted facts and scores and returns it with
  `status`/`provider`/`model` set to `"deterministic"`, with or without an
  `OPENAI_API_KEY`. There is no "OpenAI-then-fallback" behaviour in Phase 1: the
  content plan **is** the output unconditionally, so commentary is consistent run to
  run but is not LLM-written site-specific prose.
- The dormant `_call_openai()` scaffolding and the `prompts/*.md` templates are wired
  only into a **deferred Phase 2 polish layer** that will rewrite the plan's prose
  strings when a key is configured, **without** changing structure, severities, or
  ordering. LLM polish is **not** a Phase 1 feature.
- The **grounding validator strips unsupported _numeric_ claims** by comparing
  numbers in the commentary against extracted facts (timeframe phrases such as
  "1–3 months" are masked first so they survive). If stripping would empty a field
  it reverts to the baseline prose. It does not catch every possible non-numeric
  inaccuracy — scores remain the deterministic source of truth, and commentary is
  explanatory only.

---

## 7. Reproducibility — the precise guarantee

- **Scores are reproducible given identical extracted facts** (verified by the
  hermetic QA harness — `make qa-repro`). The rubric engine is pure and deterministic.
- **Live sites change over time** and **PSI varies run-to-run**, so re-auditing a
  real site later can produce different facts and therefore different scores. The
  reproducibility guarantee is about the scoring engine, not about the external
  world staying still.

---

## 8. Data & Storage

- **Report storage is local filesystem only.** PDFs are written under
  `storage/reports/`; there is no object-storage backend.
- **Database migrations target PostgreSQL** (they enable `pgcrypto`). SQLite is
  only used by the QA harness via `create_all`, not via Alembic.
- No data retention/cleanup policy: old audit rows, PDFs, and screenshots
  accumulate under `storage/` until manually pruned.

---

## 9. Operations & Observability

- **No monitoring, alerting, or error tracking** (e.g. Sentry) wired up.
- **No retry/dead-letter handling** beyond Celery's task time limits; a job that
  exceeds `CELERY_TASK_SOFT_TIME_LIMIT_SECONDS` is marked `failed`.
- **No horizontal-scale tuning**; a single worker processes audits.
- The local Docker Compose stack uses a dev bind-mount and `--reload`; it is for
  development, not production serving.

---

## 10. Recommended Next Steps (later phases)

1. Harden the now-live Clerk auth: move to a Clerk **production** instance and close open
   sign-up (invitation-only). _(Request-level SSRF interception in the crawler is now DONE —
   `crawler_intercept_requests`.)_
2. Encrypt Google OAuth/refresh tokens at rest (or move them into a secrets manager).
3. ~~Add data retention/cleanup for `storage/` and old audit rows.~~ **DONE** —
   `cleanup_storage` + `STORAGE_RETENTION_DAYS` (cron on the host).
4. Continue the deferred scope (competitor benchmarking, analytics) as separate phases.
   _(Social audits already SHIPPED in Phase 2.)_
