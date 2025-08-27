# VulnHawk Item Service

This project collects EVE Online market data for Jita 4-4 and tracks
personal trading performance using a local SQLite database.

Features:
- OAuth helpers for authenticated character access
- SQLite schema for wallet, orders, assets and market snapshots
- Region type seeding and Jita order snapshots
- Trend calculations and scheduling helpers
- Portfolio valuation and P/L plots

Run `python -m py_compile $(git ls-files '*.py')` to verify syntax.
