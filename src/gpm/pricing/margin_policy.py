from decimal import Decimal

DEFAULT_MARGIN_POLICY: dict = {
    "low_margin": Decimal("0.12"),
    "target_margin": Decimal("0.20"),
    "premium_margin": Decimal("0.32"),
}
