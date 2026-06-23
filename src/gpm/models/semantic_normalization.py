from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class GPMSemanticNormalization:
    sample_id: str
    is_comparable: bool
    comparability_score: Decimal
    reason: str
    normalized_product_type: str | None = None
    normalized_material: str | None = None
    normalized_process_tags: list[str] = field(default_factory=list)
    customization_supported: bool | None = None

    def __post_init__(self) -> None:
        score = Decimal(str(self.comparability_score))
        if not (Decimal("0") <= score <= Decimal("1")):
            raise ValueError(
                f"comparability_score must be between 0 and 1, got {score}"
            )
        self.comparability_score = score
