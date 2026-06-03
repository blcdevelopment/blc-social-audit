# Internal Deployment Guide & Epic P1-E7 (Internal Deployment & Phase 2 Readiness)

**Project:** BLC Website Audit Automation
**Client:** Builder Lead Converter (BLC)
**Document purpose:** Explain the best way to deploy the system for **internal testing**, point to the existing setup/run/operator docs, and define the Epic P1-E7 Jira plan.
**Planning principle:** Build locally first. This epic stands the working local system up on an internal/shared environment **for testing only** — not a public production launch.

> Setup and "how to run" are already documented. This guide intentionally does
> **not** repeat them — it focuses on **deployment for internal use** and links out:
> - Setup: [`docs/07_SETUP_GUIDE.md`](07_SETUP_GUIDE.md)
> - Run / operate: [`docs/10_OPERATOR_GUIDE.md`](10_OPERATOR_GUIDE.md)
> - Architecture: [`docs/08_ARCHITECTURE_OVERVIEW.md`](08_ARCHITECTURE_OVERVIEW.md)
> - Known limits: [`docs/11_KNOWN_LIMITATIONS.md`](11_KNOWN_LIMITATIONS.md)

---

## 1. Goal Of This Epic

Take the proven local-first system and make it reachable by the BLC team on an
internal environment so the team can run real audits against sites they provide,
capture what works and what breaks, fold those findings back into the docs, and
scope Phase 2. This is a **testing deployment**, not production hosting.

What "internal use" means here:

- A small number of trusted BLC team members on a private network or VPN.
- No public internet exposure, no authentication added yet.
- The goal is **validation and feedback**, not uptime or scale.

---

## 2. Deployment Options Considered

The repo already ships a working Docker Compose stack (`docker-compose.yml`) with
PostgreSQL, Redis, the FastAPI API, and the Celery worker, plus a Next.js operator
UI in `apps/frontend`. The options below build on that.

| Option | What it is | Pros | Cons | Use when |
|---|---|---|---|---|
| **A. Single operator, localhost** | One person runs the stack on their own machine (`make docker-up` + `make run-frontend`) | Zero infra, fastest to start, already documented | Only one user, results not shared, machine must stay on | A single operator just needs to test |
| **B. Shared internal host + Docker Compose** *(recommended for team testing)* | One always-on internal box (shared dev server or small cloud VM on the team VPN) runs the stack; teammates hit it over the private network | Whole team can use one instance, one shared audit history, reuses the existing Compose stack | Needs one host + someone to own it; current Compose is dev-flavored | The team needs to test together during a testing window |
| **C. Small cloud VM, locked to VPN/allowlist** | Same as B but on a cloud VM (EC2/Lightsail/DigitalOcean) reachable only via VPN or IP allowlist | Off-laptop, stable URL for the test window | Small cloud cost, must lock down networking (no auth in app yet) | Team is distributed and a shared laptop won't work |
| **D. Full managed/AWS production** | Managed Postgres, container orchestration, object storage, TLS, auth, monitoring | Real production posture | Out of scope for testing; depends on Phase 2 hardening (auth, SSRF, storage) | **Deferred — Phase 2**, see §6 |

**Recommendation:** Start with **Option A** for a single operator smoke test, then
use **Option B** (one shared internal host, Docker Compose, private network/VPN
only) for the team testing window. Treat **Option D** as Phase 2.

---

## 3. Recommended Internal Deployment (Option B)

A single internal host that the team reaches over the private network/VPN.

### 3.1 Host prerequisites

- A Linux host (or always-on machine) on the team's private network or VPN.
- Docker + Docker Compose installed.
- Node.js 18+ and npm (to run/build the operator UI).
- Outbound internet access (for OpenAI and PageSpeed Insights, if keys are set).

### 3.2 Get the code and configure

```bash
git clone <repo-url> blc-website-audit
cd blc-website-audit
cp .env.template .env
# Edit .env — see docs/07_SETUP_GUIDE.md §3 for every key.
```

Minimum `.env` review before an internal deployment:

- Set a real `POSTGRES_PASSWORD` (do **not** keep `change-me-local`).
- Optionally set `OPENAI_API_KEY` and `GOOGLE_PSI_API_KEY`. Without them the audit
  still completes (local commentary fallback, PSI rules skipped) — fine for a first test.
- Keep `CRAWLER_ALLOW_PRIVATE_HOSTS=false`.
- Set `API_CORS_ORIGINS` to include the URL teammates will use for the UI.

### 3.3 Bring up the backend stack

```bash
make docker-up        # builds + starts postgres, redis, api (runs migrations), worker
```

The API listens on `:8000` (`/docs` for OpenAPI). The Compose `api` service runs
`alembic upgrade head` on start, so the database schema is created automatically.

### 3.4 Serve the operator UI

The UI is **not** part of Compose. For a testing deployment, either:

```bash
# Simple (dev server):
cd apps/frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://<host>:8000 npm run dev   # serves :3000
```

or build it for a steadier test instance:

```bash
cd apps/frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://<host>:8000 npm run build
npm run start                                            # serves :3000
```

Teammates then open `http://<host>:3000`. Make sure `<host>:8000` (API) and
`<host>:3000` (UI) are reachable on the private network and that the API origin
list (`API_CORS_ORIGINS`) includes the UI URL.

### 3.5 Smoke-check the deployment

