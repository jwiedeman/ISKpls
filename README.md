# VulnHawk Item Service

This project collects EVE Online market data for Jita 4-4 and tracks
personal trading performance using a local SQLite database.

Features:
- OAuth helpers for authenticated character access
- SQLite schema for wallet, orders, assets and market snapshots
- Region type seeding and Jita order snapshots
- Trend calculations and scheduling helpers
- Portfolio valuation and P/L plots
- Cached type names in API responses

## Getting Started

### Prerequisites
- Python 3.11 or newer
- EVE Online developer application credentials
- Character ID for the account you want to track

### Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Database Initialization

The API service now ensures the SQLite schema exists on startup. If you need to
initialize the database manually (for example before running standalone
scripts) you can do so with:

```bash
python -c "from app.db import init_db; init_db()"
```

### Seed Region Types
```bash
python -c "from app.types_sync import seed_region_types; seed_region_types()"
```

### (Optional) Fetch Market Trends and Order Snapshots
```bash
python -c "from app.trends import refresh_trends; refresh_trends()"
python -c "from app.scheduler import fill_queue_from_trends, run_tick; fill_queue_from_trends(); run_tick()"
```

### Sync Character Data
Provide environment variables `EVE_CLIENT_ID`, `EVE_CLIENT_SECRET` and `CHAR_ID`
(either export them or place them in a `.env` file), then run:

```bash
python -m app.run_character_sync
```

The first run opens a browser window to authorize and caches a refresh token in
`token.json`. Subsequent runs refresh automatically and synchronize wallet,
orders and assets while printing a portfolio snapshot.

Run `python -m py_compile $(git ls-files '*.py')` to verify syntax.

Run the unit tests to ensure everything works as expected:

```bash
pytest
```

### Local API Service
With the database initialized you can launch a small FastAPI service that exposes
status, settings and job triggers.

```bash
pip install fastapi uvicorn
uvicorn app.service:app --reload
```

The service provides endpoints such as:

- `GET /status` – recent job history
- `GET /settings` – current configuration with defaults
- `PUT /settings` – update configuration values
- `POST /jobs/recommendations/run` – rebuild recommendation table
- `POST /jobs/scheduler_tick/run` – process due market snapshots
- `GET /auth/status` – check whether SSO token is cached
- `POST /auth/connect` – initiate the EVE SSO flow
- Most responses include `type_name` alongside `type_id`

### Frontend UI

The `/ui` directory contains a small React + Tauri interface for interacting
with the service. To install dependencies and build the static assets:

```bash
cd ui
npm install
npm run lint
npm run build
```

`npm run dev` launches a hot-reload development server, while `npx tauri dev`
starts the desktop shell during development.

