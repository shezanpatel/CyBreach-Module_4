# CyBreach Arena – Full Setup Guide

This repository is a full-stack project built around a FastAPI backend for the Pod Delta system. It contains:

- Notification APIs
- Analytics APIs
- Integration services with Kafka/Redpanda, Redis, and WebSocket feeds
- A React front-end prototype file set in the project root
- Docker-based infrastructure for local running

The main application logic runs from the Python backend under `app/`, while the root-level React files (`App.jsx`, `CyBreachArena.jsx`, `main.jsx`, `App.css`, `index.css`) are frontend prototype artifacts that can be launched in a separate Vite app.

---

## 1. What this project includes

### Backend
- FastAPI application in `app/main.py`
- Notification routes in `app/api/notification_routes.py`
- Preference routes in `app/api/preference_routes.py`
- Analytics routes in `app/api/analytics_engine_routes.py`
- Integration routes in `app/api/integration_routes.py`
- WebSocket route in `app/api/websocket_routes.py`

### Integration services
- Kafka / Redpanda consumer and producer logic
- Redis cache and rate-limiter support
- WebSocket session handling for tenant updates
- Prometheus metrics output

### Frontend
- Root-level React files are included as prototype / UI assets
- These are not the active backend runtime, but they can be run as a Vite React app if needed

---

## 2. Prerequisites

Install the following before running anything:

### Required
- Python 3.11+
- Node.js 18+ and npm
- Docker Desktop / Docker Engine with Compose
- Git

### Verify installation

Windows PowerShell:

```powershell
python --version
node -v
npm -v
docker --version
```

If any are missing, install them first.

---

## 3. Clone the project

```bash
git clone https://github.com/medhagupta1216/CyBreach-arena--Pod-delta.git
cd CyBreach-arena--Pod-delta
```

If you downloaded the project as a zip, extract it first and open the folder in VS Code.

---

## 4. Create environment files

From the project root:

```powershell
Copy-Item .env.example .env
```

The `.env` file is used by the backend to configure database, Redis, Kafka, and security settings.

Example values are already in `.env.example`.

---

## 5. Backend setup from scratch

### 5.1 Create Python virtual environment

```powershell
python -m venv venv
```

Activate it:

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```cmd
venv\Scripts\activate.bat
```

Linux / macOS:

```bash
source venv/bin/activate
```

### 5.2 Install Python dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt psycopg2-binary
```

This installs the FastAPI app dependencies and Postgres support.

### 5.3 Start the supporting services

The backend depends on Redis, Redpanda, Postgres, and optionally ClickHouse.

From the project root:

```powershell
docker compose up -d redis redpanda redpanda-init postgres clickhouse
```

This will start:

- Redis: `localhost:6379`
- Redpanda: `localhost:19092`
- Postgres: `localhost:5432`
- ClickHouse: `localhost:8123`

If you want the full stack including the API service container:

```powershell
docker compose up --build
```

---

## 6. Run the backend server

Once the infrastructure is running:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The server will be available at:

- API root: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/api/v1/health`
- Integration health: `http://127.0.0.1:8000/api/v1/integration/health`
- Swagger: `http://127.0.0.1:8000/api/docs`
- ReDoc: `http://127.0.0.1:8000/api/redoc`
- OpenAPI: `http://127.0.0.1:8000/api/openapi.json`

---

## 7. Backend API overview

### Health endpoints

- `GET /`
- `GET /api/v1/health`
- `GET /api/v1/integration/health`
- `GET /metrics`

### Notification API

Base path:

```text
/api/v1/notifications
```

Available endpoints:

- `GET /api/v1/notifications/`
- `GET /api/v1/notifications/user/{user_id}`
- `GET /api/v1/notifications/unread`
- `GET /api/v1/notifications/unread/count`
- `GET /api/v1/notifications/stats`
- `POST /api/v1/notifications/`
- `PUT /api/v1/notifications/{notification_id}`
- `DELETE /api/v1/notifications/{notification_id}`
- `PATCH /api/v1/notifications/{notification_id}/read`
- `PATCH /api/v1/notifications/{notification_id}/status`
- `PATCH /api/v1/notifications/bulk/read`
- `DELETE /api/v1/notifications/bulk`

### Preference API

Base path:

```text
/api/v1/preferences
```

Available endpoints:

- `POST /api/v1/preferences/`
- `GET /api/v1/preferences/{user_id}`
- `PUT /api/v1/preferences/{user_id}`

### Analytics API

Base path:

```text
/api/v1/analytics
```

Available endpoints:

- `POST /api/v1/analytics`
- `GET /api/v1/analytics`
- `GET /api/v1/analytics/{id}`
- `GET /api/v1/analytics/tenant/{tenant_id}`
- `GET /api/v1/analytics/dashboard/{tenant_id}`
- `GET /api/v1/analytics/credit-flow/{tenant_id}`
- `GET /api/v1/analytics/engagement/{tenant_id}`
- `GET /api/v1/analytics/score/{tenant_id}`
- `GET /api/v1/analytics/score-trend/{tenant_id}`
- `GET /api/v1/analytics/report/{tenant_id}`
- `PUT /api/v1/analytics/{id}`
- `DELETE /api/v1/analytics/{id}`

### Integration API

Base path:

```text
/api/v1/integration
```

Available endpoints:

