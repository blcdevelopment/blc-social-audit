# Deployment Guide — BLC Website Audit

> **Status (2026-06-10): ✅ Build-verified, ready to deploy.** *(Last verified against the
> code: 2026-06-23 — stack, Caddy routing, CI/CD flow, and the `deploy/deploy.sh` `/health`
> gate all still match. This pass added: migration head `20260623_0003`, the new env vars
> (Apify / Sentry / retention / share-link), the storage-retention cron, and the public
> token-gated share endpoints.)*
>
> **Update (2026-06-23):** the **standalone Social audit is now BUILT and runnable** (not just a
> data layer). Ops impact: migration head is now **`20260623_0004`** (additive; auto-runs on
> deploy) and **`APIFY_API_TOKEN` is required on the box for social audits** (blank ⇒ social
> collection is skipped; website audits unaffected). The provider is **Apify** with **two
> actors** — Instagram Scraper (`apify~instagram-scraper`) + Facebook Pages Scraper
> (`apify~facebook-pages-scraper`) — and a social audit renders its **own separate branded PDF**
> (no DOCX). Website auditing is untouched.
> All three production images (`api`, `frontend`, `worker`) build cleanly and the
> auth/architecture has been reviewed end-to-end. The remaining work is **operator-side
> only** (secrets, the box, and the Clerk dashboard) — no code changes are required.
>
> Target: a single Linode running the full stack via Docker Compose behind Caddy
> (automatic HTTPS) on **https://ai.builderleadconverter.com**, for ~2–3 internal users.

This document is the single source of truth for *how this app is deployed and operated*.
For *how the app is built* (pipeline, scoring, conventions), see [CLAUDE.md](CLAUDE.md) and
[docs/03_ARCHITECTURE.md](docs/03_ARCHITECTURE.md).

---

## 1. What we are deploying

A Phase-1 website-audit app: submit a URL → crawl with Playwright → collect PageSpeed
Insights → extract SEO + UX/UI facts (plus an external-SEO sweep) → score deterministically
→ generate grounded, fully deterministic commentary (Phase 1 calls no LLM) → render a
branded PDF (DOCX on demand) → expose it through a Next.js operator UI.

