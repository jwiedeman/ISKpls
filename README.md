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

1. Ensure Python 3.11+ is installed.
2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install requests pandas matplotlib python-dotenv
   ```
3. Initialize the database and seed market types:

   ```bash
   python -c "from app.db import init_db; init_db()"
   python -c "from app.types_sync import seed_region_types; seed_region_types()"
   ```
4. (Optional) load trend data and fetch Jita order snapshots:

   ```bash
   python -c "from app.trends import refresh_trends; refresh_trends()"
   python -c "from app.scheduler import fill_queue_from_trends, run_tick; fill_queue_from_trends(); run_tick()"
   ```
5. Provide the following environment variables (either export them or place them in a `.env` file):

   - `EVE_CLIENT_ID` and `EVE_CLIENT_SECRET` – from your EVE developer application
   - `CHAR_ID` – your character's ID

   Then run the character sync:

   ```bash
   python -m app.run_character_sync
   ```

   The first run will open a browser window for authorization and cache the
   refresh token in `token.json`.

Run `python -m py_compile $(git ls-files '*.py')` to verify syntax.

See `INSTRUCTIONS.md` for more details.