- `GET /api/v1/integration/health`
- `GET /api/v1/integration/score/{tenant_id}`
- `GET /api/v1/integration/metrics`
- `POST /api/v1/integration/analytics/flush/{tenant_id}`

---

## 8. Notification flow and Kafka events

This project listens for integration events from Kafka topics like:

- `wallet.transaction`
- `engagement.lifecycle`
- `engagement.completed`
- `mod3.score`
- `achievement.awarded`
- `leaderboard.updated`
- `benchmark.computed`

It can publish events such as:

- `notification.sent`
- `analytics.report`
- `score.displayed`

This is the main event-driven part of the Pod Delta system.

---

## 9. Example API calls

### Get health

```powershell
curl http://127.0.0.1:8000/api/v1/health
```

### Create a notification

```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/notifications/" ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\":1,\"title\":\"Security Alert\",\"message\":\"Suspicious login detected\",\"channel\":\"email\",\"priority\":\"high\"}"
```

### Get notifications for a user

```powershell
curl "http://127.0.0.1:8000/api/v1/notifications/user/1"
```

### Get notification stats

```powershell
curl "http://127.0.0.1:8000/api/v1/notifications/stats"
```

### Create preferences

```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/preferences/" ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\":1,\"email\":true,\"sms\":false,\"push\":true,\"in_app\":true}"
```

### Get analytics for a tenant

```powershell
curl "http://127.0.0.1:8000/api/v1/analytics/tenant/tenant-a"
```

---

## 10. WebSocket setup

The app exposes a tenant-specific WebSocket endpoint:

```text
ws://127.0.0.1:8000/ws/{tenant_id}?token=<JWT>
```

Your JWT token should contain a `tenant_id` claim that matches the URL tenant.

Example:

```text
ws://127.0.0.1:8000/ws/tenant-a?token=eyJ...
```

---

## 11. Frontend setup from scratch

The repo has root-level React files but not a full Vite project ready to run out of the box. To run the frontend prototype:

### Option A: Create a new React app in a separate folder

From a terminal outside the backend project folder:

```powershell
npm create vite@latest cybreach-frontend -- --template react
cd cybreach-frontend
npm install
```

Then copy the following files from this project into the new app's `src/` folder:

- `App.jsx`
- `App.css`
- `index.css`
- `main.jsx`

Then run:

```powershell
npm run dev -- --host 0.0.0.0
```

Open the app in the browser at:

```text
http://localhost:5173
```

### Option B: Use the current project root as a React app

If you want to run the frontend files directly in the same repo, create a Vite app in the root folder or move the frontend files into a dedicated frontend folder. This repo is primarily a backend service, so the cleaner setup is to keep backend and frontend in separate folders.

---

## 12. Full project run order

If you want to start the entire stack from scratch, follow this order:

### Step 1 – Install tools
- Install Python
- Install Node.js + npm
- Install Docker Desktop

### Step 2 – Clone repo
```bash
git clone https://github.com/medhagupta1216/CyBreach-arena--Pod-delta.git
cd CyBreach-arena--Pod-delta
```

### Step 3 – Backend setup
```powershell
Copy-Item .env.example .env
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt psycopg2-binary
```

### Step 4 – Start infrastructure
```powershell
docker compose up -d redis redpanda redpanda-init postgres clickhouse
```

### Step 5 – Run backend
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Step 6 – Open Swagger
```text
http://127.0.0.1:8000/api/docs
```

### Step 7 – Optional React frontend
```powershell
npm create vite@latest cybreach-frontend -- --template react
cd cybreach-frontend
npm install
npm run dev -- --host 0.0.0.0
```

---

## 13. Useful commands

### Backend

```powershell
# activate environment
.\venv\Scripts\Activate.ps1

# run app
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# run tests
pytest
```

### Docker

```powershell
docker compose up -d

docker compose down

docker compose logs -f
```

### Frontend

```powershell
npm install
npm run dev -- --host 0.0.0.0
```

---

## 14. Troubleshooting

### Backend does not start
- Ensure your virtual environment is activated
- Ensure `pip install -r requirements.txt` completed successfully
- Ensure Docker services are running
- Check `.env` has valid values

### Redis connection fails
- Start Redis with:

```powershell
docker compose up -d redis
```

### Kafka / Redpanda fails
- Start the Redpanda services:

```powershell
docker compose up -d redpanda redpanda-init
```

### Frontend does not render
- Ensure Node.js is installed
- Run `npm install` in the frontend folder
- Ensure Vite is running on the expected port (`5173` by default)

---

## 15. Project notes

- This repository is primarily a backend service and integration platform.
- The frontend files in the root are meant as UI prototypes or reference assets.
- The real runtime for the service is the FastAPI backend under `app/`.
- For full end-to-end event testing, refer to `INTEGRATION_RUNBOOK.md`.

---

## 16. Quick reference

```text
Backend URL:         http://127.0.0.1:8000
Docs:                http://127.0.0.1:8000/api/docs
Health:              http://127.0.0.1:8000/api/v1/health
Integration health:  http://127.0.0.1:8000/api/v1/integration/health
Frontend dev:        http://localhost:5173
Redis:               localhost:6379
Redpanda:            localhost:19092
Postgres:            localhost:5432
```

This gives you a complete from-scratch setup for the project, including backend, APIs, notification flow, integration services, and frontend prototype startup.

