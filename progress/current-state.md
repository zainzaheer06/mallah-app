# Mallah Backend — Current State

**Last verified:** 5 May 2026
**Server:** Hetzner KSA, IP 5.78.115.147
**Repo path on server:** `/root/mallah-testing-app/`
**GitHub:** `https://github.com/zainzaheer06/mallah-app` (private)
**Live API base:** `http://5.78.115.147:8000/api/v1`
**Swagger UI:** `http://5.78.115.147:8000/docs`

This document captures everything that has been built, tested, and is currently running on the server. It is the source of truth for "what works right now" — distinct from `BACKEND_ROADMAP.md` which is the original engagement contract.

---

## Quick status

| Area | Status |
|---|---|
| D1 — Foundation & Auth (per roadmap) | ✅ Complete |
| Profile fields (gender, DOB, editable email) | ✅ Added post-D1 |
| Password change endpoint | ✅ Added post-D1 |
| Redis foundation (rate limit + health check + cache primitive) | ✅ Added post-D1 |
| Audience-split folder structure | ✅ Added post-D1 |
| Stack upgrade — Python 3.14 + Postgres 17 | ✅ Per client request |
| D2 — Catalog & Ingestion | ⏳ Not started (blocked on scraper sample payloads) |
| D3 — Home / Search / Detail | ⏳ Not started |
| D4 — Compare / Cart / Delivery engine | ⏳ Not started |
| D5 — Favourites / Notifications / Vendor / Admin dashboards | ⏳ Not started |
| D6 — TLS / Backups / Sentry / Hardening | ⏳ Not started |

---

## Stack

- **Language:** Python 3.14
- **Framework:** FastAPI 0.110+
- **ORM:** SQLAlchemy 2.x async + Alembic
- **Database:** PostgreSQL 17 (with `pg_trgm` extension installed for D3)
- **Cache / rate limit:** Redis 7
- **Auth:** Custom JWT (HS256) + Firebase Admin SDK (Google + phone OTP)
- **Password hashing:** bcrypt 4.x (direct, not via passlib)
- **Process manager:** Gunicorn + Uvicorn workers (2 workers on the 2 GB box)
- **Container:** Docker + docker-compose
- **Reverse proxy:** Container nginx in compose file but not currently routed

---

## Folder structure

The codebase uses an **audience-split** layout: business logic lives in `app/modules/`, HTTP routes live in `app/api/` grouped by who calls them. This is the modular monolith pattern that keeps consumer / admin / vendor / scraper concerns clean as new audiences come online in D5.

```
app/
├── core/                        # cross-cutting infrastructure (no business logic)
│   ├── config.py                # pydantic-settings, env vars
│   ├── db.py                    # async SQLAlchemy engine + session factory
│   ├── security.py              # bcrypt + JWT primitives
│   ├── deps.py                  # FastAPI deps (DbSession, CurrentUserId)
│   ├── exceptions.py            # AppException hierarchy → JSON errors
│   ├── logging.py               # structlog config
│   ├── middleware.py            # request_id, timing
│   └── cache.py                 # Redis client + get_or_set helper
│
├── modules/                     # ★ business logic (audience-agnostic)
│   ├── auth/                    # ✅ D1 — User, addresses, Firebase, JWT
│   │   ├── models.py            # User, UserAddress, AuthProvider, Gender
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── service.py           # all business logic (no FastAPI imports)
│   │   └── firebase.py          # Firebase Admin SDK wrapper
│   ├── catalog/                 # 🟡 D2 — Restaurants, menu items
│   ├── ingest/                  # 🟡 D2 — Scraper payload normalization
│   ├── home/                    # 🟡 D3 — Banners, feed
│   ├── search/                  # 🟡 D3 — pg_trgm fuzzy search
│   ├── compare/                 # 🟡 D4 — Price comparison
│   ├── cart/                    # 🟡 D4 — Cart simulation
│   ├── favorites/               # 🟡 D5 — Favorites + alerts
│   ├── notifications/           # 🟡 D5 — FCM + SendGrid
│   ├── admin/                   # 🟡 D5 — Admin operations
│   └── analytics/               # 🟡 D3+ — user_events, redirect_logs
│
├── api/                         # ★ HTTP routes split by audience
│   ├── consumer/                # mobile app (Firebase auth)
│   │   ├── auth.py              # /auth/* — register, login, firebase, refresh, logout, password reset
│   │   └── me.py                # /me/* — profile, addresses, password change
│   ├── ingestion/               # ready for D2 scraper endpoints (X-API-Key)
│   ├── ops/
│   │   └── health.py            # /health, /health/ready
│   │ (vendor/ folder created during D5 when first vendor route exists)
│   │ (admin/ folder created during D5 when first admin route exists)
│
├── interfaces/                  # ★ external system clients (placeholder)
│                                # ready for SendGrid, FCM, aggregators (D5)
│
├── workers/                     # ★ Celery entry points (placeholder)
│                                # populated when D4/D5 needs background tasks
│
└── main.py                      # composition root: middleware + router mounting
```

