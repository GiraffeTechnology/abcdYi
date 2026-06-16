"""
Benchmark validation layer — statistical checks only, no AI number generation.
Deviation grading and missing-process detection are pure code logic.
AI role (per spec §3.4): convert the already-computed grade into natural-language
explanation text for the operator — it does not decide pass/block outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional


class DeviationGrade(str, Enum):
    PASS = "pass"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    BLOCKED = "blocked"
    NO_BENCHMARK = "no_benchmark"


@dataclass
class BenchmarkRecord:
    avg_price: Optional[Decimal]
    sample_size: int
    confidence_note: Optional[str] = None


@dataclass(frozen=True)
class DeviationResult:
    grade: DeviationGrade
    deviation_rate: Optional[Decimal]
    avg_price: Optional[Decimal]
    sample_size: int
    message: str


@dataclass(frozen=True)
class ProcessNormAlert:
    process_id: str
    process_name: str
    occurrence_rate: Decimal
    message: str


class BenchmarkValidator:
    """
    Grades a quoted unit price against a statistical benchmark.
    Output is the grade and a human-readable explanation.
    No benchmark numbers are generated or modified by this class.
    """

    MIN_SAMPLE_SIZE: int = 5

    def validate(
        self,
        quoted_price: Decimal,
        benchmark: Optional[BenchmarkRecord],
        threshold_tier1: Decimal,
        threshold_tier2: Decimal,
    ) -> DeviationResult:
        if benchmark is None or benchmark.avg_price is None:
            return DeviationResult(
                grade=DeviationGrade.NO_BENCHMARK,
                deviation_rate=None,
                avg_price=None,
                sample_size=0,
                message="暂无基准数据，无法进行偏离率校验，请人工判断。",
            )

        if benchmark.sample_size < self.MIN_SAMPLE_SIZE:
            note = (
                benchmark.confidence_note
                or f"样本量 {benchmark.sample_size} 条，低于最小阈值 {self.MIN_SAMPLE_SIZE} 条。"
            )
            return DeviationResult(
                grade=DeviationGrade.NO_BENCHMARK,
                deviation_rate=None,
                avg_price=benchmark.avg_price,
                sample_size=benchmark.sample_size,
                message=f"基准置信度不足：{note}",
            )

        deviation_rate = (quoted_price - benchmark.avg_price) / benchmark.avg_price

        if abs(deviation_rate) <= threshold_tier1:
            return DeviationResult(
                grade=DeviationGrade.PASS,
                deviation_rate=deviation_rate,
                avg_price=benchmark.avg_price,
                sample_size=benchmark.sample_size,
                message=(
                    f"报价偏离率 {deviation_rate:.1%}，在一级阈值 ±{threshold_tier1:.0%} 内，直接通过。"
                ),
            )

        if abs(deviation_rate) <= threshold_tier2:
            return DeviationResult(
                grade=DeviationGrade.REQUIRES_CONFIRMATION,
                deviation_rate=deviation_rate,
                avg_price=benchmark.avg_price,
                sample_size=benchmark.sample_size,
                message=(
                    f"报价偏离率 {deviation_rate:.1%}，超出一级阈值 ±{threshold_tier1:.0%}，"
                    f"未超出二级阈值 ±{threshold_tier2:.0%}，需人工确认后有效。"
                ),
            )

        return DeviationResult(
            grade=DeviationGrade.BLOCKED,
            deviation_rate=deviation_rate,
            avg_price=benchmark.avg_price,
            sample_size=benchmark.sample_size,
            message=(
                f"报价偏离率 {deviation_rate:.1%}，超出二级阈值 ±{threshold_tier2:.0%}，"
                f"强制人工复核，报价暂不有效。"
            ),
        )


class ProcessNormChecker:
    """
    Detects processes that are common for a category but missing from the current SKU.
    Pure set-intersection — no AI inference.
    """

    def __init__(self, occurrence_threshold: Decimal = Decimal("0.70")):
        self.occurrence_threshold = occurrence_threshold

    def check(
        self,
        category: str,
        sku_process_ids: set[str],
        category_norms: list[dict],
    ) -> list[ProcessNormAlert]:
        alerts = []
        for norm in category_norms:
            rate = Decimal(str(norm["occurrence_rate"]))
            if rate >= self.occurrence_threshold and norm["process_id"] not in sku_process_ids:
                name = norm.get("process_name", norm["process_id"])
                alerts.append(ProcessNormAlert(
                    process_id=norm["process_id"],
                    process_name=name,
                    occurrence_rate=rate,
                    message=(
                        f"该品类（{category}）历史 {rate:.0%} 的订单包含工艺「{name}」，"
                        f"当前 SKU 未录入，请确认是否漏录。"
                    ),
                ))
        return alerts


class BenchmarkRecalculator:
    """
    Recalculates statistical summary from raw price samples.
    Call after every N new records or on a weekly schedule.
    Each call should also write an AssetLayerVersionSnapshot for traceability.
    """

    def recalculate(self, price_samples: list[Decimal]) -> dict:
        n = len(price_samples)
        if n == 0:
            return {
                "sample_size": 0,
                "avg_price": None,
                "std_dev": None,
                "min_price": None,
                "max_price": None,
            }
        avg = sum(price_samples, Decimal("0")) / n
        variance = sum((p - avg) ** 2 for p in price_samples) / n
        std_dev = variance.sqrt()
        return {
            "sample_size": n,
            "avg_price": avg,
            "std_dev": std_dev,
            "min_price": min(price_samples),
            "max_price": max(price_samples),
        }
