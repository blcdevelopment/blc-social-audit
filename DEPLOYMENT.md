# Deployment Guide — BLC Website Audit

> **Status (2026-06-10): ✅ Build-verified, ready to deploy.**
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
Insights → extract SEO + UX/UI facts → score deterministically → generate grounded AI
commentary → render a branded PDF → expose it through a Next.js operator UI.

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

**Out of scope (Phase 2, not built):** social-media auditing, object storage, multi-tenant
auth/roles, benchmarking/analytics. See [§9 Roadmap](#9-roadmap).

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
OPENAI_API_KEY=
GOOGLE_PSI_API_KEY=
```
> `CLERK_ISSUER` is mandatory: empty → compose **aborts** (intended fail-fast); a wrong
> slug/scheme → **every** audit request returns 401. Verify the slug matches your
> `pk_test_` key's instance.

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
On first boot the API runs `alembic upgrade head`, and Caddy requests the TLS cert
automatically (allow ~30 s).

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

## 6. Day-2 operations

```bash
cd ~/blc-social-audit

# Deploy an update (after the PR is merged to main):
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
```

**Storage:** PDFs/screenshots accumulate unbounded in the `storage` volume (no retention
policy — known limitation). Watch `df -h` and prune `~/blc-social-audit` storage paths or the
volume contents periodically.

---

## 7. Security

| Item | Status / Action |
|---|---|
| **Open sign-up** | ⚠️ Gating is client-side (`<SignedIn>/<SignedOut>`); the dev Clerk instance allows self-registration, and the API trusts any validly-signed token from the instance (no email allowlist). **Must set Clerk Restrictions → invitation-only.** |
| **Secret rotation** | ⚠️ SSH password + Clerk secret key were shared in chat → rotate both. |
| **SSH hardening** | Move to SSH keys, then disable password auth (`PasswordAuthentication no`). |
| **`CLERK_AUTHORIZED_PARTIES`** | Set to the domain so the `azp` check is active (else it's a no-op). |
| **API auth boundary** | ✅ Every `/audits` endpoint requires a valid Clerk token (`require_user`). |
| **Secrets in images** | ✅ `.dockerignore` keeps `.env` out of all images; frontend never sees the DB/OpenAI secrets. |
| **TLS** | ✅ Caddy auto-issues + auto-renews Let's Encrypt; `caddy_data` volume persists certs. |
| **SSRF** | Crawler blocks private/loopback/metadata IPs pre-navigation; mid-crawl sub-resource interception is **not** done (known limitation — see docs/06). |

---

## 8. Known limitations (operational)

- **Single worker, `--concurrency=1`** — correctly tuned for 4 GB; audits run one at a time.
- **No retention/cleanup** for `storage/` PDFs + screenshots.
- **No observability / no retry-DLQ** beyond Celery time limits.
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
3. **Automated Postgres backups** (cron `pg_dump` → off-box) + a **storage retention job**
   (delete reports/screenshots older than N days).
4. **Disk + uptime monitoring** (the 4 GB box has no headroom to spare).
5. **Smoke-test checklist** added to CI or a runbook for every deploy.

### Productionizing (when usage grows beyond a few users)
6. **Clerk Production instance** on the custom domain (`pk_live`, ~5 Clerk CNAME DNS records);
   removes the dev banner + rate limits and closes the open-sign-up exposure properly.
7. **Server-side user allowlist** in the API (defense in depth beyond Clerk restrictions).
8. **CI/CD auto-deploy** — a GitHub Action that builds images and `docker compose up -d` on the
   box on merge to `main` (replaces the manual `git pull && build`).
9. **Build images off-box** (registry) so the 4 GB box never runs `next build`.
10. **Observability** — structured logs aggregation, a Celery retry/DLQ, health/metrics endpoints.
11. **Object storage** for reports (S3-compatible) — removes the local-filesystem limitation and
    enables horizontal scaling of the worker.

### Phase 2 (product)
12. **Social-media auditing** — the second audit type. The pipeline already has the seam: add a
    `social` fact bundle + `social.yaml` rubric and extend the typed composite category set
    (`Literal["seo","uxui"]` → add `"social"`). See [docs/08_PHASE2_PLAN.md](docs/08_PHASE2_PLAN.md).
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
