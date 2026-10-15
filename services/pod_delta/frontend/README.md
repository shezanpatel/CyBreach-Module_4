# CyBreach Arena - Pod Delta frontend

React + Vite frontend. Browser API requests are sent to the Pod Delta gateway;
service URLs and service credentials are never configured in browser code.

## Run locally

Requirements: Node.js 20.19+ or 22.12+ and npm (Vite 8 supported runtimes),
plus a running Pod Delta API at `127.0.0.1:8000`.

Start the Pod Delta API on `127.0.0.1:8000` first. The Vite development server
proxies `/api` requests to that API. Then, from this directory:

```powershell
npm install
npm run dev
```

Open http://localhost:5173 and sign in with the local demo account:

| Account ID | Password |
| --- | --- |
| `manager@cybreach.demo` | `ArenaDemo2026!` |

This shared, deliberately public account works only when
`ENVIRONMENT=development`, `DEV_DEMO_AUTH_ENABLED=true`, and the API request
comes from a loopback client. It is not real authentication and must never be
enabled in production.

All account effects are simulated locally by Pod Delta's in-memory demo
ledger: top-ups always approve without charging money; scan runs return sample
findings without contacting targets; analytics, notifications, payment receipts,
and the ledger are demo records. The top-up checkout collects billing name,
email, and address to create a printable receipt. It uses fixed sandbox card/UPI
instruments and never asks for a real card number, CVV, or bank credentials.
Receipts show the simulated amount and explicitly state that no money was
charged; they are not tax invoices or proof of a real payment. The Wallet service
is not modified or charged. Receipts can be downloaded as printable HTML or
printed/saved as PDF in a standalone receipt document so the checkout dialog
cannot clip the print output. If the browser blocks the print window, the
receipt is downloaded as HTML instead. Simulated run reports are also available
as readable HTML and machine-readable JSON; each report identifies Pod Delta's
simulator as its source and states that Pod Beta did not execute the run. Demo
data resets when the API restarts or the user chooses **Reset demo**.

Use **Sign out** in the header to end the in-memory demo session and return to
the login screen. The dashboard summarizes live upstream health and the
connected campaign and leaderboard data; it does not invent user balances,
activity, or awards.

## Connected services

Configure these server-side in the Pod Delta environment:

| Setting | Local default | Backend |
| --- | --- | --- |
| `POD_BETA_CAMPAIGN_URL` | `http://127.0.0.1:8001` | Pod Beta campaign catalog |
| `POD_BETA_ENGAGEMENT_URL` | `http://127.0.0.1:8002` | Pod Beta engagement API |
| `POD_GAMMA_URL` | `http://127.0.0.1:8003` | Pod Gamma leaderboard and benchmark |
| `WALLET_SERVICE_URL` | `http://127.0.0.1:8004` | Wallet service |
| `POD_DELTA_INTERNAL_URL` | `http://127.0.0.1:8000` | Pod Delta notifications, preferences, and analytics |

The development demo account uses a separate simulated ledger. It cannot read
or modify live Wallet records. Production wallet reads use
`WALLET_SERVICE_JWT_SECRET` on the Delta server to create a short-lived
server-side delegated token; that secret is never sent to the browser.

## Data and safety

- The Campaigns, Leaderboard, Benchmark, Wallet, Notifications, Analytics, and
  Services views request data through the authenticated Pod Delta gateway.
- Seeded/demo values are identified in the UI; unavailable APIs show errors
  rather than being presented as live data.
- The local demo has a working simulated wallet, payment selection, ledger,
  scan runs, notifications, and analytics, all clearly labeled as simulated.
- Demo operations never call Wallet checkout or Pod Beta engagement creation.
- Pod Beta provides the campaign catalog and engagement API; the local demo
  scan cards intentionally generate sample results in Pod Delta instead.
- Campaign catalog, leaderboard, benchmark, and service-health views continue
  to demonstrate their configured pod integrations.
- The benchmark form loads available peer cohorts from Pod Gamma and excludes
  groups below Gamma's minimum peer count, avoiding unsupported combinations.
  Benchmark values are exact seeded synthetic baselines for the demo; they are
  not real organization or private peer data, and differential privacy is not
  applied to these synthetic values.
- `services/pod_alpha` currently contains no runnable API. The repository's
  `services/wallet_service` is the available wallet backend.

## Build

```powershell
npm run build
npm run preview
```
