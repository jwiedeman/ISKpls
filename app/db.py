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

CREATE TABLE IF NOT EXISTS types (
  type_id INTEGER PRIMARY KEY,
  name TEXT,
  group_id INTEGER
);

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
