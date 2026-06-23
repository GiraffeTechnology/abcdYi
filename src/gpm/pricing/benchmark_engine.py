from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from src.gpm.models.benchmark_snapshot import GPMBenchmarkSnapshot
from src.gpm.models.semantic_normalization import GPMSemanticNormalization
from src.gpm.normalization.sample_comparator import SampleComparator
from src.gpm.normalization.price_normalizer import PriceNormalizer


class BenchmarkEngine:
    def __init__(self) -> None:
        self._comparator = SampleComparator()
        self._price_normalizer = PriceNormalizer()

    def build_benchmark(
        self,
        requirement: dict,
        samples: list[Any],
        normalizations: list[GPMSemanticNormalization],
    ) -> GPMBenchmarkSnapshot:
        target_qty = requirement.get("quantity")
        if target_qty is not None:
            target_qty = Decimal(str(target_qty))

        usable_pairs = self._comparator.filter_usable(samples, normalizations)
        excluded = len(samples) - len(usable_pairs)

        prices: list[Decimal] = []
        timestamps: list[datetime] = []

        for sample, norm in usable_pairs:
            price = self._price_normalizer.effective_price(sample, target_qty)
            if price is None:
                excluded += 1
                continue
            prices.append(price)

            for attr in ("captured_at", "observed_at"):
                ts = getattr(sample, attr, None) or (sample.get(attr) if isinstance(sample, dict) else None)
                if ts is not None:
                    timestamps.append(ts)
                    break

        prices.sort()
        n = len(prices)

        benchmark_low = None
        benchmark_median = None
        benchmark_high = None
        weighted_median = None

        if n > 0:
            benchmark_low = self._percentile(prices, 25)
            benchmark_median = self._percentile(prices, 50)
            benchmark_high = self._percentile(prices, 75)
            weighted_median = benchmark_median

        if n >= 20:
            confidence_level = "high"
            confidence_reason = f"{n} comparable samples — high confidence."
        elif n >= 10:
            confidence_level = "medium"
            confidence_reason = f"{n} comparable samples — medium confidence."
        else:
            confidence_level = "low"
            confidence_reason = f"Only {n} comparable samples — low confidence."

        norm_product_type = None
        norm_material = None
        norm_process_tags: list[str] = []
        if usable_pairs:
            _, first_norm = usable_pairs[0]
            norm_product_type = first_norm.normalized_product_type
            norm_material = first_norm.normalized_material
            norm_process_tags = first_norm.normalized_process_tags

        return GPMBenchmarkSnapshot(
            query_keyword=requirement.get("product", ""),
            source_platform=requirement.get("source_platform", "mock"),
            sample_count=len(samples),
            comparable_sample_count=n,
            excluded_sample_count=excluded,
            confidence_level=confidence_level,
            confidence_reason=confidence_reason,
            normalized_product_type=norm_product_type,
            normalized_material=norm_material,
            normalized_process_tags=norm_process_tags,
            benchmark_low=benchmark_low,
            benchmark_median=benchmark_median,
            benchmark_high=benchmark_high,
            weighted_median=weighted_median,
            target_quantity=target_qty,
            target_quantity_unit=requirement.get("unit", "piece"),
            captured_from=min(timestamps) if timestamps else None,
            captured_to=max(timestamps) if timestamps else None,
            requirement_id=requirement.get("id"),
        )

    @staticmethod
    def _percentile(sorted_values: list[Decimal], pct: int) -> Decimal:
        n = len(sorted_values)
        if n == 0:
            raise ValueError("Empty list")
        if n == 1:
            return sorted_values[0]
        idx = (pct / 100) * (n - 1)
        lower = int(idx)
        upper = lower + 1
        if upper >= n:
            return sorted_values[lower]
        frac = Decimal(str(idx - lower))
        return sorted_values[lower] + frac * (sorted_values[upper] - sorted_values[lower])
