# CyBreach Module 4 — Pod Gamma Service

Pod Gamma delivers real-time scoring analytics, high-velocity leaderboard aggregation, cohort benchmarking, user activity streaks, and badge achievement verification for the CyBreach platform.

The system combines an in-memory Redis sorted-set engine for sub-millisecond ranking queries with an asynchronous PostgreSQL persistence layer for cross-tenant historical data, user profiles, streaks, and verifiable achievement awards.

---

## Architecture Overview

```
                                +-------------------------------+
                                |  FastAPI Gateway (:8000)      |
                                +---------------+---------------+
                                                |
                   +----------------------------+----------------------------+
                   |                                                         |
         [Low-Latency Cache / State]                               [Relational Persistence]
                   |                                                         |
         +---------v---------+                                     +---------v---------+
         |    Redis Store    |                                     |   PostgreSQL 16   |
         | (Sorted Sets ZSET)|                                     |   (Asyncpg/SQLA)  |
         +-------------------+                                     +-------------------+
          - Global Leaderboards                                     - User Profiles
          - Dimension Rankings                                      - Streak History
          - Delta Improvement                                       - Badge Awards & Evidence
          - Tenant Indexing                                         - Benchmark Aggregates

```

---

## Core Capabilities

* Real-Time Leaderboard Engine (Redis): Tracks absolute and relative rankings globally and across dimensions (governance, identity, threat, cloud).
* Velocity & Improvement Tracking: Computes delta scores against historical snapshots to rank organizations by improvement rate.
* Benchmarking & Cohort Comparison: Compares tenant performance against peer cohorts segmented by industry sector and company size.
* Activity & Streak Engine: Implements a strict activity window (completions under 24 hours are debounced, 24–48 hours increment the streak, and >48 hours reset the streak).
* Verifiable Badge Awards: Unlocks milestone achievements and persists audit proof via structured evidence_ref tokens.
* Resilience & Rate Limiting: Sliding-window rate limiters per tenant with graceful fallback handling.

---

## Repository Structure

```
CyBreach-Module_4-Pod-Gamma/
├── app/
│   ├── api/                   # Router modules (leaderboard, benchmark endpoints)
│   ├── core/                  # Rate limiting & middleware
│   ├── db/                    # DB engine, Redis client, declarative base
│   │   ├── __init__.py        # PostgreSQL AsyncSession & Base declaration
│   │   └── redis_client.py    # Redis async connection pool
│   ├── models/                # Pydantic schemas & database entities
│   │   ├── __init__.py
│   │   └── schemas.py         # Request/Response validation models
│   ├── services/              # Business logic (leaderboard, improvement service)
│   ├── utils/                 # Statistical utilities & structured logging
│   ├── award_models.py        # SQLAlchemy BadgeAward DB models
│   ├── award_repository.py    # BadgeAward queries and persistence
│   ├── badges.py              # Gamification & badge criteria evaluation
│   ├── config.py              # Centralized environment configuration
│   ├── main.py                # Unified FastAPI gateway and routing
│   ├── models.py              # SQLAlchemy UserProfile DB models
│   ├── streak.py              # 24h/48h streak evaluation logic
│   ├── tenant_contract.py     # Tenant metadata contract rules
│   ├── user_models.py         # Relational user entities
│   └── user_repository.py     # UserProfile queries and persistence
├── config/
│   └── badges.json            # Badge definitions, milestones, and icon mappings
├── database/
│   ├── 001_sanitize_leaderboard_snapshot.sql
│   ├── 002_create_leaderboard_snapshot.sql
│   ├── 003_create_benchmark_aggregate.sql
│   ├── 005_add_badge_award_evidence.sql
│   ├── 005_seed_benchmark_aggregate.sql
│   ├── 006_create_benchmark_historical.sql
│   ├── 006_update_badge_award_primary_key.sql
│   ├── 007_create_user_profile.sql
│   ├── 007_seed_benchmark_historical.sql
│   ├── redis.conf             # Redis configuration
│   └── verify_leaderboard.py  # Snapshot verification utility
├── docs/
│   ├── integration_guide.md   # Inter-pod integration specifications
│   └── redis_module.md        # Redis key taxonomy & schema documentation
├── tests/                     # 72-case automated test suite
├── Dockerfile                 # Multi-stage production container image
├── docker-compose.yml         # Local stack orchestration (API + Redis + Postgres)
├── pytest.ini                 # Pytest runner & warning filter settings
└── requirements.txt           # Unified dependency manifest

```

---

## Environment Setup

### 1. Prerequisites

* Python 3.12 or 3.13
* Docker & Docker Compose (recommended for dependencies)
* PostgreSQL 16+ (if running without Docker)
* Redis 7.x+ (if running without Docker)

