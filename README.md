# Thai PHC v2 HSS API

FastAPI-based REST API for Health Support System (HSS) with async I/O and Tortoise ORM.

## Features

- FastAPI (async) and Pydantic v2
- Tortoise ORM + asyncpg (PostgreSQL)
- Aerich migrations
- Layered architecture: routers → controllers → services → repositories → models
- Structured logging with configurable format/levels
- OAuth2 Authorization Code + Refresh Token, OpenID Connect-style endpoints (userinfo, discovery, JWKS)
- Thai Digital ID (ThaiD) authentication flow with Tortoise-backed audit logging

## Project Structure

```text
app/
├── api/
│   ├── middleware/
│   │   └── middleware.py              # Access token and first-login token validation
│   └── v1/
│       ├── controllers/               # Orchestrates service calls
│       │   ├── healthcheck_controller.py
│       │   ├── oauth2.py
│       │   ├── officer_controller.py
│       │   ├── osm_controller.py
│       │   ├── report_controller.py
│       │   └── user_controller.py
│       ├── exceptions/
│       │   └── http_exceptions.py     # 400/401/404/500 helpers
│       ├── routers/                   # HTTP endpoints
│       │   ├── healthcheck.py         # /health
│       │   ├── oauth2_route.py        # /auth
│       │   ├── officer_route.py       # /officer
│       │   ├── osm_route.py           # /osm
│       │   └── report_route.py        # /report
│       └── schemas/                   # pydantic schema
│           ├── oauth2_schema.py
│           ├── officer_schema.py
│           ├── osm_schema.py
│           ├── query_schema.py
│           ├── report_schema.py
│           ├── response_schema.py
│           └── user_schema.py
├── configs/
│   └── config.py                      # Settings via pydantic-settings
├── db/
│   └── tortoise_config.py             # Tortoise ORM config (connections, apps)
├── models/                            # Tortoise models
│   ├── administration_model.py
│   ├── auth_model.py                  # OAuthClient, OAuthConsent, OAuthAuthorizationCode, RefreshToken
│   ├── award_training_model.py
│   ├── enum_models.py
│   ├── geography_model.py
│   ├── health_model.py
│   ├── officer_model.py
│   ├── osm_model.py
│   ├── personal_model.py
│   ├── position_model.py
│   ├── report_model.py
│   └── user_credential_model.py
├── repositories/
│   ├── client_repository.py
│   ├── credential_repository.py
│   ├── officer_profile_repository.py
│   ├── officer_repository.py
│   ├── osm_profile_repository.py
│   └── report_repository.py
├── router/
│   └── root.py                        # Mounts versioned routers under API_V1_PREFIX
├── services/
│   ├── oauth2_service.py
│   ├── officer_service.py
│   ├── osm_service.py
│   ├── report_service.py
│   └── user_service.py
├── utils/
│   ├── constant.py
│   ├── logging_utils.py               # configure_logging, log_request, decorators
│   └── security.py                    # JWT encode/decode utilities
├── main.py                            # FastAPI entry, CORS, request logging, DB registration
└── ...
migrations/                            # Aerich migrations (Tortoise)
```

## Setup & Installation

### Prerequisites

- Python 3.10+
- PostgreSQL

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd thaqi-phc-v2-hss-api
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**

   Create `.env` file in root directory. Example variables:

   ```env
   # App
   APP_NAME=THAI_PHC_V2
   API_V1_PREFIX=/api/v1

   # Database
   POSTGRES_DATABASE_URL=
   DB_POOL_MIN=
   DB_POOL_MAX=

   # OAuth/JWT
   JWT_SECRET_KEY=
   JWT_ALGORITHM=
   JWT_PRIVATE_KEY_PATH=
   JWT_PUBLIC_KEY_PATH=
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES=
   JWT_REFRESH_TOKEN_EXPIRE_MINUTES=
   JWT_REFRESH_TOKEN_EXPIRE_DAYS=

   # First-login token
   JWT_FIRST_LOGIN_TOKEN_SECRET_KEY=
   JWT_FIRST_LOGIN_TOKEN_ALGORITHM=
   JWT_FIRST_LOGIN_TOKEN_EXPIRE_MINUTES=

   # Authorization code lifetime
   OAUTH2_AUTHORIZATION_CODE_EXPIRE_MINUTES=

   # Session cookie
   JWT_SESSION_TOKEN_EXPIRE_MINUTES=

   # Logging
   LOG_LEVEL=INFO
   LOG_PRETTY=0
   LOG_REQUESTS=1
   REQ_LOG_THRESHOLD_MS=0
   ```

