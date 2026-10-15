# CyBreach Arena - Module 4

CyBreach Arena is a multi-service demo for a cybersecurity training platform.
The checked-out repository combines Pod Delta (API gateway and event-driven
services), Pod Beta (campaign catalog and engagement APIs), Pod Gamma
(leaderboards and seeded cohort benchmarks), a Wallet service, and a React/Vite
web application.

The project currently supports a local manager demo with a simulated account,
wallet, checkout/receipt, scan findings, notifications, and analytics. Pod Delta
also proxies supported campaign, leaderboard, and benchmark requests to the
configured backends. See [Current behavior and limitations](#current-behavior-and-limitations)
before presenting this as a live security or payment product.

## What is in this repository

| Component | Location | Current responsibility |
| --- | --- | --- |
| Pod Delta | `services/pod_delta/` | Authenticated API gateway, notifications, preferences, analytics, Redis/Kafka integration, and local demo state |
| Pod Delta frontend | `services/pod_delta/frontend/` | React/Vite dashboard, campaigns, leaderboard, benchmark, demo wallet, and service status |
| Pod Beta | `services/pod_beta/app/` | Campaign catalog and engagement APIs |
| Pod Gamma | `services/pod_gamma/` | Redis leaderboard/improvement APIs, tenant consent lifecycle, and seeded synthetic cohort benchmark APIs |
| Wallet service | `services/wallet_service/` | FastAPI/PostgreSQL wallet, subscriptions, reconciliation, currency, and budget APIs |
| Pod Alpha | `services/pod_alpha/` | Empty in this checkout; no runnable service is included |

## Current behavior and limitations

- The default manager login is a **public development-only demo identity**:
  `manager@cybreach.demo` / `ArenaDemo2026!`. It works only when Pod Delta is in
  development mode, demo auth is enabled, and the API request is loopback.
- Demo top-ups, receipts, wallet balance/history, scans, findings, notifications,
  and analytics are simulated in Pod Delta's in-memory state. They do not charge
  money, contact targets, or process Wallet transactions. Restarting Delta or
  selecting **Reset demo** clears the demo state.
- Demo receipts are printable/downloadable HTML receipts for simulated
  transactions, not tax invoices or proof of real payment. The checkout does not
  request real card or bank credentials.
- Demo scan findings are sample results. The demo scan cards do not create or
  execute Pod Beta engagements.
- Pod Beta supplies campaign and engagement APIs. Pod Gamma supplies leaderboard
  and synthetic benchmark data. Gamma benchmark cohorts are seeded demo data,
  not real organization or private peer data; differential privacy is not applied.
- The Wallet service is a separate backend. A green service health check does not
  mean the simulated demo checkout is using it.
- Demo authentication and fallback infrastructure credentials are not suitable
  for production. Configure unique secrets, disable demo auth, add production
  identity/payment integrations, and review the security model before deployment.

## Prerequisites

- Git
- Python 3.12 recommended
- Node.js compatible with Vite 8 and npm
- Docker Desktop/Engine with Docker Compose for local infrastructure and Wallet
  integration tests

Check installations in PowerShell:

```powershell
git --version
python --version
node --version
npm --version
docker --version
docker compose version
```

## Download the project

```powershell
git clone https://github.com/shezanpatel/CyBreach-Module_4.git
Set-Location CyBreach-Module_4
```

Do not commit `.env` files or production credentials. Use the checked-in
`.env.example` files as local templates and replace development secrets before
any non-local deployment.

## Run the local demo

The quickest supported UI is Pod Delta's frontend. Start its backend and
configured upstream services first; the frontend sends API requests through
Delta rather than calling upstream pods from the browser.

### 1. Configure Pod Delta

```powershell
Copy-Item services\pod_delta\.env.example services\pod_delta\.env
```

Review the local service URLs and demo settings in that file. The defaults use
these API ports:

| API | Default port |
| --- | ---: |
| Pod Delta | 8000 |
| Pod Beta campaign catalog | 8001 |
| Pod Beta engagement API | 8002 |
| Pod Gamma | 8003 |
| Wallet service | 8004 |

The compose files for individual components may use port 8000 and common
database ports by default. When running several stacks simultaneously, configure
non-conflicting ports and make Delta's upstream URLs match them.

### 2. Install and start the APIs

Use separate terminals. Install each service's dependencies in its own virtual
environment where a `requirements.txt` is present. Pod Beta is source-only in
this checkout and has no dedicated dependency manifest; see
[Pod Beta setup](services/pod_beta/README.md).

For Pod Delta, start the infrastructure it needs from the Delta directory:

```powershell
Set-Location services\pod_delta
docker compose up -d redis redpanda redpanda-init postgres clickhouse
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt psycopg2-binary
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

For Pod Gamma, install its dependencies and start the API from another terminal.
Gamma needs Redis; configure its `.env`/environment to use the Redis instance
and a free API port (8003 for the defaults above):

```powershell
Set-Location services\pod_gamma
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:APP_PORT = "8003"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8003
```

See each component guide for its data stores, configuration, and optional
standalone setup. Pod Beta's two APIs are launched separately; configure their
host/port and package import path per
[Pod Beta setup](services/pod_beta/README.md). Wallet setup is documented in
[Wallet Service](services/wallet_service/README.md).

### 3. Start the frontend

```powershell
Set-Location services\pod_delta\frontend
npm install
npm run dev
```

Open <http://localhost:5173> and sign in with the local demo credentials shown
above. The API is available at <http://127.0.0.1:8000>; its interactive API
documentation is at <http://127.0.0.1:8000/api/docs>.

## Run tests

The repository test runner covers root/Pod Beta, Pod Gamma, Pod Delta, and
Wallet service tests. It creates Python 3.12 virtual environments, installs
each service's dependencies, and starts the Wallet test PostgreSQL container
on port 55432 if needed. Install Python 3.12 with the Windows `py` launcher and
Docker Desktop first:

```powershell
.\run-all-tests.ps1
```

Run individual suites from their service directories when debugging:

```powershell
Set-Location services\pod_gamma
.\.venv\Scripts\python.exe -m pytest tests -q

Set-Location ..\pod_delta
.\.venv\Scripts\python.exe -m pytest -q
```

The frontend has lint/build scripts:

```powershell
Set-Location services\pod_delta\frontend
npm run lint
npm run build
```

## Component guides

- [Pod Delta API and integrations](services/pod_delta/README.md)
- [Pod Delta integration runbook](services/pod_delta/INTEGRATION_RUNBOOK.md)
- [Pod Delta frontend](services/pod_delta/frontend/README.md)
- [Pod Beta](services/pod_beta/README.md)
- [Pod Gamma](services/pod_gamma/README.md)
- [Wallet service](services/wallet_service/README.md)

## Repository status and production readiness

All configured Python pod suites have recently passed together. The frontend
lint/build and current local service health have also been checked, but tests
and health checks do not establish production readiness. Pod Alpha is absent,
demo payment and scan flows are simulated, synthetic benchmark data is not real
peer data, and some dependencies emit deprecation warnings. Re-validate the
services and integrations after changing configuration or source.
