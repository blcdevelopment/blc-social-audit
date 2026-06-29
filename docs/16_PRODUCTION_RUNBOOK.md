# 16 — Production Operations Runbook

**Live:** https://ai.builderleadconverter.com · **Last updated: 2026-06-26**

This is the **practical operations runbook** for the deployed app: how it runs in production, how
CI/CD deploys it, **how to access the server, and how to add/tweak environment variables (API
keys) in production** — including exactly what the combined‑audit release needs.

> **Relationship to other docs.** [`DEPLOYMENT.md`](../DEPLOYMENT.md) (repo root) is the
> **authoritative, deep** deploy reference (firewall, CI/CD internals, day‑2 ops). This file is the
> **task‑oriented runbook** focused on env management and the current release. When they disagree,
> trust `DEPLOYMENT.md` for mechanics and the **actual code** (`docker-compose.prod.yml`,
> `deploy/deploy.sh`, `apps/shared/config.py`) for truth.

---

## 0. TL;DR — the questions you asked

- **Does merging the combined‑audit branch need new API keys?**
  The *code* needs **no new key** — but for a **combined/social audit to actually produce a social
  section**, the production `.env` must contain **`APIFY_API_TOKEN`** (Instagram + Facebook) and,
  for the YouTube backend, **`YOUTUBE_API_KEY`**. Without them the social step **degrades
  gracefully** to a website‑only report (no crash). See §5–§6.
- **Does CI/CD handle it automatically?**
  Code: **yes** — merge to `main` auto‑deploys (git reset + rebuild + restart). **Env: no** — the
  `.env` lives only on the server and is **never** touched by a deploy. Adding keys is a **manual
  one‑time `.env` edit + container recreate** (§6). You do **not** redeploy code to add a key.
- **One file that must ship in the merge:** `rubrics/overall.yaml` (the Overall Lead‑Gen Readiness
  weights). It is additive and has no secret, but if it is missing from `main`, combined audits
  degrade to website‑only. Confirm it is `git add`‑ed before merging. See §7.
- **Adding a backend key = no rebuild.** `api`/`worker` read `.env` via `env_file:`, so you edit
  `.env` and recreate those two containers. Only **frontend `NEXT_PUBLIC_*`** vars need a rebuild
  (they are baked at build time). See §6.4.

---

## 1. What is running in production

| Piece | Value |
|---|---|
| Host | Linode VM, Ubuntu 24.04 LTS, ~4 GB RAM + **2 GB swap** (added for image builds) |
| Public IP | `173.255.206.170` |
| Domain | `ai.builderleadconverter.com` (DNS A‑record → the IP) |
| TLS | Caddy auto‑issues + renews Let's Encrypt certs |
| Firewall (`ai-agents-linode-firewall`) | **Inbound:** SSH 22, HTTP 80, HTTPS 443, ICMP — everything else **Drop**. **Outbound:** Accept all. |
| Orchestration | Docker Compose, file **`docker-compose.prod.yml`** |
| Repo on server | `~/blc-social-audit` for the SSH user (i.e. `/home/abdullah/blc-social-audit`) |
| Prod `.env` | `~/blc-social-audit/.env` (gitignored, on the box only) |

### The Docker Compose stack (`docker-compose.prod.yml`)
Six services on one internal Docker network; **only Caddy publishes ports (80/443)**:

