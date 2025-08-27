# Start Instructions

This guide walks through setting up the VulnHawk Item Service and collecting data.

## Prerequisites
- Python 3.11 or newer
- EVE Online developer application credentials and a character access token

## Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install requests pandas matplotlib
```

## Database Initialization
```bash
python -c "from app.db import init_db; init_db()"
```

## Seed Region Types
```bash
python -c "from app.types_sync import seed_region_types; seed_region_types()"
```

## Fetch Market Trends and Order Snapshots
```bash
python -c "from app.trends import refresh_trends; refresh_trends()"
python -c "from app.scheduler import fill_queue_from_trends, run_tick; fill_queue_from_trends(); run_tick()"
```

## Sync Character Data
Set `CHAR_ID` and `TOKEN` in `app/run_character_sync.py` then run:
```bash
python -m app.run_character_sync
```
This synchronizes wallet, orders, assets and prints a portfolio snapshot.
