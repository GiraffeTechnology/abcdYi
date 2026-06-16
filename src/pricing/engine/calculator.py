"""
Deterministic pricing calculation engine.
Pure Python — no LLM calls, no AI inference, no estimations.
Identical inputs always produce identical outputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
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


class LeadTimeRelation(str, Enum):
    PARALLEL = "parallel"      # 并联 — concurrent with peers in same phase
    SEQUENTIAL = "sequential"  # 串联 — sequential, after previous phase completes


# ─── Garment phase reference ──────────────────────────────────────────────────
# Phase number controls execution ORDER (lower = runs first).
# Within a phase: PARALLEL items → max(days), SEQUENTIAL items → sum(days).
# Phases are summed in ascending order to get total lead time.
#
# Simple garment defaults (衬衫 / T恤):
#   1 → 采购 (procurement): fabric + accessories in parallel
#   2 → 生产 (production):  cutting + sewing
#   3 → 工艺 (process):     embroidery / printing on finished garment
#   4 → 包装 (packaging)
#
# Complex garment example (牛仔裤):
#   1 → 采购 (procurement)
#   2 → 前工艺 (pre-process): enzyme/stone wash on raw fabric
#   3 → 生产 (production):    cutting + sewing
#   4 → 后工艺 (post-process): embroidery, distressing, rivets
#   5 → 包装 (packaging)
#
# Assign phase integers to match the actual manufacturing sequence for the
# specific product. The constants below are defaults for the simple case only.
PHASE_PROCUREMENT = 1
PHASE_PRODUCTION  = 2   # 生产 — before process for most garments
PHASE_PROCESS     = 3   # 工艺 — after production for most garments
PHASE_PACKAGING   = 4


@dataclass
class LeadTimeItem:
    name: str
    days: int
    relation: LeadTimeRelation   # parallel or sequential
    phase: int                   # phase number (determines ordering)


@dataclass
class LeadTimeInput:
    items: list[LeadTimeItem] = field(default_factory=list)


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
    Phase-based critical path calculator.

    Within each phase:
      - all PARALLEL items → take max(days)
      - all SEQUENTIAL items → sum(days)
      - phase_duration = max(parallel) + sum(sequential)

    Total = sum of phase_durations across phases in ascending phase order.
    """

    def calculate(self, inp: LeadTimeInput) -> int:
        if not inp.items:
            raise MissingPricingDataError("LeadTimeInput has no items")
        phase_map: dict[int, list[LeadTimeItem]] = {}
        for item in inp.items:
            phase_map.setdefault(item.phase, []).append(item)
        total = 0
        for phase_num in sorted(phase_map.keys()):
            items = phase_map[phase_num]
            parallel = [i.days for i in items if i.relation == LeadTimeRelation.PARALLEL]
            sequential = [i.days for i in items if i.relation == LeadTimeRelation.SEQUENTIAL]
            phase_duration = (max(parallel) if parallel else 0) + sum(sequential)
            total += phase_duration
        return total


def _require(value: object, field_name: str) -> None:
    if value is None:
        raise MissingPricingDataError(
            f"缺少 {field_name} 数据，无法计算报价。请录入后重试。"
        )
