import sqlite3
import pathlib

DB_PATH = pathlib.Path("eve_trader.sqlite3")

DDL = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS wallet_snapshots (
  ts_utc TEXT PRIMARY KEY,
  balance REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS wallet_journal (
  id INTEGER PRIMARY KEY,
  ts_utc TEXT NOT NULL,
  amount REAL NOT NULL,
  balance REAL,
  ref_type TEXT,
  context_id INTEGER,
  context_id_type TEXT,
  first_party_id INTEGER,
  second_party_id INTEGER,
  description TEXT
);

CREATE INDEX IF NOT EXISTS idx_journal_ts ON wallet_journal(ts_utc);

CREATE TABLE IF NOT EXISTS wallet_transactions (
  transaction_id INTEGER PRIMARY KEY,
  ts_utc TEXT NOT NULL,
  client_id INTEGER,
  location_id INTEGER,
  type_id INTEGER,
  quantity INTEGER,
  unit_price REAL,
  is_buy INTEGER,
  journal_ref_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tx_type_ts ON wallet_transactions(type_id, ts_utc);

CREATE TABLE IF NOT EXISTS char_orders (
  order_id INTEGER PRIMARY KEY,
  is_buy INTEGER,
  region_id INTEGER,
  location_id INTEGER,
  type_id INTEGER,
  price REAL,
  volume_total INTEGER,
  volume_remain INTEGER,
  issued TEXT,
  duration INTEGER,
  range TEXT,
  min_volume INTEGER,
  escrow REAL,
  last_seen TEXT,
  state TEXT DEFAULT 'open'
);

CREATE INDEX IF NOT EXISTS idx_char_orders_type ON char_orders(type_id);

CREATE TABLE IF NOT EXISTS assets (
  item_id INTEGER PRIMARY KEY,
  type_id INTEGER,
  quantity INTEGER,
  is_singleton INTEGER,
  location_id INTEGER,
  location_type TEXT,
  location_flag TEXT,
  updated TEXT
);

CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type_id);

CREATE TABLE IF NOT EXISTS types (
  type_id INTEGER PRIMARY KEY,
  name TEXT,
  group_id INTEGER,
  category_id INTEGER,
  volume REAL,
  meta_level REAL,
  market_group_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_types_name ON types(name);

CREATE TABLE IF NOT EXISTS type_valuations (
  type_id INTEGER PRIMARY KEY,
  quicksell_bid REAL,
  mark_ask REAL,
  updated TEXT
);

CREATE TABLE IF NOT EXISTS portfolio_daily (
  day TEXT PRIMARY KEY,
  wallet_balance REAL,
  buy_escrow REAL,
  sell_gross REAL,
  inventory_quicksell REAL,
  inventory_mark REAL,
  nav_quicksell REAL,
  nav_mark REAL
);

CREATE TABLE IF NOT EXISTS region_types (
  region_id INTEGER NOT NULL,
  type_id INTEGER NOT NULL,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  PRIMARY KEY (region_id, type_id)
);

CREATE TABLE IF NOT EXISTS type_status (
  type_id INTEGER PRIMARY KEY,
  last_orders_refresh TEXT,
  next_refresh TEXT,
  tier TEXT,
  update_interval_min INTEGER
);

CREATE TABLE IF NOT EXISTS market_snapshots (
  ts_utc TEXT NOT NULL,
  type_id INTEGER NOT NULL,
  best_bid REAL,
  best_ask REAL,
  bid_count INTEGER,
  ask_count INTEGER,
  jita_bid_units INTEGER,
  jita_ask_units INTEGER,
  PRIMARY KEY (ts_utc, type_id)
);

CREATE INDEX IF NOT EXISTS idx_market_snapshots_type ON market_snapshots(type_id);

CREATE TABLE IF NOT EXISTS type_trends (
  type_id INTEGER PRIMARY KEY,
  last_history_ts TEXT,
  mom_pct REAL,
  vol_30d_avg REAL,
  vol_prev30_avg REAL
);

CREATE TABLE IF NOT EXISTS realized_trades (
  trade_id TEXT PRIMARY KEY,
  ts_utc TEXT NOT NULL,
  type_id INTEGER NOT NULL,
  qty INTEGER NOT NULL,
  sell_unit_price REAL NOT NULL,
  cost_total REAL NOT NULL,
  tax REAL NOT NULL,
  broker_fee REAL NOT NULL,
  pnl REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_cost_basis (
  type_id INTEGER PRIMARY KEY,
  remaining_qty INTEGER,
  avg_cost REAL,
  updated TEXT
);

CREATE TABLE IF NOT EXISTS recommendations (
  type_id INTEGER NOT NULL,
  station_id INTEGER NOT NULL,
  ts_utc TEXT NOT NULL,
  net_pct REAL,
  uplift_mom REAL,
  daily_capacity REAL,
  rationale_json TEXT
);

-- Remove duplicates before creating unique index
DELETE FROM recommendations
WHERE rowid IN (
  SELECT a.rowid FROM recommendations a
  JOIN recommendations b
    ON a.type_id = b.type_id
   AND a.station_id = b.station_id
   AND a.rowid > b.rowid
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_recs_type_station ON recommendations(type_id, station_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_type ON recommendations(type_id);
CREATE INDEX IF NOT EXISTS idx_recs_station ON recommendations(station_id);

CREATE TABLE IF NOT EXISTS watchlist (
  type_id INTEGER PRIMARY KEY,
  added_ts TEXT NOT NULL,
  note TEXT
);

CREATE TABLE IF NOT EXISTS jobs_history (
  name TEXT NOT NULL,
  ts_utc TEXT NOT NULL,
  ok INTEGER NOT NULL,
  details_json TEXT,
  PRIMARY KEY (name, ts_utc)
);

CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""


def connect():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys=ON;")
    return con


def init_db():
    con = connect()
    con.executescript(DDL)
    con.commit()
    return con
