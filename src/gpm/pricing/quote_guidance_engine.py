from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from src.gpm.models.benchmark_snapshot import GPMBenchmarkSnapshot
from src.gpm.models.quote_guidance import GPMQuoteGuidance
from src.gpm.pricing.margin_policy import DEFAULT_MARGIN_POLICY

TWO_PLACES = Decimal("0.01")


class QuoteGuidanceEngine:
    def generate_guidance(
        self,
        requirement: dict,
        supplier_quote: dict,
        benchmark: GPMBenchmarkSnapshot,
        margin_policy: dict | None = None,
    ) -> GPMQuoteGuidance:
        policy = margin_policy or DEFAULT_MARGIN_POLICY

        quote_price = Decimal(str(supplier_quote["unit_price"]))
        currency = supplier_quote.get("currency", "CNY")
        unit = supplier_quote.get("unit", "piece")
        moq_raw = supplier_quote.get("moq")
        supplier_id = supplier_quote.get("supplier_id")
        moq = Decimal(str(moq_raw)) if moq_raw is not None else None

        target_qty_raw = requirement.get("quantity")
        target_qty = Decimal(str(target_qty_raw)) if target_qty_raw is not None else None

        risk_flags: list[str] = []

        low = benchmark.benchmark_low
        median = benchmark.benchmark_median
        high = benchmark.benchmark_high
        confidence = benchmark.confidence_level

        if confidence == "low" or low is None or median is None or high is None:
            position = "insufficient_data"
            recommendation = "human_review_required"
        elif quote_price < low * Decimal("0.75"):
            position = "below_market"
            recommendation = "request_more_info"
            risk_flags.append("possible_quality_or_scope_mismatch")
        elif quote_price < low:
            position = "below_market"
            recommendation = "request_more_info"
        elif quote_price < median:
            position = "within_low_range"
            recommendation = "accept"
        elif quote_price <= high:
            position = "within_mid_range" if quote_price <= median + (high - median) / Decimal("2") else "within_high_range"
            recommendation = "negotiate"
        elif quote_price <= high * Decimal("1.15"):
            position = "above_market"
            recommendation = "negotiate"
        else:
            position = "above_market"
            recommendation = "reject"

        if moq is None:
            if recommendation not in ("human_review_required",):
                recommendation = "human_review_required"
            risk_flags.append("missing_supplier_moq")
        elif target_qty is not None and moq > target_qty:
            if recommendation == "accept":
                recommendation = "negotiate"
            risk_flags.append("moq_exceeds_target_quantity")

        low_m = Decimal(str(policy.get("low_margin", DEFAULT_MARGIN_POLICY["low_margin"])))
        mid_m = Decimal(str(policy.get("target_margin", DEFAULT_MARGIN_POLICY["target_margin"])))
        high_m = Decimal(str(policy.get("premium_margin", DEFAULT_MARGIN_POLICY["premium_margin"])))

        buyer_low = (quote_price * (1 + low_m)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        buyer_mid = (quote_price * (1 + mid_m)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        buyer_high = (quote_price * (1 + high_m)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        counter_price = None
        if recommendation in ("negotiate", "reject") and median is not None:
            counter_price = median.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        explanation_parts = [
            f"Supplier quote {quote_price} {currency}/{unit} is {position.replace('_', ' ')}.",
            f"Benchmark: low={low}, median={median}, high={high} (confidence={confidence}).",
            f"Recommendation: {recommendation}.",
        ]
        if risk_flags:
            explanation_parts.append(f"Risk flags: {', '.join(risk_flags)}.")

        return GPMQuoteGuidance(
            benchmark_snapshot_id=benchmark.id,
            requirement_id=requirement.get("id"),
            supplier_id=supplier_id,
            supplier_quote_price=quote_price,
            supplier_quote_currency=currency,
            supplier_quote_unit=unit,
            supplier_quote_moq=moq,
            supplier_quote_position=position,
            accept_recommendation=recommendation,
            recommended_counter_price=counter_price,
            recommended_buyer_quote_low=buyer_low,
            recommended_buyer_quote_mid=buyer_mid,
            recommended_buyer_quote_high=buyer_high,
            margin_policy={k: str(v) for k, v in policy.items()},
            risk_flags=risk_flags,
            explanation=" ".join(explanation_parts),
            human_approval_required=True,
        )