| Service | Image / build | Role | Notes |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` | database | named volume `postgres_data`; `restart: unless-stopped` |
| `redis` | `redis:7-alpine` | Celery broker + result backend | internal only |
| `api` | builds `apps/api/Dockerfile` | FastAPI/uvicorn :8000 | runs `alembic upgrade head` on boot; `env_file: .env` |
| `worker` | builds `apps/worker/Dockerfile` | Celery + Playwright/Chromium | `--concurrency=1` (one browser at a time on 4 GB); `env_file: .env` |
| `frontend` | builds `apps/frontend/Dockerfile` | Next.js :3000 | **no `env_file`** — only the two Clerk vars + `NEXT_PUBLIC_*` build args |
| `caddy` | `caddy:2-alpine` | reverse proxy + TLS | publishes 80/443; routes `/api/*` → `api:8000`, everything else → `frontend:3000` |

**Single‑origin design:** the UI and API share one domain, so the Clerk `__session` cookie reaches
`/api/*` with no extra CORS plumbing. Do not "simplify" this.

---

## 2. How environment variables reach each container (important)

This determines whether a change needs a **rebuild** or just a **restart**.

- **`api` and `worker`** load **all of `.env`** via `env_file: .env`, **plus** a few hardcoded
  `environment:` overrides in compose (DB URL, Redis, `API_CORS_ORIGINS`, storage dirs,
  `CLERK_ISSUER`). So **any optional key you put in `.env` (Apify, YouTube, OpenAI, PSI, GSC,
  Sentry, `CLERK_ALLOWED_SUBJECTS`, …) is picked up by the api/worker at container start** — no
  rebuild, just recreate the container.
- **Compose `${VAR}` interpolation** (e.g. `POSTGRES_PASSWORD`, `CLERK_ISSUER`, the Clerk keys) is
  read from `.env` in the project directory at `up`/`build` time. Four have a fail‑fast `:?` guard
  — **compose aborts** if they are empty: `POSTGRES_PASSWORD`, `CLERK_ISSUER`,
  `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`.
- **`frontend`** has **no `env_file`** by design (the internet‑facing UI must never see the DB
  password / OpenAI key). It receives only `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` + `CLERK_SECRET_KEY`,
  and its `NEXT_PUBLIC_*` values are **build args baked into the image at build time**. Changing any
  `NEXT_PUBLIC_*` therefore requires a **rebuild** of the frontend.

---

## 3. How CI/CD deploys (and what it does NOT do)

On **merge/push to `main`**, GitHub Actions ([`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml))
SSHes the box and streams [`deploy/deploy.sh`](../deploy/deploy.sh), which on the server:

1. `git fetch --prune` then **`git reset --hard <SHA>`** to the merged commit (the gitignored
   **`.env` survives** the reset).
2. Builds the three images **sequentially** (`api`, then `worker`, then `frontend`) — sequential to
   avoid OOM on the 4 GB box during `next build`.
3. `docker compose -f docker-compose.prod.yml up -d` (only changed services are recreated).
4. `docker image prune -f`.
5. **Health gate:** polls `GET /health` from inside the `api` container (~150 s budget). On failure
   it dumps api logs and exits non‑zero, **leaving the previous healthy containers serving**.

Migrations run automatically via the `api` container's start command (`alembic upgrade head && …`).

**What CI/CD does NOT do:** it never edits `.env`, never adds API keys, never changes server
settings. Those are manual (§6). A deploy with the same `.env` keeps using whatever keys are
already there.

---

## 4. Accessing the server

```bash
ssh abdullah@173.255.206.170        # port 22; password is in your password manager (NOT in this file)
```

> 🔴 **Rotate the shared credentials.** The SSH password, the root password, and the Clerk secret
> key were shared over chat during setup. Change the Linux password (`passwd`), and rotate the
> Clerk secret key in the Clerk dashboard + the prod `.env`. Ideally switch SSH to **key‑only**
> auth and disable password login. This is the single biggest exposure right now.

Where things live on the box:

```bash
cd ~/blc-social-audit                       # the cloned repo (deploy.sh resets this to main)
nano .env                                   # the production environment file (gitignored)
docker compose -f docker-compose.prod.yml ps        # service status
docker compose -f docker-compose.prod.yml logs -f api worker   # live logs
```

All `docker compose` commands in this doc assume you are in `~/blc-social-audit` and pass
`-f docker-compose.prod.yml`.

---

## 5. The production `.env` — what must be set

The `.env` only needs **secrets and optional keys**; the DB/Redis/CORS/storage/`CLERK_ISSUER`
values are injected by compose. Use [`.env.template`](../.env.template) as the field reference.

### Required (compose fails fast if missing)
| Var | Purpose |
|---|---|
| `POSTGRES_PASSWORD` | DB password (also interpolated into `DATABASE_URL`) |
| `CLERK_ISSUER` | Clerk Frontend API URL, no trailing slash. **Empty = API auth disabled** — never in prod |
| `CLERK_SECRET_KEY` | Clerk server key (`sk_…`) |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk browser key (`pk_…`) — **build arg**, baked into the frontend image |

### Optional but recommended
| Var | Enables | Needed for combined/social? |
|---|---|---|
| **`APIFY_API_TOKEN`** | Instagram + Facebook social scraping (Apify) | **Yes — for the social section of a combined/social audit** |
| **`YOUTUBE_API_KEY`** | YouTube channel stats (YouTube Data API v3, free, no OAuth) | Yes, for the YouTube backend |
| `GOOGLE_PSI_API_KEY` | real PageSpeed/Core Web Vitals data (else PSI gracefully skips) | No (website perf) |
| `OPENAI_API_KEY` | **only** the optional social‑commentary LLM polish (GPT‑4o). Website + combined social findings are deterministic without it | No |
| `CLERK_AUTHORIZED_PARTIES` | restrict accepted `azp` origins | No |
| **`CLERK_ALLOWED_SUBJECTS`** | **NEW** — allowlist of Clerk user ids permitted to use the API (defense‑in‑depth; empty = any valid token). Comma‑separated `user_…` ids | No, but recommended |
| `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET` / `_REDIRECT_URI` / `GOOGLE_OAUTH_STATE_SECRET` | Search Console enrichment | No |
| `SENTRY_DSN` | error reporting | No |
| `ALERT_WEBHOOK_URL`, `BACKUP_*`, `PG_DUMP_PATH` | the cron jobs (alerting / DB backups) | No |

### Defaults‑only — do NOT need to set, but the FILES must exist in the repo
`RUBRIC_OVERALL_PATH` (`./rubrics/overall.yaml`), `RUBRIC_SOCIAL_PATH` (`./rubrics/social.yaml`),
`RUBRIC_SEO_PATH`, `RUBRIC_UXUI_PATH`, `RUBRIC_COMPOSITE_PATH`, report templates, `STORAGE_RETENTION_DAYS`,
`SHARE_LINK_TTL_DAYS`, `APIFY_TIMEOUT_SECONDS`, `YOUTUBE_TIMEOUT_SECONDS`. These resolve to bundled
files inside the image — you only set the env var to **relocate** a file, which you won't. **But the
files themselves must be committed to the repo** (the image is built from the `main` checkout). This
is why `rubrics/overall.yaml` must be in the merge (§7).

---

## 6. Updating the environment in production (the core workflow)

### 6.1 Add or change a **backend** key (Apify, YouTube, OpenAI, PSI, GSC, Sentry, allowlist…)
This is the common case — e.g. enabling social/combined audits.

```bash
ssh abdullah@173.255.206.170
cd ~/blc-social-audit
cp .env .env.bak.$(date +%F)                 # quick backup first
nano .env                                    # add/edit the line(s), e.g.:
#   APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxx
#   YOUTUBE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
#   CLERK_ALLOWED_SUBJECTS=user_2abc...,user_3def...

# Recreate ONLY the services that read .env (api + worker). No rebuild needed.
docker compose -f docker-compose.prod.yml up -d --force-recreate api worker

# Confirm the key landed inside the container (value is masked in your shell history if you grep carefully):
docker compose -f docker-compose.prod.yml exec worker printenv | grep -E 'APIFY|YOUTUBE|CLERK_ALLOWED' | sed 's/=.*/=<set>/'
```

- **No image rebuild, no code redeploy.** `env_file: .env` is re‑read when the container is
  recreated. `--force-recreate` guarantees the new env is applied.
- The `worker` is the one that does social collection, so it must be recreated for Apify/YouTube
  keys; recreate `api` too for auth/PSI/GSC/`CLERK_ALLOWED_SUBJECTS`.

### 6.2 Change `CLERK_ISSUER` / `POSTGRES_PASSWORD` / `CLERK_SECRET_KEY`
These are compose‑interpolated. Edit `.env`, then:
```bash
docker compose -f docker-compose.prod.yml up -d           # recreates affected services
```
⚠️ Changing `POSTGRES_PASSWORD` after the DB volume exists does **not** change the actual Postgres
role password — only the connection string. Rotating the DB password is a separate `ALTER ROLE`
operation; coordinate carefully (out of scope here).

### 6.3 Change a **frontend** public var (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `NEXT_PUBLIC_*`)
These are **baked at build time** → you must **rebuild** the frontend:
```bash
nano .env
docker compose -f docker-compose.prod.yml up -d --build frontend
```

### 6.4 Rebuild‑vs‑restart cheat sheet
| Change | Command | Rebuild? |
|---|---|---|
| Backend key in `.env` (Apify, YouTube, OpenAI, PSI, GSC, Sentry, `CLERK_ALLOWED_SUBJECTS`) | `up -d --force-recreate api worker` | **No** |
| `CLERK_ISSUER` / `CLERK_SECRET_KEY` / `POSTGRES_PASSWORD` | `up -d` | No |
| `NEXT_PUBLIC_*` (frontend) | `up -d --build frontend` | **Yes (frontend)** |
| Application code | merge to `main` (CI/CD) **or** `bash deploy/deploy.sh` on the box | Yes (automatic) |

---

## 7. Post‑merge checklist — the combined‑audit release

Do these around merging the combined‑audit branch to `main`.

**Before / at merge (in the repo):**
1. ✅ **Commit `rubrics/overall.yaml`** (Overall Lead‑Gen Readiness weights). It is untracked until
   you `git add` it. If it is missing from `main`, the image won't contain it and combined audits
   silently degrade to website‑only.
2. ✅ The new/changed files all go in the same commit (combined‑audit code, deleted
   `apps/frontend/pages/social.tsx`, the doc updates, `.env.template`).
3. ⚠️ The Dockerfiles now install pinned deps from `requirements.txt` then `--no-deps -e .`. Ideally
   `docker compose -f docker-compose.prod.yml build` **once locally** to confirm the build before
   merging (a broken build would fail the auto‑deploy). The server will rebuild on deploy anyway.

**After the deploy lands (on the server, one‑time `.env` edits):**
4. **Enable social/combined audits:** add `APIFY_API_TOKEN` and (optional) `YOUTUBE_API_KEY` to
   `.env`, then `up -d --force-recreate api worker` (§6.1). Until then, a combined audit still works
   but renders **website‑only** (social section skipped).
5. *(Optional, recommended)* lock the API to your operators: set `CLERK_ALLOWED_SUBJECTS` to the
   Clerk user ids of your team, and keep the Clerk instance **invitation‑only** in the Clerk
   dashboard.
6. **No DB migration is required** — `audit_type="combined"` is a free string column and the Overall
   Readiness lives in existing JSON. Alembic head stays `20260625_0005`. The `api` container still
   runs `alembic upgrade head` on boot (a no‑op here).

**Smoke test (see §8).**

---

## 8. Verifying a deploy / smoke test

```bash
# On the box: services healthy?
docker compose -f docker-compose.prod.yml ps

