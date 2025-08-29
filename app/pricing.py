from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Tuple, Optional, Dict, Mapping
from .ticks import tick as default_tick

@dataclass
class Fees:
    """Aggregate trading fees for buy and sell sides."""
    buy_total: float
    sell_total: float


def default_fees() -> Fees:
    """Return :class:`Fees` constructed from static config constants.

    Centralizes knowledge of trading fee parameters to avoid repeating
    ``config`` imports and manual arithmetic across modules.
    """
    from .config import BROKER_BUY, SALES_TAX, BROKER_SELL, RELIST_HAIRCUT

    return Fees(
        buy_total=BROKER_BUY,
        sell_total=SALES_TAX + BROKER_SELL + RELIST_HAIRCUT,
    )


def fees_from_settings(settings: Mapping[str, float]) -> Fees:
    """Build a :class:`Fees` instance from a settings mapping."""
    return Fees(
        buy_total=settings["BROKER_BUY"],
        sell_total=settings["SALES_TAX"]
        + settings["BROKER_SELL"]
        + settings["RELIST_HAIRCUT"],
    )


def compute_profit(
    best_bid: float | None,
    best_ask: float | None,
    fees: Fees,
    tick: Callable[[float, str], float] = default_tick,
) -> Tuple[float, float]:
    """Return profit in ISK and percentage after ticks and fees.

    ``best_bid`` and ``best_ask`` are raw market prices. We first tick the ask
    down to compute our buy price and tick the bid up to compute our sell price.
    Fees are then applied to each side. Profit is floored at zero to avoid
    negative recommendations.
    """
    if best_bid is None or best_ask is None:
        return 0.0, 0.0
    buy = tick(best_ask, "down") * (1 + fees.buy_total)
    sell = tick(best_bid, "up") * (1 - fees.sell_total)
    profit_isk = max(0.0, sell - buy)
    profit_pct = profit_isk / buy if buy > 0 else 0.0
    return profit_isk, profit_pct


def deal_label(
    profit_pct: float,
    confidence: Optional[float] = None,
    thresholds: Optional[Dict[str, float]] = None,
) -> str:
    """Classify a deal based on profit percentage and confidence."""
    c = confidence if confidence is not None else 0.5
    th = thresholds or {"great_pct": 0.08, "good_pct": 0.04, "neutral_pct": 0.01}
    if profit_pct >= th.get("great_pct", 0.08) and c >= 0.6:
        return "Great"
    if profit_pct >= th.get("good_pct", 0.04) and c >= 0.4:
        return "Good"
    if profit_pct >= th.get("neutral_pct", 0.01):
        return "Neutral"
    return "Bad"
