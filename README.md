# VulnHawk Item Service

This project collects EVE Online market data for Jita 4-4 and tracks
personal trading performance using a local SQLite database.

Features:
- OAuth helpers for authenticated character access
- SQLite schema for wallet, orders, assets and market snapshots
- Region type seeding and Jita order snapshots
- Trend calculations and scheduling helpers
- Portfolio valuation and P/L plots

## Getting Started

### Prerequisites
- Python 3.11 or newer
- EVE Online developer application credentials
- Character ID for the account you want to track

### Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install requests pandas matplotlib python-dotenv
```

### Database Initialization
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
