# Integration Runbook

## Start

```powershell
Copy-Item .env.example .env
docker compose up -d redis redpanda redpanda-init postgres
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt psycopg2-binary
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Full Docker stack:

```powershell
docker compose up --build
```

## Verify Health

```powershell
curl http://127.0.0.1:8000/api/v1/integration/health
```

## Frontend API Gateway

The browser must call Pod Delta only. Pod Delta proxies authenticated requests
to Pod Beta, Pod Gamma, the Wallet service, and its own tenant-scoped
notifications/preferences/analytics APIs. The default local API ports are:

| Service | Port |
| --- | ---: |
| Pod Delta | 8000 |
| Pod Beta campaign catalog | 8001 |
| Pod Beta engagement manager | 8002 |
| Pod Gamma | 8003 |
| Wallet service | 8004 |

Set the `POD_BETA_CAMPAIGN_URL`, `POD_BETA_ENGAGEMENT_URL`, `POD_GAMMA_URL`,
`WALLET_SERVICE_URL`, and `POD_DELTA_INTERNAL_URL` variables when the APIs use
different addresses. The default URLs are for local development; do not expose
the Beta, Gamma, or Wallet APIs publicly. Keep them on a private service
network and expose only the authenticated Delta gateway.

The local demo account issues a short-lived token only when
`ENVIRONMENT=development`, `DEV_DEMO_AUTH_ENABLED=true`, and the request is
from a loopback client. The shared credentials are
`manager@cybreach.demo` / `ArenaDemo2026!` by default; configure
`DEMO_ACCOUNT_ID`, `DEMO_ACCOUNT_PASSWORD`, and `DEMO_STARTING_CREDITS` to
override them locally. This is not production authentication. The Wallet API
validates JWT signatures independently. Configure
`WALLET_SERVICE_JWT_SECRET` on Delta to match the Wallet service's
`JWT_SECRET_KEY`; Delta creates a short-lived server-side delegation token.
Because Wallet authorizes per-user balance/history paths against its
`tenant_id` claim, Delta scopes the delegated token's tenant to the authenticated
subject used for that user's wallet path.
Demo top-ups, receipts, scans, ledger, notifications, and analytics use only
Delta's in-memory demo state. Checkout collects billing name, email, and address
for a simulated receipt, and uses fixed demo card/UPI instruments; it never
collects real card or bank credentials. Each checkout has a replay-safe ID, and
receipts are retained in the demo state until reset. Payments are always
simulated and no external targets are contacted. Restart Delta or select
**Reset demo** to restore the initial state. Production must use the real
identity provider and production secrets, with local demo auth disabled.

Simulated top-up receipts can be downloaded as printable HTML or printed to
PDF from a standalone receipt document, avoiding the scrollable checkout dialog.
When browser popup settings block that print document, the flow downloads the
HTML receipt instead. Demo run reports can be downloaded as HTML or JSON and
identify the Delta simulator as their source. Pod Beta provides the campaign catalog and
engagement API; the current demo run cards do not invoke Pod Beta or perform
real security tests, so their findings must not be presented as live test
results.

The gateway provides read-only UI integration for campaign catalog,
engagement recommendations, leaderboard, benchmark, and health. Pod Gamma
exposes `GET /benchmark/cohorts`; Delta proxies the authenticated request, and
the frontend builds its selectors only from cohorts meeting Gamma's minimum
peer threshold. Benchmark values are exact seeded synthetic baselines, not real
organization or private peer data; differential privacy is not applied to
these demo values. In demo
sessions, wallet, top-up, scan-run, notification, and analytics operations
stay inside the simulated demo ledger; they do not invoke Wallet checkout or
Pod Beta engagement creation.

`services/pod_alpha` is empty in this checkout; the wallet backend is located
at `services/wallet_service`.

The Vite frontend proxies `/api` to `http://127.0.0.1:8000` in development.
Start each API on its assigned port before opening the frontend. The Services
tab reports configured upstream reachability. A successful build does not
mean the pods are running; verify the Services tab and each API's health route.

## Verify Score Display Flow

Produce:

```powershell
docker compose exec redpanda rpk topic produce mod3.score --brokers redpanda:9092
```

Message:

```json
{"event_type":"mod3.score","event_id":"score-1","tenant_id":"tenant-a","timestamp":"2026-09-20T00:00:00Z","data":{"score":82.5,"previous_score":80.0,"trend":"up","components":{"training":40,"response":42.5}}}
```

Check Redis and published event:

```powershell
docker compose exec redis redis-cli GET score:tenant-a
docker compose exec redpanda rpk topic consume score.displayed --brokers redpanda:9092 --num 1
```

## Verify Notification Flow

Produce:

```powershell
docker compose exec redpanda rpk topic produce achievement.awarded --brokers redpanda:9092
```

Message:

```json
{"event_type":"achievement.awarded","event_id":"ach-1","tenant_id":"tenant-a","timestamp":"2026-09-20T00:00:00Z","data":{"achievement_id":"first-defense","achievement_name":"First Defense","user_id":1,"points":50}}
```

Check Notification Hub and published event:

```powershell
curl "http://127.0.0.1:8000/api/v1/notifications/?user_id=1"
docker compose exec redpanda rpk topic consume notification.sent --brokers redpanda:9092 --num 1
```

## Verify Analytics Flow

Produce:

```powershell
docker compose exec redpanda rpk topic produce wallet.transaction --brokers redpanda:9092
```

Message:

```json
{"event_type":"wallet.transaction","event_id":"wallet-1","tenant_id":"tenant-a","timestamp":"2026-09-20T00:00:00Z","data":{"transaction_id":"txn-1","amount":10.0,"currency":"USD","direction":"credit","status":"completed","user_id":1}}
```

Check Analytics Engine and published event:

```powershell
curl "http://127.0.0.1:8000/api/v1/analytics?tenant_id=tenant-a"
docker compose exec redpanda rpk topic consume analytics.report --brokers redpanda:9092 --num 1
```

## Tests

```powershell
pytest tests/integration/test_app_integration_layer.py
```
