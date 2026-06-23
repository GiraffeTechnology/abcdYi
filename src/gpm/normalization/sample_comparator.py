from decimal import Decimal
from typing import Any

from src.gpm.models.semantic_normalization import GPMSemanticNormalization

DEFAULT_THRESHOLD = Decimal("0.60")


class SampleComparator:
    """Filters samples based on semantic normalization scores."""

    def __init__(self, threshold: Decimal = DEFAULT_THRESHOLD) -> None:
        self._threshold = threshold

    def is_usable(self, sample: Any, normalization: GPMSemanticNormalization | None) -> bool:
        if normalization is None:
            return False
        usable = True
        if hasattr(sample, "usable_for_benchmark"):
            usable = sample.usable_for_benchmark
        elif isinstance(sample, dict):
            usable = sample.get("usable_for_benchmark", True)
        if not usable:
            return False
        return normalization.comparability_score >= self._threshold

    def filter_usable(
        self,
        samples: list[Any],
        normalizations: list[GPMSemanticNormalization],
    ) -> list[tuple[Any, GPMSemanticNormalization]]:
        norm_by_id = {n.sample_id: n for n in normalizations}
        result = []
        for sample in samples:
            sid = sample.id if hasattr(sample, "id") else sample.get("id")
            norm = norm_by_id.get(str(sid))
            if self.is_usable(sample, norm):
                result.append((sample, norm))
        return result
