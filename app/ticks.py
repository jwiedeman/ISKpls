from __future__ import annotations
import math


def tick_size(price: float) -> float:
    """Return the market tick size for a given price."""
    if price < 0:
        raise ValueError("price must be non-negative")
    if price < 100:
        return 0.01
    if price < 1000:
        return 0.1
    if price < 10_000:
        return 1.0
    if price < 100_000:
        return 10.0
    if price < 1_000_000:
        return 100.0
    if price < 10_000_000:
        return 1_000.0
    if price < 100_000_000:
        return 10_000.0
    if price < 1_000_000_000:
        return 100_000.0
    if price < 10_000_000_000:
        return 1_000_000.0
    if price < 100_000_000_000:
        return 10_000_000.0
    return 100_000_000.0


def tick(price: float, direction: str) -> float:
    """Move ``price`` one tick in ``direction`` ('up' or 'down')."""
    size = tick_size(price)
    base = math.floor(price / size) * size
    if direction == "up":
        return base + size
    if direction == "down":
        return max(0.0, base - size)
    raise ValueError("direction must be 'up' or 'down'")
