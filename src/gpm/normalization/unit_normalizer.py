from decimal import Decimal


class UnitNormalizer:
    """Normalizes quantity units for price comparisons."""

    UNIT_ALIASES: dict[str, str] = {
        "pcs": "piece",
        "pc": "piece",
        "pieces": "piece",
        "件": "piece",
        "条": "piece",
    }

    def normalize_unit(self, unit: str) -> str:
        return self.UNIT_ALIASES.get(unit.lower().strip(), unit.lower().strip())

    def are_comparable_units(self, unit_a: str, unit_b: str) -> bool:
        return self.normalize_unit(unit_a) == self.normalize_unit(unit_b)