| Layer | Tech | Container |
|---|---|---|
| Reverse proxy + TLS | Caddy 2 (auto Let's Encrypt) | `caddy` |
| Operator UI | Next.js 14 (standalone build) + Clerk | `frontend` |
| API | FastAPI + uvicorn, Clerk JWKS auth | `api` |
| Async jobs | Celery + Playwright/Chromium | `worker` |
| Database | PostgreSQL 16 | `postgres` |
| Broker / results | Redis 7 | `redis` |

**Auth:** Clerk gates the UI (sign-in required) and the API (every `/audits` endpoint
verifies a Clerk session token). See [§7](#7-security).

**Out of scope here:** multi-tenant auth/roles, benchmarking/analytics. Object
storage was evaluated and **removed by decision** (reports stay on the local filesystem). See
[§9 Roadmap](#9-roadmap).

> **Update (2026-06-23):** social-media auditing is **no longer out of scope** — the standalone
> Social audit type ships and is runnable from the browser (its own report + Social Score,
> independent of the website composite). Its one ops dependency is `APIFY_API_TOKEN` (see
> [§4](#4-the-server--prerequisites) / [§5 step 4](#step-4--create-the-production-env-on-the-box)).

---

## 2. Current situation

### What's done
- **Production stack authored & build-verified** — [docker-compose.prod.yml](docker-compose.prod.yml),
  [Caddyfile](Caddyfile), [apps/frontend/Dockerfile](apps/frontend/Dockerfile),
  [apps/api/Dockerfile](apps/api/Dockerfile), [apps/worker/Dockerfile](apps/worker/Dockerfile).
- **Clerk auth wired on both ends** — API: [apps/api/auth.py](apps/api/auth.py) (opt-in via
  `CLERK_ISSUER`, verifies `__session` cookie / Bearer against JWKS), enforced as a router
  dependency in [apps/api/routes/audits.py](apps/api/routes/audits.py). Frontend:
  [_app.tsx](apps/frontend/pages/_app.tsx) `<SignedIn>/<SignedOut>` gate +
  [middleware.ts](apps/frontend/middleware.ts) + `UserButton`.
- **Dependencies in sync** — `pyjwt[crypto]` (pyproject/poetry.lock/requirements.txt) and
  `@clerk/nextjs` (package.json + package-lock.json, lockfileVersion 3, `npm ci` verified).
- **Image hygiene** — [.dockerignore](.dockerignore) keeps `.env`, `.git`, `node_modules`,
  and `storage/` out of the images.

### What's verified (2026-06-10)
| Check | Result |
|---|---|
| `docker build` api / frontend / worker | ✅ all pass (1.32 GB / 226 MB / 2.78 GB) |
| `npm ci` lockfile sync + `next build` | ✅ 5 pages + middleware + standalone |
| Same-origin `__session` cookie → Caddy → API auth path | ✅ sound |
| `alembic upgrade head` on a fresh DB | ✅ (env.py overrides the DB URL from settings) |
| api ↔ worker share the `storage` volume (PDF download) | ✅ |
| Compose fail-fast guards (`:?` on required secrets) | ✅ |

### What is NOT yet done (operator-side — see [§5 Runbook](#5-deployment-runbook))
1. Commit + push the deploy files to `main` (they are currently untracked/uncommitted).
2. Create the production `.env` on the box (real secrets, esp. `CLERK_ISSUER`).
3. Restrict Clerk sign-up to invitation-only.
4. Rotate the SSH password + Clerk secret key (both were shared in chat).
5. Run the post-deploy smoke test (a real signed-in audit has not been tested yet).

---

## 3. Production architecture

```
                Internet  (HTTP :80  /  HTTPS :443)
                                │
                                ▼
                         ┌─────────────┐   Let's Encrypt auto-TLS
                         │    Caddy     │   ai.builderleadconverter.com
                         └──────┬───────┘
                  one origin →  │  reverse proxy
              ┌─────────────────┴──────────────────┐
       /api/* │ (strip prefix)                      │ /*
              ▼                                      ▼
        ┌───────────┐                          ┌────────────┐
        │   api     │  FastAPI :8000           │  frontend  │  Next.js :3000
        └─────┬─────┘                          └────────────┘
              │                                   (server reads CLERK_SECRET_KEY)
   ┌──────────┼───────────┐
   ▼          ▼           ▼
┌────────┐ ┌───────┐  ┌─────────┐
│postgres│ │ redis │◄─│ worker  │  Celery + Playwright/Chromium (--concurrency=1)
│ :5432  │ │ :6379 │  └────┬────┘
└────────┘ └───────┘       │
   ▲                       │
   └───── api + worker write/read the SAME `storage` volume (PDFs, screenshots)

Only Caddy publishes ports (80/443). postgres/redis/api/frontend/worker are internal-only.
Named volumes: postgres_data · storage (shared) · caddy_data · caddy_config
```

Key design points:
- **Single origin.** UI and API are both served from `ai.builderleadconverter.com`
  (`/api/*` is reverse-proxied to the API, prefix stripped). This is why the Clerk
  `__session` cookie reaches the API with no extra CORS/Bearer plumbing.
- **`environment:` in the prod compose overrides `env_file: .env`.** The on-box `.env`
  only needs to supply *secrets*; the DB/Redis URLs, CORS origin, and storage paths are set
  by compose itself. Stale `localhost` values in `.env` are harmless.
- **The frontend container does NOT mount the root `.env`** — it only receives the two
  Clerk vars it needs, so the DB password / OpenAI key never reach the internet-facing UI.

---

## 4. The server & prerequisites

| Item | Value |
|---|---|
| Host | Linode `173.255.206.170`, Ubuntu 24.04 LTS, ~4 GB RAM, ~78 GB disk |
| SSH | user `abdullah` (sudo → root), port 22 |
| Domain | `ai.builderleadconverter.com` → A-record → the IP (confirmed) |
| Firewall | `ai-agents-linode-firewall`: inbound **22/80/443/ICMP** open, default-drop inbound, accept outbound |

Firewall and DNS already satisfy everything the stack needs (Caddy ACME needs 80 + 443
reachable; both are open). **No additional ports are required.**

**Before deploying, on the box:**
- Install Docker Engine + Compose plugin.
- Ensure **≥ 2 GB swap** (the 4 GB box can OOM during `next build` / the Playwright install).

---

## 5. Deployment runbook

> Per the project rule, **the operator runs all git/server commands.** Replace every `<…>`.

### Step 0 — Decisions (already made)
- **Clerk:** keep the **dev instance** (`pk_test…`) for now. (Production-instance migration is a
  future task — see [§9](#9-roadmap).)
- **Code transfer:** commit deploy files → PR → merge `main` → `git clone` `main` on the box.

### Step 1 — Commit the deploy work to `main` (laptop)
The prod stack + Clerk wiring is currently uncommitted. A `git clone main` on the box would
be missing all of it, so this must land on `main` first.

```bash
cd /Users/apple/Desktop/BLC/dev/blc-social-audit
git checkout -b feat/production-deploy-clerk-auth

git add .env.template .gitignore pyproject.toml poetry.lock requirements.txt \
        apps/api/auth.py apps/api/routes/audits.py apps/shared/config.py \
        Caddyfile docker-compose.prod.yml DEPLOYMENT.md \
        apps/frontend/Dockerfile apps/frontend/.dockerignore apps/frontend/middleware.ts \
        apps/frontend/next.config.js apps/frontend/package.json apps/frontend/package-lock.json \
        apps/frontend/pages/_app.tsx apps/frontend/components/Layout.tsx \
        apps/frontend/components/Welcome.tsx apps/frontend/styles/globals.css

git status                     # confirm .env is NOT staged
git commit -m "feat: production deploy stack + Clerk auth"
git push -u origin feat/production-deploy-clerk-auth
gh pr create --base main --title "Production deploy stack + Clerk auth" \
  --body "Prod Docker stack (Caddy auto-TLS) + Clerk auth on the UI and API."
```
Let pre-commit (ruff/pytest/typecheck) run. Merge the PR after review.

### Step 2 — Prepare the box (one-time)
```bash
ssh abdullah@173.255.206.170

passwd                                            # rotate the shared password

curl -fsSL https://get.docker.com | sudo sh       # Docker + compose plugin
sudo usermod -aG docker abdullah
exit && ssh abdullah@173.255.206.170              # re-login for the docker group
docker --version && docker compose version

free -h                                           # ensure swap >= 2G:
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Step 3 — Clone `main` on the box (read-only deploy key)
```bash
ssh-keygen -t ed25519 -f ~/.ssh/blc_deploy -N "" -C "blc-linode-deploy"
cat ~/.ssh/blc_deploy.pub      # → GitHub repo → Settings → Deploy keys → Add (read-only)

cat >> ~/.ssh/config <<'EOF'
Host github-blc
  HostName github.com
  User git
  IdentityFile ~/.ssh/blc_deploy
EOF

git clone github-blc:blcdevelopment/blc-social-audit.git ~/blc-social-audit
cd ~/blc-social-audit
```

### Step 4 — Create the production `.env` on the box
```bash
cd ~/blc-social-audit
nano .env        # then: chmod 600 .env
```
```bash
# --- Postgres (compose builds DATABASE_URL from these) ---
POSTGRES_DB=blc_website_audit
POSTGRES_USER=blc
POSTGRES_PASSWORD=<openssl rand -base64 24>

# --- Clerk (DEV instance). Publishable key is read at BUILD time. ---
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx
CLERK_ISSUER=https://immortal-quail-38.clerk.accounts.dev   # exact Frontend API URL, NO trailing slash
CLERK_AUTHORIZED_PARTIES=https://ai.builderleadconverter.com

# --- Optional (safe to leave blank; app degrades gracefully) ---
OPENAI_API_KEY=          # Phase-1 commentary is fully deterministic; this is dormant scaffolding
GOOGLE_PSI_API_KEY=
APIFY_API_TOKEN=         # REQUIRED for social audits (Apify IG + FB-pages actors); blank ⇒ social collection is skipped
# APIFY_TIMEOUT_SECONDS=120  # per-actor sync-run timeout (default 120, min 10)
SENTRY_DSN=              # optional error reporting; blank ⇒ disabled (mirrors the Clerk opt-in)
SENTRY_TRACES_SAMPLE_RATE=0.0

# These have sensible defaults and can be omitted entirely:
# STORAGE_RETENTION_DAYS=90        # cleanup_storage.py prunes artifacts older than this; 0 disables
# SHARE_LINK_TTL_DAYS=7            # defaults-only (NOT in .env.template); lifetime of a share link
# CRAWLER_INTERCEPT_REQUESTS=true  # aborts sub-resource/redirect fetches to private/metadata IPs
```
> `CLERK_ISSUER` is mandatory: empty → compose **aborts** (intended fail-fast); a wrong
> slug/scheme → **every** audit request returns 401. Verify the slug matches your
> `pk_test_` key's instance.
>
> Other integrations are optional and off by default — the external-SEO sweep runs built-in
> (no key), while Google Search Console (`GOOGLE_OAUTH_*` / `GSC_*`) and the licensed
> Screaming Frog CLI (`SCREAMING_FROG_*`) stay disabled unless configured. See
> [.env.template](.env.template) for the full list; leaving them blank is a supported path.
>
> **`APIFY_API_TOKEN`** powers the **runnable Social audit** via two Apify actors — Instagram
> Scraper (`apify~instagram-scraper`) and Facebook Pages Scraper (`apify~facebook-pages-scraper`).
> It is **required for social audits**; without it social collection is skipped (the job degrades
> gracefully) and **website audits are entirely unaffected** (they never call Apify). Tune the
> per-actor sync-run timeout with `APIFY_TIMEOUT_SECONDS` (default `120`). **`SENTRY_DSN`** is a
> no-op unless set *and* `sentry-sdk` is installed (it ships in the prod images via
> `pyproject.toml`).
> **`STORAGE_RETENTION_DAYS`** (default `90`, `0` disables), **`SHARE_LINK_TTL_DAYS`**
> (default `7`; defaults-only — not listed in `.env.template`), and
> **`CRAWLER_INTERCEPT_REQUESTS`** (default `true`) all default sensibly and rarely need setting.

### Step 5 — Build & launch
```bash
docker compose -f docker-compose.prod.yml config       # validate interpolation first

# Build one service at a time (frontend's next build is the OOM risk on 4 GB):
docker compose -f docker-compose.prod.yml build postgres redis caddy
docker compose -f docker-compose.prod.yml build api worker
docker compose -f docker-compose.prod.yml build frontend

docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```
> **Dependency note:** the prod images install from **`pyproject.toml`** (via `uv`), so the
> newly-added `sentry-sdk` is already picked up at build time. `poetry.lock` has **not** yet been
> regenerated — run `poetry lock` (laptop) and commit it before the next build so the lock and
> `requirements.txt` mirror match `pyproject.toml`. This is a dev-sync chore, not a deploy blocker.
On first boot the API runs `alembic upgrade head` (current head **`20260623_0004`** — chain
`0001 → 0002 → 0003 → 0004`; `0004` adds the `audit_type` discriminator + `social_handles` to
`audit_jobs`, `social_score` + `social_facts` to `audit_results`, and makes the website
`seo_score` / `uxui_score` / `lead_gen_score` columns nullable so a social result can leave them
empty — all **additive and safe** to apply over an existing DB; `0003` added `share_token` /
`share_expires_at` / `brand_overrides`), and Caddy requests the TLS cert automatically
(allow ~30 s).

### Step 6 — Clerk dashboard
- **Restrictions → invitation-only.** Disable open sign-up and invite your 2–3 teammates
  by email. (Without this, anyone who finds the URL can self-register — see [§7](#7-security).)

### Step 7 — Verify (smoke test)
```bash
curl -I https://ai.builderleadconverter.com             # 200 (Welcome page)
curl -i https://ai.builderleadconverter.com/api/audits  # 401 (auth enforced, no token)
docker compose -f docker-compose.prod.yml logs -f caddy api worker
```
Then in a browser: open the domain → sign in → submit a URL → watch progress → download the
PDF. **This is the real test** (only the 401 path has been verified so far).

---

## 5.1 Continuous deployment (CI/CD)

> **Automates the manual deploy in [§6](#6-day-2-operations).** Once set up, **merging a PR to
> `main` deploys it to the box automatically** — no SSH, no manual `git pull`. It builds on the
> box exactly as before; CI only changes *what triggers* the deploy, not *how* it is built.

### The flow

```
 feature branch ──PR──▶  CI: pre-commit.yml (ruff · pytest · typecheck)
                              │  must be green  ─── enforced by branch protection
                              ▼
                         merge to main  ─── protect-main.yml blocks direct pushes
                              │  (push: main)
                              ▼
                      deploy.yml ──SSH──▶ Linode box
                                            └─ deploy/deploy.sh:
                                               git reset --hard <merged sha>
                                               docker compose build api·worker·frontend
                                               docker compose up -d
                                               health-check /health  (fails loud if unhealthy)
```

Three pieces — two already existed, the third is new:
- **CI gate** — [pre-commit.yml](.github/workflows/pre-commit.yml) runs ruff, pytest and the
  frontend typecheck on every PR (the job is named **`Run pre-commit hooks`**).
- **Branch protection** — the *enforcement* that a PR may only merge once that check is green
  (a GitHub setting, configured once — see step C below; [protect-main.yml](.github/workflows/protect-main.yml)
  is the after-the-fact backstop).
- **CD** *(new)* — [deploy.yml](.github/workflows/deploy.yml) fires on `push: main` (i.e. the
  merge commit) and runs [deploy/deploy.sh](deploy/deploy.sh) on the box over SSH. The script is
  the exact, pinned-to-commit form of the manual day-2 command, plus a post-deploy `/health`
  gate that fails the run loudly if the new containers come up unhealthy.

Because CI gates the PR, any commit that reaches `main` has already passed the checks; `deploy.yml`
does not re-run the tests, it only deploys.

### One-time setup (operator)

> Per the project rule, **you run all of these.** They are infrastructure/secret/GitHub-settings
> actions; the workflow files themselves are already in the repo.

**A. Create a dedicated CI deploy SSH key** (separate from the box's read-only *git* deploy key —
this one lets GitHub Actions log in and run the deploy). Generate it on a trusted machine:
```bash
ssh-keygen -t ed25519 -f ~/.ssh/blc_ci_deploy -N "" -C "github-actions-deploy"
ssh-copy-id -i ~/.ssh/blc_ci_deploy.pub abdullah@173.255.206.170   # add .pub to the box's authorized_keys
```

**B. Capture the box's host key** (so CI verifies it's really your box, not a MITM):
```bash
ssh-keyscan -t ed25519 173.255.206.170      # copy the whole output line
```

**C. Add the repository secrets** — GitHub → repo → **Settings → Secrets and variables → Actions
→ New repository secret**:

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | `173.255.206.170` |
| `DEPLOY_USER` | `abdullah` |
| `DEPLOY_SSH_KEY` | full contents of `~/.ssh/blc_ci_deploy` (the **private** key, incl. the `-----BEGIN…END-----` lines) |
| `DEPLOY_KNOWN_HOSTS` | the `ssh-keyscan` output line from step B |
| `DEPLOY_PORT` | *(optional)* SSH port; omit to default to `22` |

**D. Turn on branch protection** so "checks must pass before merge" is *enforced* (not just
advisory) — GitHub → repo → **Settings → Branches → Add branch ruleset / rule** for `main`:
- ✅ **Require a pull request before merging** (this is what stops direct commits to `main`).
- ✅ **Require status checks to pass before merging** → search and add **`Run pre-commit hooks`**.
- ✅ *(recommended)* **Require branches to be up to date before merging**.
- ✅ *(recommended)* **Do not allow bypassing the above settings** / include administrators.

Then, separately, in **Settings → General → Pull Requests**, **disable "Allow squash merging" and
"Allow rebase merging"** (leave only **"Allow merge commits"**). The
[protect-main.yml](.github/workflows/protect-main.yml) backstop recognises a legitimate merge by its
**two parent commits**; a squash/rebase merge lands a *single-parent* commit and would trip that
workflow red on a valid PR. (It doesn't block the deploy — `deploy.yml` is independent — but it's a
misleading red ❌ in the Actions tab.) Pinning the merge method keeps the whole scheme consistent.

> Do **not** add the deploy workflow as a required status check — it runs *after* merge (on
> `push: main`), so it never reports a status on the PR and would deadlock the merge.

Once A–D are done, the next merge to `main` deploys itself.

### Triggering, watching, rolling back

```bash
# Watch a deploy run live:           GitHub → repo → Actions → "Deploy to production"
# Re-deploy current main by hand:    Actions → "Deploy to production" → Run workflow
# Deploy by hand ON the box (fallback if CI/secrets are down):
cd ~/blc-social-audit && bash deploy/deploy.sh
# Roll back to a known-good commit:
cd ~/blc-social-audit && bash deploy/deploy.sh <previous-good-sha>
```
A failed build leaves the previous (healthy) containers running — `up -d` is only reached if all
three images build. A failed post-deploy `/health` check turns the Action **red** so you know the
new containers are up but unhealthy; investigate with `docker compose logs api`, then roll back
with the command above.

### Security notes for the CI deploy path
- The CI key logs in as `abdullah` (a sudo user). For tighter blast-radius later, restrict it with
  a `command="…"`/`no-pty` forced-command in `authorized_keys`, or add a dedicated unprivileged
  `deploy` user in the `docker` group. Fine as-is for 2–3 internal users.
- Host-key pinning (`DEPLOY_KNOWN_HOSTS` + `StrictHostKeyChecking=yes`) is on, so a spoofed host
  fails the connect rather than silently trusting it.
- The private key lives only in GitHub Actions secrets (write-only once saved) and is written to
  the ephemeral runner with `chmod 600`; it is never echoed.

---

## 6. Day-2 operations

```bash
cd ~/blc-social-audit

# Deploy an update: normally AUTOMATIC on merge to main (see §5.1). To deploy by hand:
bash deploy/deploy.sh            # or, the original raw command:
git pull && docker compose -f docker-compose.prod.yml up -d --build

# Logs / status / restart:
docker compose -f docker-compose.prod.yml logs -f <service>
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml restart <service>

# Stop (keep data) / stop and WIPE the DB:
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml down -v        # destroys postgres_data + storage!

# Database backup (do this on a schedule):
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U blc blc_website_audit > ~/backups/blc_$(date +%F).sql

# Reclaim disk (build cache grows fast):
docker builder prune -f

# Prune old reports/screenshots/tool-exports (see Storage note below):
docker compose -f docker-compose.prod.yml exec api python scripts/cleanup_storage.py --dry-run
docker compose -f docker-compose.prod.yml exec api python scripts/cleanup_storage.py
```

**Storage:** reports stay on the **local filesystem** in the shared `storage` volume — object
storage (S3) was evaluated and **removed by decision** (single internal VM, ~5–10 users).
`scripts/cleanup_storage.py` deletes reports / screenshots / tool-exports older than
`STORAGE_RETENTION_DAYS` (default 90; `0` disables). There is **no in-app scheduler** — run it
from cron on the host. Add a daily job (runs inside the `api` container, which mounts the
`storage` volume):

```bash
# crontab -e  (on the box)
0 3 * * *  cd ~/blc-social-audit && docker compose -f docker-compose.prod.yml exec -T api \
             python scripts/cleanup_storage.py >> ~/blc-cleanup.log 2>&1
```
Still watch `df -h` — the build cache and Postgres data grow independently of report retention.

**Observability (P2-10):** error reporting is Sentry (`SENTRY_DSN`). Two more cron jobs round it out
(all run inside a container that has the DB URL / storage volume):

```bash
# Operational alerting — every 15 min; posts to ALERT_WEBHOOK_URL on failed-audit / stuck-job thresholds
*/15 * * * *  cd ~/blc-social-audit && docker compose -f docker-compose.prod.yml exec -T api \
                python scripts/health_alert.py >> ~/blc-alert.log 2>&1
# PostgreSQL backup — nightly; pg_dump -> timestamped .sql.gz under BACKUP_STORAGE_DIR, pruned to BACKUP_RETENTION_DAYS
30 2 * * *   cd ~/blc-social-audit && docker compose -f docker-compose.prod.yml exec -T api \
                python scripts/backup_db.py >> ~/blc-backup.log 2>&1
```
Live metrics: `GET /metrics` (Clerk-gated) returns audit/storage stats as JSON. Note the API/worker
images need PostgreSQL client tools (`pg_dump`) for `backup_db.py`; if absent, run it on the host or
add `postgresql-client` to the image.

---

## 7. Security

| Item | Status / Action |
|---|---|
| **Open sign-up** | ⚠️ Gating is client-side (`<SignedIn>/<SignedOut>`); the dev Clerk instance allows self-registration, and the API trusts any validly-signed token from the instance (no email allowlist). **Must set Clerk Restrictions → invitation-only.** |
| **Secret rotation** | ⚠️ SSH password + Clerk secret key were shared in chat → rotate both. |
| **SSH hardening** | Move to SSH keys, then disable password auth (`PasswordAuthentication no`). |
| **`CLERK_AUTHORIZED_PARTIES`** | Set to the domain so the `azp` check is active (else it's a no-op). |
| **API auth boundary** | ✅ Every `/audits` endpoint requires a valid Clerk token (`require_user`). |
| **Public share links** | ℹ️ **By design.** `GET /shared/{token}` and `GET /shared/{token}/report` are **unauthenticated** (mounted outside the `require_user` router) so clients can view/download a report without an account; they are reachable through Caddy's `/api/*` route (i.e. `/api/shared/{token}`). Access needs a 32-byte URL-safe token that is **time-limited** (`SHARE_LINK_TTL_DAYS`, default 7) and **operator-revocable** (`DELETE /audits/{id}/share` nulls the token). Expired → 410, missing/revoked → 404. |
| **Secrets in images** | ✅ `.dockerignore` keeps `.env` out of all images; frontend never sees the DB/OpenAI secrets. |
| **TLS** | ✅ Caddy auto-issues + auto-renews Let's Encrypt; `caddy_data` volume persists certs. |
| **SSRF** | Crawler blocks private/loopback/metadata IPs pre-navigation and re-validates the post-redirect host; the external-SEO site-health sweep re-validates **every** redirect hop. The page crawler's mid-crawl sub-resource interception is still **not** done (known limitation — see docs/06). |

---

## 8. Known limitations (operational)

- **Single worker, `--concurrency=1`** — correctly tuned for 4 GB; audits run one at a time.
- **Storage retention is cron-driven, not automatic** — `scripts/cleanup_storage.py` exists and
  closes the old "no cleanup" gap, but there is **no in-app scheduler**; you must wire the host
  cron job (see [§6](#6-day-2-operations)) or artifacts still accumulate.
- **Observability is opt-in and minimal** — optional Sentry error reporting via `SENTRY_DSN`
  (no-op when unset); **no metrics/alerts/dashboards and no Celery retry-DLQ** beyond Celery
  time limits (still TODO).
- **Dev Clerk instance** — rate-limited, ~100-user cap, shows a dev banner; fine for internal
  use, not ideal for production (see roadmap).
- **`depends_on` is start-order, not readiness** — expect a brief 502 warm-up on the very first
  request after `up -d` while the API migrates; self-heals.
- **First signed-in round-trip untested** until the post-deploy smoke test.

---

## 9. Roadmap

### Near-term hardening (do soon after go-live)
1. **Restrict Clerk sign-up** + invite the team (security — do at deploy).
2. **Rotate secrets** + move SSH to keys, disable password login.
3. **Automated Postgres backups** (cron `pg_dump` → off-box). The **storage retention job** now
   exists (`scripts/cleanup_storage.py`) — just wire it into host cron (see [§6](#6-day-2-operations)).
4. **Disk + uptime monitoring** (the 4 GB box has no headroom to spare).
5. **Smoke-test checklist** added to CI or a runbook for every deploy.

### Productionizing (when usage grows beyond a few users)
6. **Clerk Production instance** on the custom domain (`pk_live`, ~5 Clerk CNAME DNS records);
   removes the dev banner + rate limits and closes the open-sign-up exposure properly.
7. **Server-side user allowlist** in the API (defense in depth beyond Clerk restrictions).
8. ✅ **CI/CD auto-deploy** *(done — see [§5.1](#51-continuous-deployment-cicd))* — [deploy.yml](.github/workflows/deploy.yml)
   SSHes in and runs [deploy/deploy.sh](deploy/deploy.sh) (`up -d --build`) on merge to `main`.
   Still builds *on the box*; building off-box is item 9 below.
9. **Build images off-box** (registry) so the 4 GB box never runs `next build`.
10. **Observability** — optional **Sentry** error reporting is now wired (set `SENTRY_DSN`); still
    TODO: structured log aggregation, a Celery retry/DLQ, and metrics/alerts.
11. ~~**Object storage** for reports (S3-compatible).~~ **Removed by decision** — for a single
    internal VM (~5–10 users) reports stay on the **local filesystem**; the cron retention job
    (item 3) handles disk pressure instead.

### Phase 2 (product)
12. ✅ **Social-media auditing** *(done — 2026-06-23)* — the second audit type, designed
    **standalone** (its own `audit_type`, its own report, its own Social Score — *not* folded into
    the website composite, which is untouched and still `{seo, uxui}`). **Now fully built and
    runnable from the browser:** the Apify-backed `social` fact extractor + collector under
    [apps/worker/stages/social/](apps/worker/stages/social/) (two actors — Instagram Scraper +
    Facebook Pages Scraper), `rubrics/social.yaml` (`phase2-social-v1`) scored by
    `scoring.score_social_audit()` into a standalone 0–100 Social Score, deterministic
    rule-derived findings (no LLM), a separate branded PDF (`templates/social_report.html` via
    `render_social_pdf`, PDF only — no DOCX), the `audit_type` discriminator + migration
    `20260623_0004`, a social branch in `run_collection_audit` (`_run_social_pipeline`), and a
    Social Audit tab + submit/detail UI. Ops dependency: `APIFY_API_TOKEN`. **FB limitation:** the
    Facebook pages actor returns page metadata, not posts, so cadence/recency/engagement rules
    *skip* for FB (rescaled, never penalized); IG has full post data. See
    [docs/08_PHASE2_PLAN.md](docs/08_PHASE2_PLAN.md).
13. **Multi-tenant / roles, benchmarking, analytics** — planning docs only (docs/08–10).

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `docker compose up` aborts: "set CLERK_ISSUER…" | `CLERK_ISSUER` empty/unset in `.env` | Set it to the exact dev-instance Frontend API URL (no trailing slash). |
| Every audit request → **401** after sign-in | `CLERK_ISSUER` slug/scheme mismatch | Make it match the `pk_test_` instance exactly; `auth.py` verifies token `iss == issuer`. |
| `next build` killed / image build fails | OOM on 4 GB | Add ≥2 GB swap; build services one at a time; or build off-box. |
| Site not reachable / no HTTPS | Cert not issued | Check `docker compose logs caddy`; ensure DNS→IP, ports 80/443 free + open; avoid repeated up/down (Let's Encrypt rate limits). |
| 502 right after `up -d` | API still running migrations | Wait ~30 s; self-heals. Re-check `logs api`. |
| PDF download 404 | Worker hasn't finished / volume mismatch | Confirm api + worker both mount the `storage` volume; check worker logs for the render stage. |
| Frontend can't reach API | `NEXT_PUBLIC_API_BASE_URL` wrong (baked at build) | It's a build arg = `https://ai.builderleadconverter.com/api`; rebuild the frontend image if changed. |

---

*Maintained alongside the code. Update this file whenever the deploy topology, secrets, or
the runbook change.*
