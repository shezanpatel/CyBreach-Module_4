# Pod Beta - Campaign Catalog and Engagement APIs

Pod Beta contains two FastAPI applications:

- Campaign catalog on `app.campaign.api:app`: campaign browsing and creation,
  hash verification, scheduling, and staged boss-fight endpoints.
- Engagement manager on `app.engagement.api:app`: engagement creation,
  lifecycle transitions, recommendations, and reports. It uses a local mock
  wallet and in-memory engagement state in this checkout.

The local Arena frontend uses the campaign catalog and engagement API as
configured upstreams. However, the demo scan/run workflow intentionally
generates sample findings in Pod Delta; it does not create or execute a Pod Beta
engagement. Do not present those demo scan reports as live security testing.

## Requirements

- Python 3.12 recommended
- FastAPI, Uvicorn, Pydantic 2, and SQLAlchemy 2

This source-only service currently has no dedicated `requirements.txt`, Docker
Compose file, or separate Pod Beta test command. Install the dependencies in a
virtual environment and run tests from the repository root using
[`run-all-tests.ps1`](../../run-all-tests.ps1).

## Install and run (PowerShell)

Create a virtual environment for this service:

```powershell
Set-Location services\pod_beta
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install fastapi uvicorn "pydantic>=2,<3" "sqlalchemy>=2,<3"
```

Start the campaign catalog in one terminal:

```powershell
Set-Location services\pod_beta
.\.venv\Scripts\uvicorn.exe app.campaign.api:app --reload --host 127.0.0.1 --port 8001
```

Start the engagement API in a second terminal:

```powershell
Set-Location services\pod_beta
.\.venv\Scripts\uvicorn.exe app.engagement.api:app --reload --host 127.0.0.1 --port 8002
```

Delta's default upstream settings use these local ports:

| API | Local URL |
| --- | --- |
| Campaign catalog | <http://127.0.0.1:8001> |
| Engagement manager | <http://127.0.0.1:8002> |

If you use different ports, update `POD_BETA_CAMPAIGN_URL` and
`POD_BETA_ENGAGEMENT_URL` in `services/pod_delta/.env` and restart Delta.

## Explore the APIs

- Campaign catalog docs: <http://127.0.0.1:8001/docs>
- Engagement manager docs: <http://127.0.0.1:8002/docs>
- Campaign list: `GET /campaigns`
- Engagement create: `POST /engagement/create`
- Engagement report: `GET /engagement/{id}/report`

Check the OpenAPI docs for required authentication headers and payloads.
Campaign definitions are loaded from the Pod Beta fixtures directory. Engagement
state and its mock wallet are process-local demo state and may reset when the
service restarts.

## Tests

The repository runner includes root and Pod Beta tests:

```powershell
Set-Location <repository-root>
.\run-all-tests.ps1
```

The Beta Python package is included on the root test runner's Python path; run
the suite through that runner rather than expecting a standalone Beta test
directory.
