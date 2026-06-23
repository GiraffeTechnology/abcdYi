from decimal import Decimal
from typing import Any


class PriceNormalizer:
    """Extracts a usable price from a sample given a target quantity."""

    def effective_price(self, sample: Any, target_quantity: Decimal | None) -> Decimal | None:
        ladder = None
        price_min = None
        price_max = None

        if hasattr(sample, "ladder_prices"):
            ladder = sample.ladder_prices
        elif isinstance(sample, dict):
            ladder = sample.get("ladder_prices")

        if hasattr(sample, "price_min"):
            price_min = sample.price_min
        elif isinstance(sample, dict):
            price_min = sample.get("price_min")

        if hasattr(sample, "price_max"):
            price_max = sample.price_max
        elif isinstance(sample, dict):
            price_max = sample.get("price_max")

        if ladder and target_quantity is not None:
            selected = None
            for tier in sorted(ladder, key=lambda t: t.get("min_qty", 0) if isinstance(t, dict) else t["min_qty"]):
                min_qty = Decimal(str(tier.get("min_qty", 0) if isinstance(tier, dict) else tier["min_qty"]))
                if target_quantity >= min_qty:
                    selected = Decimal(str(tier.get("price", 0) if isinstance(tier, dict) else tier["price"]))
            if selected is not None:
                return selected

        if price_min is not None and price_max is not None:
            return (Decimal(str(price_min)) + Decimal(str(price_max))) / Decimal("2")
        if price_min is not None:
            return Decimal(str(price_min))
        if price_max is not None:
            return Decimal(str(price_max))
        return None