5. **Run the application**

   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at [http://localhost:8000](http://localhost:8000)

### Static uploads directory

By default the API mounts `/uploads` from the path specified by the `STATIC_UPLOADS_ROOT` environment variable (falling back to `/app/uploads` in containers). When running locally without that directory, the app now automatically uses `<repo>/uploads` and creates it if needed. Set `STATIC_UPLOADS_ROOT` if you want to point to another folder.

## Legacy OSM profile migration (MySQL -> Postgres)

This repo includes a safe *trial* migration script for completing legacy OSM profile data.

Script: [scripts/migrate_osm_profiles_mysql_to_postgres.py](scripts/migrate_osm_profiles_mysql_to_postgres.py)

### Required env vars

- Postgres: `DATABASE_URL` (preferred) or `POSTGRES_DATABASE_URL`
- MySQL: `MYSQL_HOST`, `MYSQL_PORT` (optional, default 3306), `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`

### Trial run (recommended)

Dry-run 24 rows (prints intended updates, does not write):

```bash
python scripts/migrate_osm_profiles_mysql_to_postgres.py --limit 24 --dry-run
```

Apply 24 rows:

```bash
python scripts/migrate_osm_profiles_mysql_to_postgres.py --limit 24 --apply
```

After each run, check the report JSON at:

`migrations/old_model_merge_new_modle/migrate_osm_profiles_report.json`

## Thai Digital ID (ThaiD) Authentication

The `/api/v1/thaid` router delivers a full Thai Digital ID login + logout experience while integrating with DOPA. Key components:

- **Router**: `app/api/v1/routers/thaid_route.py` exposes `POST /thaid/auth` and `POST /thaid/logout` with reusable response formatting.
- **Service layer**: `app/services/thaid_service.py` exchanges authorization codes for ThaiD tokens, resolves OSM/Officer identities, and issues OAuth2-aligned access/refresh pairs.
- **Audit logging**: `app/services/audit_service.py` writes to `admin_audit_logs` for both success and error cases.
- **JWT middleware**: `app/middleware/jwt_middleware.py` verifies access tokens (type=access, active user) for logout.
- **Utilities**: `app/utils/thaid_utils.py` centralises safe logging, masking, and consistent response codes.

### Environment variables

Add the following keys to `.env` (defaults shown where applicable):

```env
THAID_CLIENT_ID=
THAID_CLIENT_SECRET=
THAID_REQUEST_URI=
THAID_REDIRECT_URI=
ALGORITHM=HS256
JWT_EXPIRATION_DELTA_MIN=15
JWT_REFRESH_TOKEN_EXPIRATION_DELTA_DAYS=7
ENVIRONMENT=production
```

### Endpoints

- `POST /api/v1/thaid/auth` — Exchanges a ThaiD `auth_code` plus `client_id`/`user_type` for OAuth2 access & refresh tokens, reusing OSM or Officer profiles.
- `POST /api/v1/thaid/logout` — Requires a valid access token (Bearer) and records a logout audit entry.

Responses honour the standard `FormatResponseModel` contract with `res_code` values:

## Dashboard Summary API

- `GET /api/v1/dashboard/summary` keeps cached annual snapshots for every geography level.
- Pass `provinceCode`, `districtCode`, or `subdistrictCode` (aliases `province`, `district`, `subdistrict` are still accepted) to switch between province-, district-, and subdistrict-level summaries.
- Results now include a `level` flag plus matching `district*` / `subdistrict*` metadata so the frontend can render three granular views from the same contract.
- `forceRefresh=true` recalculates only the requested scope, so province refreshes do not touch district caches and vice versa. Refresh operations are limited to the current Buddhist year; older years must be corrected through data pipelines or manual migration scripts.
- Run the latest Aerich migration (`32_20251205093000_add_geography_levels_to_dashboard_summary.py`) after pulling these changes to add the new `geography_level`, `district_*`, and `subdistrict_*` columns.

### Scheduled Cache Warm-up

The API now **auto-refreshes** missing caches for the current Buddhist year, including multi-district requests. However, pre-warming caches via scheduled jobs is still recommended for better performance and to avoid timeout issues.

#### Monthly Cache Refresh

- Use `scripts/cache_dashboard_snapshots.sh` to pre-warm district caches at the end of each month. The script logs in with a service account, walks `/geo-management/districts` with `offset/limit` pagination, and refreshes each matching `/dashboard/summary` snapshot.
- Run `scripts/cache_subdistrict_snapshots.sh` about an hour later to hydrate the heavier subdistrict layer using the same pagination strategy.
#### New Year Cache Initialization

- **CRITICAL**: Run `scripts/new_year_cache_warmup.sh` on January 1st (or the first day of the Thai fiscal year) to initialize all caches for the new Buddhist year. This prevents slow first requests when the year changes.
- The script sequentially refreshes province, district, and subdistrict caches in one run.

#### Cron Configuration

Configure credentials and pacing via environment variables (`DASHBOARD_CACHE_USERNAME`, `CACHE_SLEEP_SECONDS`, `GEO_PAGE_SIZE`, `TOKEN_REFRESH_INTERVAL_SECONDS`, etc.) before wiring the scripts into crontab. Example entries:

```cron
# New Year cache initialization on January 1st at 01:00
0 1 1 1 * /usr/local/bin/new_year_cache_warmup.sh >> /var/log/dashboard-cache.log 2>&1

# Districts on the last day of the month at 21:00
0 21 28-31 * * [ $(date +\%d) -eq $(date -d tomorrow +\%d) ] && /usr/local/bin/cache_dashboard_snapshots.sh >> /var/log/dashboard-cache.log 2>&1

# Subdistricts an hour later at 22:00
0 22 28-31 * * [ $(date +\%d) -eq $(date -d tomorrow +\%d) ] && /usr/local/bin/cache_subdistrict_snapshots.sh >> /var/log/dashboard-cache.log 2>&1
```

All scripts require `jq` for pagination and only refresh the current Buddhist year, matching the API's enforcement. Historical corrections should be performed via dedicated ETL or migration jobs.

| Code | Meaning                         |
|------|---------------------------------|
| 0000 | ThaiD authentication succeeded  |
| 4010 | ThaiD-specific unauthorized     |
| 5000 | Internal server error           |

### Testing

Unit tests for the ThaiD feature live under `tests/thaid/` and cover happy paths, OAuth2 client validation, upstream errors, missing identity handling, and logout logging.

```powershell
pytest tests/thaid -q
```

## API Documentation

- **Interactive API Docs**: `http://localhost:8000/docs` (Swagger UI)

## Architecture Overview

### Layer Separation

This project follows a clean architecture pattern with clear separation of concerns:

- **Router Layer** (`app/router/`): Main routing configuration
- **API Layer** (`app/api/v1/`): Version-specific API endpoints
  - **Controllers** (`controllers/`): Request handling and business coordination
  - **Routers** (`routers/`): Route definitions and HTTP endpoint mappings
  - **Schemas** (`schemas/`): Request/response data validation
- **Service Layer** (`app/services/`): Business logic implementation
- **Repository Layer** (`app/repositories/`): Data access and persistence
- **Model Layer** (`app/models/`): Database entity definitions

### Key Components

#### Database Configuration

- **`app/db/tortoise_config.py`**: Tortoise ORM configuration
- **`app/configs/config.py`**: Application configuration settings

#### API Structure

- **`app/router/root.py`**: Central router that mounts versioned routers
- **`app/api/v1/routers/`**: endpoints
- **`app/api/v1/controllers/`**: controllers

#### Data Flow

```text
HTTP Request → Router → API Controller → Service → Repository → Database
     ↓            ↓          ↓            ↓          ↓           ↓
   Routing    Validation  Business    Data Logic  Database  Persistence
             (Schemas)    Logic                   Access
```

## 🔧 Development

### Adding New Features

1. **Create Model** in `app/models/`
2. **Define Schemas** in `app/api/v1/schemas/`
3. **Implement Repository** in `app/repositories/`
4. **Create Service** in `app/services/`
5. **Add Controller** in `app/api/v1/controllers/`
6. **Create Router** in `app/api/v1/routers/`
7. **Update Main Router** in `app/router/root.py`

### API Development Workflow

```bash
# 1. Create new feature branch
git checkout -b feature/new-endpoint

# 2. Implement following the architecture layers
# 3. Test endpoints using FastAPI docs
# 4. Commit and push changes
```

## 📋 Dependencies

From `requirements.txt` (key packages): FastAPI, Tortoise ORM, asyncpg, Aerich, bcrypt, PyJWT, cryptography, pydantic v2, pydantic-settings, uvicorn, starlette.

## CORS

Configured in `app/main.py` to allow:

- [http://localhost:3000](http://localhost:3000)
- [http://127.0.0.1:3000](http://127.0.0.1:3000)

## OAuth2 Endpoints (under `{API_V1_PREFIX}`)

- POST `/auth/pre-login` – body: `{ citizen_id }`
- POST `/auth/set-password` – Bearer First-Login Token, body: `{ password }`
- POST `/auth/login` – form: `username, password, client_id, state, user_type, redirect_to?` → 303 redirect, sets `session_token` cookie
- GET `/auth/authorize` – query: `client_id, redirect_uri, scope, state`
- POST `/auth/consent` – form: `client_id, redirect_uri, scopes[], state, action`
- POST `/auth/token` – Basic Auth (`client_id`/`client_secret`), grant types: `authorization_code` or `refresh_token`
- POST `/auth/revoke` – Basic Auth, form: `token, token_type_hint?`
- GET `/auth/userinfo` – Bearer access token
- GET `/.well-known/openid_configuration`
- GET `/.well-known/jwks.json`

## Other Routers

- Healthcheck: `GET /health/`
- OSM: `/osm/...` (protected)
- Officer: `/officer/...` (protected)
- Report: `/report/...` (protected)

## Reports

- `GET /reports/volunteer-gender` — production data sourced from `osm_gender_summary`, filtered by optional `province`, `district`, `subdistrict`, or `village` codes and paginated with `page` + `pageSize`. Response follows the mock envelope (`success`, `items`, `total`, `page`, `pageSize`) and also exposes `villageCode`, `villageNo`, and `villageName` (resolved from the authoritative `villages` table when available) for parity with OSM records.
- `POST /reports/volunteer-gender/refresh` — force rebuilds the live slice of `osm_gender_summary` (rows flagged with `snapshot_type = 'live'`) using the logic in `scripts/sql/refresh_osm_gender_summary.sql`. Use after bulk imports or before capturing reports.
- `POST /reports/volunteer-gender/snapshots` — copies the live rows into the same table but tagged with `snapshot_type = 'snapshot'`. The API always uses the current Thai fiscal year calculated with Bangkok time (UTC+07:00), so the `fiscalYear` field can be omitted and any provided value is ignored. Existing snapshot rows for that year are replaced.
- `GET /reports/volunteer-gender/snapshots` — read-only endpoint for historical data; accepts the same geography filters plus `fiscalYear` (falls back to the latest snapshot year when omitted).
- `GET /reports/volunteer-family` — live roster of volunteers, spouses, and children built directly from `osm_profiles`, `osm_spouses`, and `osm_children` with joins to the `villages` lookup so `villageName` is always populated. Supports the same geography filters/pagination and emits `status`/`statusLabel` so the UI can distinguish volunteer vs. family rows.
- `GET /reports/{reports_key}` — legacy mock dataset for UI development. The Postman "Mock Reports" request documents the remaining slugs (e.g., `volunteer-address`, `president-list`, etc.).

See the new **Reports (Live)** folder in `postman/Thaqi PHC v2 HSS API.postman_collection.json` for an authenticated example call against the live volunteer gender endpoint.

## Runbook

```bash
# 1) Configure .env
# 2) Run migrations
aerich upgrade
# Set .env
python -m venv venv # one time
source venv/bin/activate  # On Windows: venv\Scripts\activate
# 4) Start API
uvicorn app.main:app --reload
```

```bash
docker build -t registry.digitalocean.com/minerta-k8s/osm-thai-phc-hss-api:v1.6 .
docker push registry.digitalocean.com/minerta-k8s/osm-thai-phc-hss-api:v1.6
kubectl apply -f app-deployment.yaml

docker build -f admin-console/Dockerfile -t registry.digitalocean.com/minerta-k8s/thaiphc2-admin-console:dev13 admin-console
docker push registry.digitalocean.com/minerta-k8s/thaiphc2-admin-console:dev13
```
