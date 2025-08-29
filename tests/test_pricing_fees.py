import sys
from pathlib import Path

# Ensure 'app' package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import config
from app.pricing import default_fees, fees_from_settings


def test_default_fees_matches_config():
    fees = default_fees()
    assert fees.buy_total == config.BROKER_BUY
    assert fees.sell_total == config.SALES_TAX + config.BROKER_SELL + config.RELIST_HAIRCUT


def test_fees_from_settings_overrides():
    settings = {
        "BROKER_BUY": 0.01,
        "SALES_TAX": 0.02,
        "BROKER_SELL": 0.03,
        "RELIST_HAIRCUT": 0.04,
    }
    fees = fees_from_settings(settings)
    assert fees.buy_total == settings["BROKER_BUY"]
    assert fees.sell_total == settings["SALES_TAX"] + settings["BROKER_SELL"] + settings["RELIST_HAIRCUT"]
