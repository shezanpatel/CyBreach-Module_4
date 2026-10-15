# CyBreach Arena – Frontend

React + Vite frontend for CyBreach Arena (Pod Delta).

## Run locally

Requires Node.js 18+.

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Any email and password logs in (demo login).

## Build

```
npm run build      # outputs to frontend/dist
npm run preview    # serves the built app
```

## Notes

- The UI currently uses built-in sample data (agents, leaderboard, transactions). It does not call the backend API yet.
- The backend runs separately on http://127.0.0.1:8000 (see the root README). Its CORS settings already allow http://localhost:5173.
