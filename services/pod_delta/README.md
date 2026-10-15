# Pod Delta - API Gateway and Integration Services

Pod Delta is the browser-facing FastAPI service in the CyBreach Arena demo. It
provides authenticated APIs for notifications, preferences, analytics,
integration health, WebSocket events, and the Arena gateway. The Arena gateway
proxies selected requests to Pod Beta, Pod Gamma, and Wallet without exposing
upstream URLs or service credentials to the browser.

## Current features

- Local development-only manager sign-in and a tenant-scoped in-memory demo
  state.
- API gateway routes for Pod Beta campaign catalog, Pod Gamma leaderboard and
  synthetic benchmarks, configured upstream health, and production wallet
  read paths.
- Notification, preference, analytics, integration health, metrics, and
  WebSocket routes backed by the Delta service and its configured infrastructure.
- Local demo wallet balance, top-ups, printable receipt downloads, reports,
  notifications, analytics, and scan findings.

The demo wallet/checkout, scans and findings, receipts, notifications, ledger,
and analytics are simulated in Delta memory. No payment is charged, no real
target is contacted, and demo scan actions do not invoke Pod Beta engagement
execution or Wallet checkout. Restart the API or choose **Reset demo** to clear
the in-memory state. A demo receipt is not a tax invoice or proof of real
payment. Do not enable demo authentication outside loopback development.

## Requirements

- Python 3.12 recommended
- Docker Desktop/Engine with Compose for Redis, Redpanda, PostgreSQL, and
  ClickHouse infrastructure
- Node.js compatible with Vite 8 and npm for the frontend
- Pod Beta, Pod Gamma, and Wallet APIs if their live gateway routes are needed

## Configure and run the API (PowerShell)

From the repository root:

```powershell
Set-Location services\pod_delta
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt psycopg2-binary
docker compose up -d redis redpanda redpanda-init postgres clickhouse
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Edit `.env` to match the actual upstream API addresses. The defaults are:

| Variable | Default | Service |
| --- | --- | --- |
| `POD_BETA_CAMPAIGN_URL` | `http://127.0.0.1:8001` | Campaign catalog |
| `POD_BETA_ENGAGEMENT_URL` | `http://127.0.0.1:8002` | Engagement API |
| `POD_GAMMA_URL` | `http://127.0.0.1:8003` | Leaderboard and benchmark |
| `WALLET_SERVICE_URL` | `http://127.0.0.1:8004` | Wallet service |
| `POD_DELTA_INTERNAL_URL` | `http://127.0.0.1:8000` | Delta internal routes |

Individual service compose projects can have overlapping default host ports.
Change host port mappings or service URLs before starting them together.

## Demo login and safe-use notes

Default local demo credentials:

| Account ID | Password |
| --- | --- |
| `manager@cybreach.demo` | `ArenaDemo2026!` |

Demo auth requires `ENVIRONMENT=development`, `DEV_DEMO_AUTH_ENABLED=true`, and
a loopback client. `DEMO_ACCOUNT_ID`, `DEMO_ACCOUNT_PASSWORD`, and
`DEMO_STARTING_CREDITS` may be changed locally. These default credentials are
public demo credentials, not secrets or a production identity system.

The demo account uses only Delta's in-memory simulator. For authenticated
production Wallet reads, Delta signs a short-lived server-side delegated token
using `WALLET_SERVICE_JWT_SECRET`; it must match the Wallet service signing
configuration. Never send that secret to the browser. Demo checkout deliberately
does not call the Wallet service.

## Useful URLs and API docs

- API root / service status: <http://127.0.0.1:8000/>
- Health: <http://127.0.0.1:8000/api/v1/health>
- Integration health: <http://127.0.0.1:8000/api/v1/integration/health>
- Gateway API docs: <http://127.0.0.1:8000/api/docs>
- ReDoc: <http://127.0.0.1:8000/api/redoc>

The configured upstream connectivity report is available through the
authenticated `/api/v1/arena/connections` route. Browser calls must go through
Pod Delta; do not expose internal services or their credentials publicly.

## Frontend

The active React/Vite app is `services/pod_delta/frontend/`, not the old
root-level prototype assets:

```powershell
Set-Location services\pod_delta\frontend
npm install
npm run dev
```

Open <http://localhost:5173>. See the
[frontend guide](frontend/README.md) for user workflows and more detail about
the demo/live-data boundaries.

## Tests and integration checks

From the repository root, run the configured multi-service test suite:

```powershell
.\run-all-tests.ps1
```

For Delta only, run from this directory after activating the Delta virtual
environment:

```powershell
python -m pytest -q
```

For service start order, environment variables, Kafka event examples, and
integration smoke checks, see [INTEGRATION_RUNBOOK.md](INTEGRATION_RUNBOOK.md).
Passing tests or health checks do not imply that demo checkout, scans, or sample
findings are real transactions or security tests.