# Health endpoint (from inside, like the deploy gate does):
docker compose -f docker-compose.prod.yml exec -T api \
  python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)" \
  && echo HEALTHY
```

From a browser (real end‑to‑end):
1. Sign in at https://ai.builderleadconverter.com (Clerk).
2. **Website‑only:** submit a URL → confirm the report renders and the PDF downloads.
3. **Combined:** submit a URL **plus** an Instagram/Facebook/YouTube link → confirm progress shows
   *"Auditing social profiles"* (~96 %), and the final report (PDF **and** DOCX) ends with a
   **Social Media Audit** section + an **Overall Lead‑Gen Readiness** score.
   - If the social section is missing, the Apify/YouTube keys aren't set (§6.1) — the audit still
     completes website‑only (that's the graceful path, not a failure).

---

## 9. Day‑2 operations

- **Logs:** `docker compose -f docker-compose.prod.yml logs -f api worker` (worker logs the audit
  pipeline). A render/skew error like `'dict object' has no attribute 'social_audit'` means a
  **stale worker** — recreate it: `up -d --force-recreate worker` (Celery does not hot‑reload).
- **Restart a service:** `docker compose -f docker-compose.prod.yml restart worker`.
- **Disk:** `df -h` and `docker system df`. Reports/screenshots accumulate under the `storage`
  volume; prune images with `docker image prune -f` / `docker builder prune -f`.
- **Cron jobs** (host crontab, run scripts inside the `api` container — see `DEPLOYMENT.md §6`):
  storage retention (`scripts/cleanup_storage.py`), DB backup (`scripts/backup_db.py`), alerting
  (`scripts/health_alert.py`). Confirm they are installed (`crontab -l`).
- **Manual deploy / rollback:** on the box, `bash deploy/deploy.sh` (HEAD of `main`) or
  `bash deploy/deploy.sh <previous-sha>` to roll back to a known‑good commit.
- 🔴 **Never** `docker compose down -v` — the `-v` wipes `postgres_data` + `storage` (all data and
  reports). Use `down` (no `-v`) if you must stop the stack.

---

## 10. Security notes (open items)

- **Rotate the shared credentials** (SSH/root passwords, Clerk secret) — see §4. Move SSH to
  key‑only auth.
- **Clerk is a dev instance (`pk_test_…`)** with open self‑registration by default — set the Clerk
  dashboard to **invitation‑only**, and/or set `CLERK_ALLOWED_SUBJECTS` so only your operators'
  user ids are accepted by the API.
- **`.env` is the only place secrets live on the box** — keep `chmod 600 .env`, never commit it, and
  keep the timestamped `.env.bak.*` backups off any public location.
- **DB backups stay on‑box** (`scripts/backup_db.py` → `storage/backups`). Copy them off‑box
  periodically; the host is a single point of failure.
- **GSC OAuth tokens are stored unencrypted** in the DB (documented accepted risk for a single
  internal VM; the main exposure is a DB dump leaving the box — keep backups access‑controlled).

---

## 11. Quick troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| First request after deploy returns 502 for a few seconds | API still migrating / warming up | wait; the health gate covers it |
| Combined audit completes but has **no social section** | `APIFY_API_TOKEN`/`YOUTUBE_API_KEY` not in `.env` | add them, `up -d --force-recreate api worker` (§6.1) |
| Combined audit **fails** with a template error (`… no attribute 'social_audit'`) | stale worker running pre‑release code | `up -d --force-recreate worker` (and confirm the deploy rebuilt the image) |
| Every audit returns **401** | wrong/empty `CLERK_ISSUER`, or caller's `sub` not in `CLERK_ALLOWED_SUBJECTS` | fix `CLERK_ISSUER`; check the allowlist |
| Deploy build fails / OOM | `next build` on 4 GB box | ensure the **2 GB swap** is active (`swapon --show`); builds are already sequential |
| Frontend shows an old Clerk key / API URL | `NEXT_PUBLIC_*` baked into a stale image | `up -d --build frontend` (§6.3) |

---

*Keep this file in step with `docker-compose.prod.yml`, `deploy/deploy.sh`, and `apps/shared/config.py`.
For deep CI/CD internals and the original setup runbook, see [`DEPLOYMENT.md`](../DEPLOYMENT.md).*
