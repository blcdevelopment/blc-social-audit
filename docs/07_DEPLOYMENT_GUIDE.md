# Internal Deployment Guide & Epic P1-E7 (Internal Deployment & Phase 2 Readiness)

> ## ⚠️ SUPERSEDED — historical record (banner added 2026-06-16)
>
> **This guide describes the earlier internal-testing deployment plan** (a single
> shared/VPS host on a private network/VPN, **no authentication**, manual UI serving,
> ports locked down by firewall). **That plan is no longer how the system is deployed.**
>
> The system is now **live in production** and is documented authoritatively in the root
> [`DEPLOYMENT.md`](../DEPLOYMENT.md). The production deployment is materially different:
> a single Linode VM running `docker-compose.prod.yml` (postgres, redis, api, worker,
> Next.js frontend, **Caddy** reverse proxy with **automatic Let's Encrypt TLS**),
> **Clerk authentication** (RS256 JWT / `__session` cookie), Google Search Console OAuth,
> and **GitHub Actions CI/CD** that auto-deploys on merge to `main` — all served at
> **https://ai.builderleadconverter.com**.
>
> **For anything current — deploying, configuring, auth, TLS, CI/CD, the live stack — use
> [`DEPLOYMENT.md`](../DEPLOYMENT.md), not this file.** Everything below is retained only as
> a historical record of the original internal-testing approach.

**Project:** BLC Website Audit Automation
**Client:** Builder Lead Converter (BLC)
**Document purpose:** Explain the best way to deploy the system for **internal testing**, point to the existing setup/run/operator docs, and define the Epic P1-E7 Jira plan.
**Planning principle:** Build locally first. This epic stands the working local system up on an internal/shared environment **for testing only** — not a public production launch.

> Setup and "how to run" are already documented. This guide intentionally does
> **not** repeat them — it focuses on **deployment for internal use** and links out:
> - Setup: [`docs/02_SETUP_GUIDE.md`](02_SETUP_GUIDE.md)
> - Run / operate: [`docs/05_OPERATOR_GUIDE.md`](05_OPERATOR_GUIDE.md)
> - Architecture: [`docs/03_ARCHITECTURE.md`](03_ARCHITECTURE.md)
> - Known limits: [`docs/06_KNOWN_LIMITATIONS.md`](06_KNOWN_LIMITATIONS.md)

---

## 1. Goal Of This Epic

Take the proven local-first system and make it reachable by the BLC team on an
internal environment so the team can run real audits against sites they provide,
capture what works and what breaks, fold those findings back into the docs, and
scope Phase 2. This is a **testing deployment**, not production hosting.

What "internal use" means here:

- A small number of trusted BLC team members on a private network or VPN.
- No public internet exposure, no authentication added yet. *(Superseded — the live system is public at https://ai.builderleadconverter.com behind Clerk auth; see [`DEPLOYMENT.md`](../DEPLOYMENT.md).)*
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

### 2.1 R&D Findings & Decision Record (P1-27)

**Cost / effort to stand up:**

| Option | Infra cost | Setup effort | Ongoing ownership |
|---|---|---|---|
| A. localhost | $0 | Minutes (already documented) | The operator keeps their machine on |
| B. shared internal host | $0 if a box already exists, else a small VM | ~1–2 hrs first time | One owner restarts/maintains the host |
| C. cloud VM (VPN/allowlist) | Low (small VM + VPN) | ~2–4 hrs (provision + lock down networking) | One owner + networking |
| D. managed/AWS | Ongoing (managed DB, compute, object storage, TLS) | Days — Phase 2 hardening must come first | Real ops burden |

**Decision (recommended):** Use **Option A** for the first single-operator smoke
test, then **Option B** — one shared internal host running the existing Docker
Compose stack, reachable only over the private network/VPN — for the team testing
window. Treat **Option D** as Phase 2.

**Why:**

- The Compose stack (postgres, redis, api, worker) already works and runs
  migrations on start, so Option B reuses proven infrastructure with near-zero new code.
- A single shared instance gives the team one URL and one shared audit history,
  which is exactly what a testing window needs — not uptime or scale.
- The app has **no authentication** and only **partial SSRF protection**, so every
  option must stay on a private network/VPN. That rules out public exposure and
  makes full managed/AWS hosting (Option D) premature until Phase 2 hardening.

**Constraints acknowledged** (see §4 and [`docs/06_KNOWN_LIMITATIONS.md`](06_KNOWN_LIMITATIONS.md)):
no auth, partial SSRF, local-filesystem report storage, dev-flavoured Compose.
All acceptable for a short internal test; none acceptable for public production.

**Revisit when:** the team needs external/client access, multiple concurrent
operators at scale, or persistent hosting — at which point Phase 2 (P1-32) takes over.

**Status:** ✅ Done — this section is the P1-27 deliverable.

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
# Edit .env — see docs/02_SETUP_GUIDE.md §3 for every key.
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
  downloads. (Full operating steps: [`docs/05_OPERATOR_GUIDE.md`](05_OPERATOR_GUIDE.md).)

### 3.6 VPS specifics (Option C): provision & lock down

Use this when the shared host is a cloud VM — a **plain VPS** (Lightsail,
DigitalOcean, Hetzner, a bare EC2 instance), **not** managed AWS. The app deploy
itself is still §3.2–§3.5; this subsection adds the provisioning and the network
lockdown an internet-facing VM needs.

> **Why lockdown is non-negotiable here.** The app has no authentication and only
> partial SSRF protection (§4). `docker-compose.yml` publishes the API on `0.0.0.0`
> (and `next start` serves the UI on `0.0.0.0` too), so on a public VM those ports
> are world-reachable unless a firewall blocks them. An exposed instance lets anyone
> run audits and make your server fetch arbitrary URLs. Lock it to your team
> **before** sharing the URL.

#### a. Pick the VM

| Item | Recommendation | Why |
|---|---|---|
| OS | Ubuntu 22.04 / 24.04 LTS | First-class Docker support |
| Size | ≥ 2 vCPU / 4 GB RAM | Postgres + Redis + API + worker **and** a headless Chromium crawl; 2 GB is tight |
| Disk | ≥ 20 GB | Images, Chromium, and PDFs/screenshots under `storage/` accumulate |
| Region | Near the team | Lower latency to the UI |

#### b. First-boot hardening (SSH)

```bash
# As root on the new VM: create a sudo user and use SSH key auth.
adduser blc && usermod -aG sudo blc
rsync --archive --chown=blc:blc ~/.ssh /home/blc        # copy your authorized key
```

Then in `/etc/ssh/sshd_config` set `PasswordAuthentication no` and
`PermitRootLogin no`, run `sudo systemctl restart ssh`, and log in as `blc` from here on.

#### c. Network lockdown — do this BEFORE bringing the app up

Pick **one** access method (a VPN is cleanest):

- **Option 1 — VPN (recommended): Tailscale / WireGuard.** Install it, join your
  tailnet, and have teammates reach the VM by its VPN IP.
- **Option 2 — IP allowlist.** Restrict access to your team's office/static IPs.

Then enforce it with the **cloud provider's firewall / security group** as the
primary control (network level, upstream of the host):

| Port | Allow from | Purpose |
|---|---|---|
| 22 (SSH) | your IPs / VPN only | admin |
| 8000 (API) | VPN / team allowlist only | backend |
| 3000 (UI) | VPN / team allowlist only | operator UI |
| everything else | **deny** | — |

> **Docker + `ufw` gotcha:** Docker writes its own iptables rules and can bypass a
> host `ufw` config for *published* ports. Don't rely on `ufw` alone for 8000/3000 —
> enforce it at the **cloud security-group / firewall** level (or don't publish the
> ports publicly at all and reach them only over the VPN interface).

#### d. Install Docker + Node

```bash
# Docker Engine + Compose plugin (Ubuntu)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker blc          # log out/in so group membership applies

# Node.js 20 for the operator UI
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

#### e. Deploy the app (VPS notes on top of §3.2–§3.5)

- In `.env`: set a real `POSTGRES_PASSWORD` and set `API_CORS_ORIGINS` to the URL
  teammates actually use (e.g. `http://<vpn-ip>:3000`). Keep `CRAWLER_ALLOW_PRIVATE_HOSTS=false`.
- Run the backend **detached** so it survives your SSH session:

  ```bash
  docker compose up --build -d        # detached (note: -d; `make docker-up` runs in the foreground)
  docker compose logs -f              # follow logs when needed
  ```

- Serve the UI **built** (not the dev server) and keep it running past logout:

  ```bash
  cd apps/frontend
  npm ci
  NEXT_PUBLIC_API_BASE_URL=http://<vpn-ip>:8000 npm run build
  nohup npm run start >/tmp/blc-ui.log 2>&1 &     # or run it under pm2 / a systemd unit
  ```

#### f. Verify + hand off

- From a teammate **on the VPN/allowlist**: `curl http://<vpn-ip>:8000/health` returns OK.
- From an **outside** network: the same request should **time out or be refused** —
  that's the proof your lockdown works.
- Run one end-to-end audit from the UI and confirm the PDF downloads.
- Share the internal URL plus a one-line note: "internal test tool — do not share
  publicly."

---

## 4. Security Notes For Internal Use (read before exposing)

The system is internal-only by design (see [`docs/06_KNOWN_LIMITATIONS.md`](06_KNOWN_LIMITATIONS.md)):

- **No authentication.** *(Superseded — the live system now has Clerk authentication
  gating the `/audits/*` router; see [`DEPLOYMENT.md`](../DEPLOYMENT.md).)* Anyone who can
  reach the API/UI can run audits and read
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

**Status legend:** ✅ Done · ◐ Doc ready, pending human action · ⬜ To do.

### P1-27 R&D: Deployment Options For Internal Use — ✅ Done

**Issue type:** Task
**Goal:** Compare realistic ways to deploy the existing stack for internal testing and write down the trade-offs.
**Deliverable:** Findings + decision record in §2 and §2.1 of this doc.
**Subtasks:**

- [x] Review the existing Docker Compose stack and frontend run/build options.
- [x] List options: localhost, shared internal host, cloud VM (VPN/allowlist), managed/AWS.
- [x] Capture pros/cons, cost, and security implications of each.
- [x] Note constraints: no auth, partial SSRF, local-only storage.
- [x] Record findings in this doc (§2, §2.1).

### P1-28 Choose & Document The Internal Deployment Approach — ◐ Doc ready, pending host sign-off

**Issue type:** Task
**Goal:** Pick the recommended approach for the team test window and write a repeatable runbook.
**Deliverable:** Decision in §2.1; generic runbook in §3; VPS provisioning + lockdown in §3.6; security guardrails in §4.
**Subtasks:**

- [x] Select the approach (VPS running Docker Compose, locked to VPN/IP allowlist).
- [x] Define host prerequisites and required `.env` changes (real DB password, CORS origins, optional API keys).
- [x] Write the step-by-step deploy + UI-serve runbook (§3, §3.6).
- [x] Document the internal-use security guardrails (§4).
- [ ] Get sign-off from the team owner of the host. *(human action)*

### P1-29 Stand Up The Internal Test Deployment — ⬜ To do

**Issue type:** Task
**Goal:** Get a working, team-reachable instance running on the chosen internal environment.
**Subtasks:**

- Provision/identify the host and install Docker + Node.
- Clone repo, configure `.env`, run `make docker-up` (migrations run on start).
- Build/serve the operator UI with the correct `NEXT_PUBLIC_API_BASE_URL`.
- Confirm `/health`, run one end-to-end smoke audit, confirm PDF download.
- Share the internal URL + short usage note with the team.

### P1-30 Validate The System On Team-Provided Sites — ⬜ To do

**Issue type:** Task
**Goal:** Run real audits on sites the team provides and capture results and failures.
**Subtasks:**

- Collect the list of test sites from the team.
- Run an audit on each; record status, scores, and PDF.
- Log failures/edge cases (JS-heavy, bot-protected, missing PSI, failed internal pages).
- Note crawler page-cap effects and any scoring surprises.
- Summarize results in a short test log.

### P1-31 Update Documentation With Deployment & Test Insights — ⬜ To do

**Issue type:** Task
**Goal:** Fold everything learned back into the docs so the next person can repeat it.
**Subtasks:**

- Update this guide (§2–§4) with anything that changed during the real deploy.
- Add deployment/test caveats to [`docs/06_KNOWN_LIMITATIONS.md`](06_KNOWN_LIMITATIONS.md).
- Update the README pointer to this guide if needed.
- Capture the test-site results summary as an appendix or linked note.
- Note any `.env` / CORS / networking gotchas discovered.

### P1-32 R&D: Phase 2 Scope & Readiness — ◐ Draft ready, pending P1-30 feedback

**Issue type:** Task
**Goal:** Use the internal test results to scope Phase 2 (productionization + deferred features).
**Deliverable:** Phase 2 scope / approach / timeline draft in [`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md) (grounded in the original scope docs — external `*.docx` files, gitignored and not committed; their content lives in [`docs/01_REQUIREMENTS.md`](01_REQUIREMENTS.md)).
**Subtasks:**

- [x] List production-hardening needs: authentication, complete SSRF interception, TLS, object storage, monitoring/backups, data retention.
- [x] Evaluate hosting target (managed/AWS) and rough cost.
- [x] Capture deferred product scope (social audits, live competitor-benchmarking providers,
  analytics integrations). The benchmarking presentation scaffold later shipped, while the paid
  provider clients remain deferred.
- [ ] Prioritize Phase 2 candidates against test feedback. *(needs P1-30 results)*
- [x] Draft a Phase 2 epic outline for review (§8).

---

## 7. Done Criteria For P1-E7

Epic P1-E7 is complete when:

- The deployment options and the chosen approach are documented (P1-27, P1-28).
- A team-reachable internal instance is running and passed a smoke audit (P1-29).
- Real team-provided sites have been audited and results/failures recorded (P1-30).
- The docs reflect the real deployment and test findings (P1-31).
- A reviewed Phase 2 scope/readiness outline exists (P1-32) — see [`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md).
