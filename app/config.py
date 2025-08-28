import os

STATION_ID = 60003760  # Jita 4-4
REGION_ID = 10000002  # The Forge region
DATASOURCE = "tranquility"

# Fee parameters (adjust for structure vs NPC)
VENUE = "npc"  # or "structure"
SALES_TAX = 0.075 * 0.45  # Accounting V 2025
BROKER_BUY = 0.01 if VENUE == "npc" else 0.005
BROKER_SELL = BROKER_BUY
RELIST_HAIRCUT = 0.002

MOM_THRESHOLD = 0.12
MIN_DAYS_TRADED = 26
MIN_DAILY_VOL = 100
SPREAD_BUFFER = 0.02
SNIPE_EPSILON = 0.002
# Z-score threshold for anomaly-based snipes
SNIPE_Z = 3.0
# Minimum percentage drop from rolling median for anomaly detection
SNIPE_DELTA = 0.10

# Maximum age of market snapshots (in milliseconds) to consider "fresh"
# for recommendations. Can be overridden via the ``REC_FRESH_MS``
# environment variable.
REC_FRESH_MS = int(os.getenv("REC_FRESH_MS", 30 * 60 * 1000))