- `GET http://<host>:8000/health` returns OK.
- Submit one audit from the UI and confirm it reaches `completed` and the PDF
  downloads. (Full operating steps: [`docs/10_OPERATOR_GUIDE.md`](10_OPERATOR_GUIDE.md).)

---

## 4. Security Notes For Internal Use (read before exposing)

The system is internal-only by design (see [`docs/11_KNOWN_LIMITATIONS.md`](11_KNOWN_LIMITATIONS.md)):

- **No authentication.** Anyone who can reach the API/UI can run audits and read
  results. **Keep it on a private network/VPN. Do not expose it to the public internet.**
- **SSRF protection is partial.** Submitted URLs are untrusted input; private-host
  blocking is on, but request-level interception is not complete.
- **Secrets live in `.env`.** Restrict file permissions; no secrets manager yet.
- **The Compose stack is dev-flavored** (`--reload`, bind mount). That is acceptable
  for a short testing window; production hardening (TLS, auth, real storage,
  monitoring) is **Phase 2** work, not this epic.

---

## 5. What This Epic Does NOT Cover

- Public hosting, custom domains, or TLS termination.
- Authentication / user accounts.
- Object storage (S3) for reports — still local filesystem.
- Monitoring, alerting, backups, autoscaling.

These are tracked as Phase 2 / production-hardening candidates (see §6 R&D ticket).

---

## 6. Epic P1-E7: Internal Deployment & Phase 2 Readiness

**Epic name:** `P1-E7: Internal Deployment & Phase 2 Readiness`
**Fix Version:** Phase 1 (closeout) → Phase 2 (R&D)
**Labels:** `phase-1`, `website-audit`, `internal-deploy`, `blc`
**Description:** Research the best way to deploy the working local-first system for
internal testing, stand it up on an internal/shared environment, validate it
against real sites provided by the team, fold the findings back into the docs, and
scope Phase 2.

Recommended order: P1-27 → P1-28 → P1-29 → P1-30 → P1-31 → P1-32.

### P1-27 R&D: Deployment Options For Internal Use

**Issue type:** Task
**Goal:** Compare realistic ways to deploy the existing stack for internal testing and write down the trade-offs.
**Subtasks:**

- Review the existing Docker Compose stack and frontend run/build options.
- List options: localhost, shared internal host, cloud VM (VPN/allowlist), managed/AWS.
- Capture pros/cons, cost, and security implications of each.
- Note constraints: no auth, partial SSRF, local-only storage.
- Record findings in this doc (§2).

### P1-28 Choose & Document The Internal Deployment Approach

**Issue type:** Task
**Goal:** Pick the recommended approach for the team test window and write a repeatable runbook.
**Subtasks:**

- Select the approach (recommendation: shared internal host + Docker Compose, VPN-only).
- Define host prerequisites and required `.env` changes (real DB password, CORS origins, optional API keys).
- Write the step-by-step deploy + UI-serve runbook (§3).
- Document the internal-use security guardrails (§4).
- Get sign-off from the team owner of the host.

### P1-29 Stand Up The Internal Test Deployment

**Issue type:** Task
**Goal:** Get a working, team-reachable instance running on the chosen internal environment.
**Subtasks:**

- Provision/identify the host and install Docker + Node.
- Clone repo, configure `.env`, run `make docker-up` (migrations run on start).
- Build/serve the operator UI with the correct `NEXT_PUBLIC_API_BASE_URL`.
- Confirm `/health`, run one end-to-end smoke audit, confirm PDF download.
- Share the internal URL + short usage note with the team.

### P1-30 Validate The System On Team-Provided Sites

**Issue type:** Task
**Goal:** Run real audits on sites the team provides and capture results and failures.
**Subtasks:**

- Collect the list of test sites from the team.
- Run an audit on each; record status, scores, and PDF.
- Log failures/edge cases (JS-heavy, bot-protected, missing PSI, failed internal pages).
- Note crawler page-cap effects and any scoring surprises.
- Summarize results in a short test log.

### P1-31 Update Documentation With Deployment & Test Insights

**Issue type:** Task
**Goal:** Fold everything learned back into the docs so the next person can repeat it.
**Subtasks:**

- Update this guide (§2–§4) with anything that changed during the real deploy.
- Add deployment/test caveats to [`docs/11_KNOWN_LIMITATIONS.md`](11_KNOWN_LIMITATIONS.md).
- Update the README pointer to this guide if needed.
- Capture the test-site results summary as an appendix or linked note.
- Note any `.env` / CORS / networking gotchas discovered.

### P1-32 R&D: Phase 2 Scope & Readiness

**Issue type:** Task
**Goal:** Use the internal test results to scope Phase 2 (productionization + deferred features).
**Subtasks:**

- List production-hardening needs: authentication, complete SSRF interception, TLS, object storage, monitoring/backups, data retention.
- Evaluate hosting target (managed/AWS) and rough cost.
- Capture deferred product scope (social audits, competitor benchmarking, analytics integrations).
- Prioritize Phase 2 candidates against test feedback.
- Draft a Phase 2 epic outline for review.

---

## 7. Done Criteria For P1-E7

Epic P1-E7 is complete when:

- The deployment options and the chosen approach are documented (P1-27, P1-28).
- A team-reachable internal instance is running and passed a smoke audit (P1-29).
- Real team-provided sites have been audited and results/failures recorded (P1-30).
- The docs reflect the real deployment and test findings (P1-31).
- A reviewed Phase 2 scope/readiness outline exists (P1-32).
