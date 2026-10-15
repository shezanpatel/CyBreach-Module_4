# Pod Gamma - Leaderboards and Benchmarks

Pod Gamma is a FastAPI service backed by Redis. It provides player score and
rank APIs, tenant-aware dimension rankings, improvement rankings, cohort
benchmark endpoints, and additional Arena analytics/streak/badge routes.

## Current behavior

- Redis stores absolute global, industry, region, and size leaderboards and
  improvement rankings.
- Tenant opt-in records validated industry, region, and size metadata. Tenant
  score updates require opt-in and exactly matching metadata.
- A username can belong to only one tenant. Global-only set, increment, and
  bulk-score writes are rejected for users currently associated with a tenant
  so dimension rankings cannot drift out of sync.
- Opt-out removes the tenant's absolute and improvement rankings and consent
  metadata. Absolute-score and improvement updates require opt-in again.
- Opt-in metadata cannot change while absolute or improvement scores exist.
  User deletion cleans associated dimension indexes; leaderboard reset clears
  absolute and improvement rankings.
- Benchmark, comparison, and trend endpoints use exact seeded synthetic demo
  data. They are labelled as synthetic, are not real/private peer data, and do
  not apply differential privacy.

## Requirements

- Python 3.12 recommended
- Redis 7+
- PostgreSQL 16 for routes/features that use Gamma's relational persistence
- Docker Compose for the included standalone infrastructure

## Run standalone with Docker Compose

From this directory:

```powershell
Copy-Item .env.example .env
# Edit .env and set a local POSTGRES_PASSWORD and Redis credentials as needed.
docker compose up --build
```

The standalone compose file exposes the API at <http://127.0.0.1:8000>, Redis
at port 6379, and PostgreSQL at port 5432. These ports overlap with other
services in this repository. Change the compose host mappings and configure
Delta's `POD_GAMMA_URL` before running the stacks concurrently.

## Run the API on the host

Start Redis and PostgreSQL first, then from this directory:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

To use a non-default port such as the Arena gateway's default Gamma port:

```powershell
$env:APP_PORT = "8003"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8003
```

Set `REDIS_HOST`, `REDIS_PORT`, database settings, and credentials in `.env` to
match the services you started. The `uvicorn --port` argument controls the
actual listener port; set the matching application setting for accurate
configuration reporting.

## API reference

The API docs are available at `/docs` on the configured host/port. Common
endpoints include:

| Method and path | Purpose |
| --- | --- |
| `GET /health` | App and Redis health |
| `GET /leaderboard?limit=10` | Global absolute ranking |
| `GET /leaderboard/{dimension}` | Global, industry, region, or size absolute ranking |
| `POST /score` | Add/update a global or tenant-aware score |
| `POST /increment` | Increment a global-only player score |
| `GET /rank/{username}` | Get a player's score and rank |
| `GET /improvement?dimension=global` | Tenant improvement ranking |
| `POST /opt-in` / `POST /opt-out` | Manage tenant leaderboard consent |
| `DELETE /user/{username}` | Remove a player and associated dimension indexes |
| `DELETE /leaderboard` | Reset absolute and improvement indexes |
| `GET /benchmark/cohorts` | List seeded cohorts meeting the peer threshold |
| `POST /benchmark` | Read a seeded cohort baseline |
| `POST /benchmark/compare` | Compare regional and global synthetic baselines |
| `GET /benchmark/trend/{tenant_id}` | Read seeded historical synthetic trend |

Non-global leaderboard filters are `industry`, `region`, and `size_band`.
Improvement filters use `dimension` and `value`. Review API schemas in the
interactive docs for request payload shapes.

## Example tenant consent flow

Opt in before writing a tenant score:

```powershell
curl.exe -X POST http://127.0.0.1:8000/opt-in `
  -H "Content-Type: application/json" `
  -d "{\"tenant_id\":\"CORP-001\",\"industry\":\"technology\",\"region\":\"europe\",\"size\":\"1-50\"}"

curl.exe -X POST http://127.0.0.1:8000/score `
  -H "Content-Type: application/json" `
  -d "{\"username\":\"tenant_user\",\"score\":1500,\"tenant_id\":\"CORP-001\",\"industry\":\"technology\",\"region\":\"europe\",\"size\":\"1-50\"}"
```

After opt-out, score and improvement writes are rejected until the tenant
consents again. Do not send real organization data to the seeded benchmark API.

## Tests

From the repository root:

```powershell
Set-Location services\pod_gamma
..\..\.venv\Scripts\python.exe -m pytest tests -q
```

Or run the repository's full test command from the root:

```powershell
.\run-all-tests.ps1
```

The tests use in-memory Redis where configured. See
[`docs/redis_module.md`](docs/redis_module.md) for Redis key details.