### 2. Environment Variables

Create a .env file in the root directory:

```bash
# On Windows CMD:
copy .env.example .env

# On Linux/macOS:
cp .env.example .env

```

Ensure the configuration matches your local or container setup:

```ini
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cybreach
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

```

---

## How to Run

### Method 1: Using Docker Compose (Full Stack)

This is the fastest method to spin up the FastAPI gateway, Redis, and PostgreSQL with all dependencies pre-configured:

```bash
# Build images and start all containers in detached mode
docker-compose up --build -d

# Follow application logs
docker-compose logs -f app

# Stop the stack
docker-compose down

```

The gateway will be accessible at http://localhost:8000.

---

### Method 2: Running Locally (Development Mode)

If running the application directly on your host machine:

#### Step 1: Start Redis and PostgreSQL

If you already have Docker installed, start just the backing data stores:

```bash
docker run --name cybreach-redis -p 6379:6379 -d redis:7-alpine
docker run --name cybreach-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=cybreach -p 5432:5432 -d postgres:16-alpine

```

#### Step 2: Set Up Python Virtual Environment

On Windows (CMD):

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

```

On Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

```

#### Step 3: Run Database Migrations

Initialize the schema and seed data into PostgreSQL:

```bash
psql -U postgres -h localhost -d cybreach -f database/001_sanitize_leaderboard_snapshot.sql
psql -U postgres -h localhost -d cybreach -f database/002_create_leaderboard_snapshot.sql
psql -U postgres -h localhost -d cybreach -f database/003_create_benchmark_aggregate.sql
psql -U postgres -h database/005_add_badge_award_evidence.sql
psql -U postgres -h localhost -d cybreach -f database/005_seed_benchmark_aggregate.sql
psql -U postgres -h localhost -d cybreach -f database/006_create_benchmark_historical.sql
psql -U postgres -h localhost -d cybreach -f database/006_update_badge_award_primary_key.sql
psql -U postgres -h localhost -d cybreach -f database/007_create_user_profile.sql
psql -U postgres -h localhost -d cybreach -f database/007_seed_benchmark_historical.sql

```

#### Step 4: Start the FastAPI Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

```

---

## Verifying the Service

Once started, test the application via curl or browse the interactive documentation:

* Swagger UI: http://localhost:8000/docs
* ReDoc: http://localhost:8000/redoc

### Smoke Test Commands

1. Health Check:
curl http://localhost:8000/health
2. Metrics:
curl http://localhost:8000/metrics
3. Ingest Analytics (SQL Track):
curl -X POST http://localhost:8000/api/v1/analytics -H "Content-Type: application/json" -d "{"tenant_id":"tenant_alpha","scores":[{"user_id":"usr_100","score":92.5,"timestamp":"2026-10-06T12:00:00Z"}]}"
4. Query Global Leaderboard (Redis Track):
curl http://localhost:8000/api/v1/leaderboard/global
5. Verify User Streak:
curl -X POST http://localhost:8000/api/v1/streak/verify -H "Content-Type: application/json" -d "{"user_id":"usr_100","action_timestamp":"2026-10-06T12:00:00Z"}"

---

## Running the Automated Test Suite

Run the full pytest suite (72 unit and integration tests across all microservice layers):

```bash
pytest -v

```

To run with test coverage reporting:

```bash
pytest -v --cov=app --cov-report=term-missing

```

---

## API Reference

### Health & Metrics

* GET /health — Liveness and readiness probe
* GET /metrics — Prometheus and operational runtime metrics

### Leaderboard & Benchmarking (Redis Core)

* GET /api/v1/leaderboard/global — Global absolute rankings
* GET /api/v1/leaderboard/{dimension} — Absolute rankings by category dimension
* POST /api/v1/leaderboard/score — Update or increment tenant score
* GET /api/v1/leaderboard/rank/{tenant_id} — Fetch current rank and score for a tenant
* GET /api/v1/leaderboard/improvement/global — Top tenant velocity rankings
* GET /api/v1/leaderboard/improvement/{dimension} — Top velocity rankings for a dimension
* GET /api/v1/benchmark/compare — Cohort peer comparison analysis

### Analytics, Streaks & Gamification (SQL Core)

* POST /api/v1/analytics — Ingest streaming analytics payload
* POST /api/v1/streak/verify — Evaluate activity timestamps and update consecutive streaks
* GET /user/{user_id}/streak — Retrieve current streak count and last active timestamp
* GET /user/{user_id}/badges — Retrieve unlocked badges for a user
* POST /api/v1/achievements/check — Process achievement criteria with evidence_ref validation
