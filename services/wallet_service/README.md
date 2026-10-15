# Wallet Service

The Wallet service is a separate FastAPI/PostgreSQL backend with wallet
transactions, transaction history/export, subscriptions, reconciliation,
currency conversion, budget alerts, and an authenticated integration API.
Kafka/Redpanda is configured for wallet events.

This is separate from Pod Delta's **simulated demo wallet**. The local Arena
demo checkout does not charge money or create Wallet service transactions.
Starting this service and seeing it healthy does not turn demo checkout into a
real payment flow.

## Requirements

- Python 3.12
- Docker Desktop/Engine with Docker Compose
- PostgreSQL (started by the included Compose file)
- Redpanda/Kafka (started by the included Compose file)

## Configure and run locally

From this directory:

```powershell
Copy-Item .env.example .env
# Review .env and set unique local secrets before exposing the API.
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
docker compose up -d postgres redpanda
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The included Compose file also defines the Wallet API container and publishes
it on host port `8000`. If running Uvicorn on the host, do not start that
container at the same time, or change its host port mapping. In an integrated
local stack, configure Delta's `WALLET_SERVICE_URL` to the Wallet API's host
address and port (default documented by Delta is `http://127.0.0.1:8004`).
Adjust the Wallet Compose mapping to `8004:8000` if using the container and that
port.

The `.env.example` file is a development template, not a production config.
`DATABASE_URL`, `JWT_SECRET_KEY`, `SERVICE_API_KEY`, and Kafka/database settings
must agree with the actual local deployment. Use unique, private values in any
shared or deployed environment.

## API documentation

When running locally, open <http://127.0.0.1:8000/docs>. The root route reports
service name, version, and status. The API includes:

- Wallet deposit, withdrawal, balance, transaction history, and export
- Wallet integration/authenticated service endpoints
- Subscription signup, renewal, upgrade/downgrade, and cancellation
- Reconciliation and currency conversion
- Budget alert configuration and checks

The exact schemas, authentication requirements, and response contracts are
defined in the generated OpenAPI documentation and the `app/api/v1/` modules.
The Wallet API is not anonymously exposed; configure a valid bearer token or
service credentials as required by the endpoint.

## Tests

Run a focused suite from this directory with the appropriate test dependencies
installed and its database configured:

```powershell
python -m pytest tests\unit -q
python -m pytest tests\contract -q
python -m pytest tests\integration -q
```

The integration tests require PostgreSQL and use the environment configured for
the tests. The full repository runner prepares its dedicated Wallet test
database and then runs the Wallet suite:

```powershell
Set-Location <repository-root>
.\run-all-tests.ps1
```

Do not point test setup at a production database.
