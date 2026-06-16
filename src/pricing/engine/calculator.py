"""
Deterministic pricing calculation engine.
Pure Python — no LLM calls, no AI inference, no estimations.
Identical inputs always produce identical outputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


class MissingPricingDataError(ValueError):
    """Raised when required pricing data is absent. No fallback, no estimation allowed."""


@dataclass
class ProcessLineItem:
    process_id: str
    process_name: str
    unit_price: Decimal
    quantity: Decimal
    supplier: str
    quote_date: str


@dataclass
class PricingInput:
    sku_id: str
    sku_name: str
    fabric_unit_price: Optional[Decimal] = None
    fabric_quantity: Optional[Decimal] = None
    # List of (unit_price, quantity) tuples — one per accessory line
    accessory_lines: list[tuple[Decimal, Decimal]] = field(default_factory=list)
    process_lines: list[ProcessLineItem] = field(default_factory=list)
    packaging_unit_price: Optional[Decimal] = None
    packaging_quantity: Optional[Decimal] = None
    loss_rate: Optional[Decimal] = None
    labor_unit_price: Optional[Decimal] = None
    labor_hours: Optional[Decimal] = None
    overhead_rate: Optional[Decimal] = None
    profit_rate: Optional[Decimal] = None


@dataclass(frozen=True)
class PricingBreakdown:
    fabric_cost: Decimal
    accessory_cost: Decimal
    process_cost: Decimal
    packaging_cost: Decimal
    loss_cost: Decimal
    labor_cost: Decimal
    subtotal: Decimal
    overhead_fee: Decimal
    total_cost: Decimal
    quoted_price: Decimal


@dataclass
class LeadTimeInput:
    fabric_lead_time: Optional[int] = None
    accessory_lead_times: list[int] = field(default_factory=list)
    process_lead_times: list[int] = field(default_factory=list)
    packaging_lead_time: Optional[int] = None
    production_days: Optional[int] = None


class PricingEngine:
    """
    Deterministic pricing engine.
    Raises MissingPricingDataError for any absent required field.
    No network calls, no randomness, no LLM interaction.
    """

    def calculate(self, inp: PricingInput) -> PricingBreakdown:
        _require(inp.fabric_unit_price, "fabric_unit_price（面料单价）")
        _require(inp.fabric_quantity, "fabric_quantity（面料用量）")
        _require(inp.loss_rate, "loss_rate（损耗率）")
        _require(inp.labor_unit_price, "labor_unit_price（人工单价）")
        _require(inp.labor_hours, "labor_hours（工时）")
        _require(inp.overhead_rate, "overhead_rate（管理费率）")
        _require(inp.profit_rate, "profit_rate（利润率）")
        _require(inp.packaging_unit_price, "packaging_unit_price（包装单价）")
        _require(inp.packaging_quantity, "packaging_quantity（包装数量）")

        fabric_cost: Decimal = inp.fabric_unit_price * inp.fabric_quantity  # type: ignore[operator]

        accessory_cost = Decimal("0")
        for unit_price, qty in inp.accessory_lines:
            accessory_cost += unit_price * qty

        process_cost = Decimal("0")
        for line in inp.process_lines:
            process_cost += line.unit_price * line.quantity

        packaging_cost: Decimal = inp.packaging_unit_price * inp.packaging_quantity  # type: ignore[operator]
        loss_cost: Decimal = (fabric_cost + accessory_cost) * inp.loss_rate  # type: ignore[operator]
        labor_cost: Decimal = inp.labor_unit_price * inp.labor_hours  # type: ignore[operator]

        subtotal = fabric_cost + accessory_cost + process_cost + packaging_cost + loss_cost + labor_cost
        overhead_fee: Decimal = subtotal * inp.overhead_rate  # type: ignore[operator]
        total_cost = subtotal + overhead_fee
        quoted_price: Decimal = total_cost * (Decimal("1") + inp.profit_rate)  # type: ignore[operator]

        return PricingBreakdown(
            fabric_cost=fabric_cost,
            accessory_cost=accessory_cost,
            process_cost=process_cost,
            packaging_cost=packaging_cost,
            loss_cost=loss_cost,
            labor_cost=labor_cost,
            subtotal=subtotal,
            overhead_fee=overhead_fee,
            total_cost=total_cost,
            quoted_price=quoted_price,
        )


class LeadTimeEngine:
    """
    Deterministic lead time aggregation.

    Sequential phases:
      Phase 1 (concurrent procurement): max(fabric, accessories)
      Phase 2 (sequential, needs fabric): sum of process lead times
      Phase 3 (sequential): packaging lead time
      Phase 4 (sequential): production days
    Total = phase1 + phase2 + phase3 + phase4
    """

    def calculate(self, inp: LeadTimeInput) -> int:
        _require(inp.fabric_lead_time, "fabric_lead_time（面料 lead time）")
        _require(inp.production_days, "production_days（生产天数）")

        procurement_times: list[int] = [inp.fabric_lead_time]  # type: ignore[list-item]
        procurement_times.extend(inp.accessory_lead_times)
        phase1 = max(procurement_times)

        phase2 = sum(inp.process_lead_times)

        phase3 = inp.packaging_lead_time if inp.packaging_lead_time is not None else 0

        return phase1 + phase2 + phase3 + inp.production_days  # type: ignore[operator]


def _require(value: object, field_name: str) -> None:
    if value is None:
        raise MissingPricingDataError(
            f"缺少 {field_name} 数据，无法计算报价。请录入后重试。"
        )