```
migrations/                      # Alembic
└── versions/
    ├── 0001_d1_baseline.py      # users + user_addresses + pg_trgm
    └── 0002_add_gender_and_dob.py

tests/                           # pytest suite (8 tests passing)
nginx/                           # reverse-proxy config (TLS-ready)
scripts/                         # postgres-init.sql, start.sh
test-d1.sh                       # 19-case bash smoke test (all passing)
```

**Why this structure:** the same `modules/auth/service.py` is callable from any audience — consumer login flow, admin user lookup, vendor auth check. When D5 adds vendor and admin web dashboards, they go in `app/api/vendor/` and `app/api/admin/` respectively, calling the shared business logic in `modules/`. No code duplication, no cross-audience cycles.

---

## What's running

```
docker compose ps
```

Three containers actively serving:

- `mallah-postgres` — PostgreSQL 17-alpine, port 5433 host-side (5432 internal)
- `mallah-redis` — Redis 7-alpine, port 6379, healthy
- `mallah-api` — FastAPI app on Python 3.14, port 8000, 2 Gunicorn workers

Nginx container is in the compose file but stopped (port 80 conflict resolved by removing the host nginx that served `facti.ai`; container nginx not currently needed since API is exposed directly on `:8000`).

---

## Endpoints currently live

### Authentication — `app/api/consumer/auth.py`

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Email + password registration. Returns access + refresh tokens. 409 on duplicate. |
| `POST` | `/api/v1/auth/login` | Email + password login. 401 on bad credentials (generic — doesn't leak which is wrong). |
| `POST` | `/api/v1/auth/firebase` | Verifies Firebase ID token, mints Mallah tokens. Auto-creates user on first login, links by `firebase_uid` on repeat. Verified working with phone OTP using test number `+966501234567` / code `123456`. |
| `POST` | `/api/v1/auth/refresh` | Exchanges refresh token for new access + refresh pair. Token-type confusion blocked. |
| `POST` | `/api/v1/auth/logout` | Returns 204. Client-side only — no server-side blocklist (Phase 2). |
| `POST` | `/api/v1/auth/password/reset-request` | Generates a reset token. In dev, the token is logged to stdout (until SendGrid is wired). Same response whether email exists or not (no leak). |
| `POST` | `/api/v1/auth/password/reset-confirm` | Confirms reset using the token, sets new password. Token expires after 30 minutes. |

### Profile — `app/api/consumer/me.py`

All require `Authorization: Bearer <access_token>`.

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/api/v1/me` | Returns current user profile (no `hashed_password`). |
| `PATCH` | `/api/v1/me` | Accepts: `display_name`, `email`, `language`, `default_city`, `gender`, `date_of_birth`. DOB validated (not future, age ≥ 13, age ≤ 120). Email change resets `is_email_verified`. Phone is **read-only** in MVP. |
| `DELETE` | `/api/v1/me` | PDPL-compliant soft delete. Anonymizes PII fields, sets `deleted_at`, keeps row for FK integrity. |
| `POST` | `/api/v1/me/password/change` | Logged-in password change. Requires `old_password`. Returns 400 for Firebase-only accounts (no local password). 400 if old equals new. |

### Addresses — `app/api/consumer/me.py`

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/api/v1/me/addresses` | Create. If `is_default: true`, backend auto-unsets previous default. First address auto-defaults. |
| `GET` | `/api/v1/me/addresses` | List (default first, then most recent). |
| `PATCH` | `/api/v1/me/addresses/{id}` | Update. Setting `is_default: true` un-defaults the previous one. |
| `DELETE` | `/api/v1/me/addresses/{id}` | Delete. **Note:** if the deleted address was default, no auto-promotion happens (frontend must handle). |

### Health / ops — `app/api/ops/health.py`

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/` | Basic info (name, version, env). |
| `GET` | `/health` | Liveness probe — returns 200 always (just confirms the process is up). |
| `GET` | `/health/ready` | Readiness probe. Returns 200 only if DB **and** Redis are reachable. Returns 503 with details if either fails. |
| `GET` | `/docs` | Swagger UI. |
| `GET` | `/redoc` | ReDoc UI. |
| `GET` | `/openapi.json` | OpenAPI spec. |

### Stub modules

These modules exist as scaffolding for future deliverables. Each has a `/{module}/health` endpoint that returns `{"module": "<name>", "status": "scaffolded"}`. No real logic.

`catalog`, `ingest`, `search`, `home`, `compare`, `cart`, `favorites`, `notifications`, `admin`, `analytics`.

---

## Database

**Connection:** `postgresql+asyncpg://mallah:****@postgres:5432/mallah` (inside container) or port 5433 from host.

**Migrations applied (in order):**

- `0001_d1_baseline.py` — creates `users` + `user_addresses` tables, installs `pg_trgm` extension
- `0002_add_gender_and_dob.py` — adds `gender` (varchar(32)) and `date_of_birth` (date) columns to `users`

**Live schema for `users`:**

```
id                | uuid PRIMARY KEY
email             | varchar(255) NOT NULL  (with partial unique idx where deleted_at IS NULL)
hashed_password   | varchar(255)           (nullable — Firebase-only users have no password)
firebase_uid      | varchar(128)           (unique, indexed)
auth_provider     | varchar(32) NOT NULL   ('email' | 'firebase_google' | 'firebase_apple' | 'firebase_phone')
display_name      | varchar(120)
phone_number      | varchar(32)            (read-only via API in MVP)
language          | varchar(8) NOT NULL    ('en' | 'ar', default 'en')
default_city      | varchar(80)
gender            | varchar(32)            ('male' | 'female' | 'prefer_not_to_say')
date_of_birth     | date
is_active         | boolean NOT NULL default true
is_admin          | boolean NOT NULL default false
is_email_verified | boolean NOT NULL default false
created_at        | timestamptz NOT NULL
updated_at        | timestamptz NOT NULL
last_login_at     | timestamptz
deleted_at        | timestamptz            (soft-delete marker)
```

**Live schema for `user_addresses`:**

```
id            | uuid PRIMARY KEY
user_id       | uuid FK users.id ON DELETE CASCADE
label         | varchar(40) NOT NULL
address_line  | varchar(500) NOT NULL
city          | varchar(80) NOT NULL
district      | varchar(80)
country       | varchar(2) NOT NULL default 'SA'
latitude      | float
longitude     | float
is_default    | boolean NOT NULL default false
created_at    | timestamptz NOT NULL
updated_at    | timestamptz NOT NULL
```

**Known schema cleanup deferred:** users table has both `uq_users_email` constraint and `ix_users_email_active` partial index — redundant. Will clean up in a later migration.

---

## Auth flow (verified end-to-end)

### Email / password

1. `POST /auth/register` → bcrypt-hashed password stored, JWT pair issued
2. `POST /auth/login` → bcrypt verify, JWT pair issued
3. Subsequent calls use `Authorization: Bearer <access_token>`
4. `POST /auth/refresh` exchanges expired access for new pair

### Firebase phone OTP (verified with test number)

1. Frontend obtains Firebase ID token via Firebase SDK
2. `POST /auth/firebase` with `{id_token: "..."}`
3. Backend verifies with Firebase Admin SDK (using credentials from `FIREBASE_CREDENTIALS_JSON` env var)
4. If `firebase_uid` is new, user is auto-created with synthetic email `phone_<uid>@phone.firebase.invalid`
5. If `firebase_uid` exists, returns existing user
6. Mallah JWTs returned to frontend

### JWT structure

- **Access token:** 60-minute expiry, payload: `{sub: user_id, type: "access", iat, exp, is_admin}`
- **Refresh token:** 30-day expiry, payload: `{sub, type: "refresh", iat, exp}`
- **Password reset token:** 30-minute expiry, payload: `{sub, type: "password_reset", iat, exp}`
- All signed HS256 with `JWT_SECRET_KEY` (32+ chars required)
- Token type confusion is blocked: `decode_token(token, expected_type=...)` rejects mismatches

---

## Rate limiting

**Current:** 60 requests / minute / IP, applied globally to all endpoints via `SlowAPIMiddleware`.

**Backed by Redis** (`storage_uri=settings.REDIS_URL`) — counters shared correctly across both Gunicorn workers.

**Strategy:** fixed-window (resets at the top of each minute, not rolling).

**Key function:** `get_remote_address` — keys by IP only. Per-user limits and per-route overrides are deferred until D3 search and D4 compare arrive.

---

## Known limitations / deferred items

These are deliberate, not bugs. Documented so future devs don't think they're missing something.

| Item | Why deferred | When to address |
|---|---|---|
| Server-side logout / token blocklist | Phase 2 per roadmap | When session revocation is genuinely needed |
| Refresh token rotation (one-time-use) | Phase 2 — needs Redis jti store | Same time as blocklist |
| Per-user rate limits + per-route overrides | Sufficient for MVP | When D3 search and D4 compare arrive |
| Real password reset emails | SendGrid creds blocked on client | When `SENDGRID_API_KEY` is provisioned |
| Avatar upload | Awaiting product decision (MVP or v2?) | TBD |
| Phone number editing | Read-only in MVP per discussion | Phase 2 — needs re-verify flow |
| Email verification flow | Phase 2 | Same time as SendGrid integration |
| Auto-promote address default on delete | Frontend handles for now | If product decides backend should |
| Smart Saver / Deal Hunter tier badges | No tier-promotion engine in scope | Out of MVP scope |
| Cuisine preferences | Phase 2 per roadmap | Out of MVP scope |
| Real Apple sign-in | Code path works, blocked on iOS team | When frontend wires it |
| Schema cleanup (redundant email index/constraint) | Cosmetic, not breaking | Next migration cycle |

---

## How to run locally

```bash
git clone https://github.com/zainzaheer06/mallah-app.git
cd mallah-app
cp .env.example .env

# Generate a real JWT secret
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> .env

# Set the ingest API key
echo "INGEST_API_KEY=$(openssl rand -hex 16)" >> .env

# Optional: paste Firebase service account JSON for phone-OTP testing
# echo "FIREBASE_CREDENTIALS_JSON='<paste full service account JSON here>'" >> .env

docker compose up -d --build
docker compose exec api alembic upgrade head

# API is at http://localhost:8000
# Swagger at http://localhost:8000/docs
```

---

## How to test

A bash smoke-test script lives at `test-d1.sh` on the server. Runs 19 cases covering register, login, /me, addresses, refresh, password reset, error paths, and soft-delete. **All passing as of the most recent verification.**

```bash
./test-d1.sh
```

There's also a pytest suite at `tests/test_auth.py` — 8 tests covering the same flows in pure Python. Run with:

```bash
docker compose exec api pytest tests/ -v
```

---

## Configuration (`.env`)

All settings load from environment variables via `pydantic-settings`. Required:

| Var | Purpose |
|---|---|
| `JWT_SECRET_KEY` | Signs all JWTs. Must be 32+ chars. Generate with `openssl rand -hex 32`. |
| `INGEST_API_KEY` | Shared secret for scraping team's `/ingest` calls. 16+ chars. |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `REDIS_URL` | `redis://redis:6379/0` |

Optional but configured for D1+:

| Var | Purpose |
|---|---|
| `FIREBASE_PROJECT_ID` | e.g. `mallah-testing` |
| `FIREBASE_CREDENTIALS_PATH` | `/app/firebase-creds.json` (mounted) — OR — |
| `FIREBASE_CREDENTIALS_JSON` | full service account JSON inlined as env var (preferred) |
| `FIREBASE_WEB_API_KEY` | for testing OTP flow via Firebase REST API |

Stubbed (D5+):

| Var | Purpose |
|---|---|
| `SENDGRID_API_KEY` | Empty until client provides creds |
| `SENTRY_DSN` | Optional; integration is conditional |

---

## Secrets handling

Currently using **Level 2** approach (env-vars). Firebase credentials live in `.env` as a JSON-string env var (`FIREBASE_CREDENTIALS_JSON`). No JSON file on disk. `.env` is in `.gitignore`.

**Not yet at:** Doppler / GCP Secret Manager / Workload Identity. Recommended for production launch.

---

## What hasn't been verified yet

Honest list of things not directly exercised in testing:

- Apple sign-in via Firebase (code path is identical to Google/Phone, but no real Apple test)
- Behavior under high concurrency (no load test run)
- Backup + restore flow (Makefile target exists, never executed end-to-end)
- TLS termination (HTTPS not configured — running on raw HTTP `:8000`)
- Behavior with a Postgres failover / restart mid-request
- Behavior when Redis goes down mid-session (graceful degradation expected, not load-tested)

---

## Files of interest for new devs

If you're trying to understand a specific area, jump here:

| To understand... | Read |
|---|---|
| All env vars | `.env.example` |
| App startup, middleware, router composition | `app/main.py` |
| Auth + profile + address business logic | `app/modules/auth/service.py` |
| Auth HTTP routes (`/auth/*`) | `app/api/consumer/auth.py` |
| Profile + address HTTP routes (`/me/*`) | `app/api/consumer/me.py` |
| Health / readiness routes | `app/api/ops/health.py` |
| User / address ORM models | `app/modules/auth/models.py` |
| Pydantic schemas | `app/modules/auth/schemas.py` |
| Firebase Admin SDK wrapper | `app/modules/auth/firebase.py` |
| Password hashing + JWT primitives | `app/core/security.py` |
| FastAPI dependencies (`CurrentUserId`, `DbSession`) | `app/core/deps.py` |
| Custom exception hierarchy | `app/core/exceptions.py` |
| Redis client + cache helpers | `app/core/cache.py` |
| Config / settings | `app/core/config.py` |
| Database migrations | `migrations/versions/*.py` |
| Container orchestration | `docker-compose.yml` |
| Production image build | `Dockerfile` |

---

## Patterns to follow when adding new code

When D2-D6 work begins, follow these conventions to keep the codebase consistent:

**Adding a new business domain (D2 catalog, D3 search, etc.):**
1. Create `app/modules/<domain>/` with `models.py`, `schemas.py`, `service.py`
2. Service functions take `(db: AsyncSession, ...args)` and contain all business logic
3. Service functions never import FastAPI — they're framework-agnostic
4. Models import `from app.core.db import Base`
5. Add a migration in `migrations/versions/000N_<description>.py`

**Adding a new HTTP route:**
1. Choose audience: `app/api/consumer/`, `vendor/`, `admin/`, or `ingestion/`
2. Create or extend the audience file (`catalog.py`, `search.py`, etc.)
3. Each file defines a single `router = APIRouter(prefix="/...", tags=[...])`
4. Routes are thin: parse input → call `service.function()` → return result
5. Mount the new router in `app/main.py` with `app.include_router(...)`

**Adding a new external service (SendGrid, FCM, aggregator API):**
1. Create `app/interfaces/<service>.py`
2. Singleton client with retry + timeout config
3. Service modules import from `interfaces/`, not directly from SDKs

**Adding a Celery task:**
1. Define task in `app/modules/<domain>/tasks.py`
2. Wire entry point in `app/workers/<domain>.py`
3. `workers/celery_app.py` discovers tasks automatically

---

## Open product questions

These came up during D1 work and are still pending decisions before D5:

1. **Avatar upload** — in MVP screens or just on Figma mocks?
2. **Phone change** — "contact support" link, or build the re-verify flow?
3. **Help / Support** — mailto link, Tawk.to widget, or real ticket endpoint?
4. **Address auto-promote on delete** — backend handles, or frontend forces user to pick a new default first?
5. **Cuisine preferences** — Phase 2 per roadmap, but Smart Offers on home screen depends on it. Bring into MVP scope, or accept that Smart Offers will be generic in MVP?
6. **Smart Saver / Deal Hunter tier badges** — visible in profile screen design, but no tier-promotion logic in scope. Remove from MVP screens, or build the engine?
7. **V2.1 architecture scope reconciliation** — V2.1 doc adds delivery observation engine, KNN estimator, Celery infrastructure, and 5+ new tables vs the original 6-week roadmap. Confirm whether this is in-scope or treated as Phase 2.

---

*Document maintainer: whoever ships the next change. Update timestamps + status table when work lands.*