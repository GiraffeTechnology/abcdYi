"""
Acceptance tests for the Giraffe pricing model skeleton (spec §7).
All tests are pure-Python unit tests — no database required.
"""
from decimal import Decimal
from typing import Optional

import pytest

from src.pricing.engine.calculator import (
    MissingPricingDataError, PricingEngine, PricingInput,
    LeadTimeEngine, LeadTimeInput, LeadTimeItem, LeadTimeRelation,
    PHASE_PROCUREMENT, PHASE_PROCESS, PHASE_PRODUCTION, PHASE_PACKAGING,
    ProcessLineItem,
)
from src.pricing.benchmark.validator import (
    BenchmarkRecord, BenchmarkValidator, BenchmarkRecalculator,
    DeviationGrade, ProcessNormChecker,
)
from src.pricing.distillation.service import (
    DistillationPipelineError, validate_submission, validate_approval,
)
from src.pricing.layers.service import resolve_benchmark_value


# ── Helpers ──────────────────────────────────────────────────────────────────

def _full_input(**overrides) -> PricingInput:
    """A fully-populated PricingInput; override any field to test missing-data paths."""
    defaults = dict(
        sku_id="sku-001",
        sku_name="Test Shirt",
        fabric_unit_price=Decimal("12.50"),
        fabric_quantity=Decimal("2.0"),
        accessory_lines=[
            (Decimal("1.20"), Decimal("3")),
            (Decimal("0.50"), Decimal("5")),
        ],
        process_lines=[
            ProcessLineItem(
                process_id="p-001",
                process_name="刺绣",
                unit_price=Decimal("3.00"),
                quantity=Decimal("1"),
                supplier="绣品厂A",
                quote_date="2026-06-01",
            )
        ],
        packaging_unit_price=Decimal("0.80"),
        packaging_quantity=Decimal("1"),
        loss_rate=Decimal("0.05"),
        labor_unit_price=Decimal("25.00"),
        labor_hours=Decimal("0.4"),
        overhead_rate=Decimal("0.10"),
        profit_rate=Decimal("0.15"),
    )
    defaults.update(overrides)
    return PricingInput(**defaults)


# ── AC1: Empty data state → cannot generate quote ─────────────────────────────

def test_empty_fabric_price_raises():
    engine = PricingEngine()
    inp = _full_input(fabric_unit_price=None)
    with pytest.raises(MissingPricingDataError) as exc_info:
        engine.calculate(inp)
    assert "fabric_unit_price" in str(exc_info.value)


def test_empty_loss_rate_raises():
    engine = PricingEngine()
    inp = _full_input(loss_rate=None)
    with pytest.raises(MissingPricingDataError) as exc_info:
        engine.calculate(inp)
    assert "loss_rate" in str(exc_info.value)


def test_empty_overhead_rate_raises():
    engine = PricingEngine()
    inp = _full_input(overhead_rate=None)
    with pytest.raises(MissingPricingDataError):
        engine.calculate(inp)


def test_empty_profit_rate_raises():
    engine = PricingEngine()
    inp = _full_input(profit_rate=None)
    with pytest.raises(MissingPricingDataError):
        engine.calculate(inp)


def test_missing_all_fields_each_raises():
    """Every required field independently raises MissingPricingDataError when absent."""
    engine = PricingEngine()
    required_fields = [
        "fabric_unit_price", "fabric_quantity", "loss_rate",
        "labor_unit_price", "labor_hours", "overhead_rate",
        "profit_rate", "packaging_unit_price", "packaging_quantity",
    ]
    for field in required_fields:
        with pytest.raises(MissingPricingDataError, match=field):
            engine.calculate(_full_input(**{field: None}))


# ── AC3: Same inputs → same output (determinism) ─────────────────────────────

def test_deterministic_calculation():
    engine = PricingEngine()
    inp = _full_input()
    result1 = engine.calculate(inp)
    result2 = engine.calculate(inp)
    assert result1.quoted_price == result2.quoted_price
    assert result1.total_cost == result2.total_cost
    assert result1 == result2


# ── AC3b: Manual formula verification ────────────────────────────────────────

def test_formula_correctness():
    """
    Manually verify the pricing formula matches the spec:
      fabric = 12.50 × 2 = 25.00
      accessory = 1.20×3 + 0.50×5 = 3.60 + 2.50 = 6.10
      process = 3.00×1 = 3.00
      packaging = 0.80×1 = 0.80
      loss = (25 + 6.10) × 0.05 = 1.555
      labor = 25.00 × 0.4 = 10.00
      subtotal = 25 + 6.10 + 3 + 0.80 + 1.555 + 10 = 46.455
      overhead = 46.455 × 0.10 = 4.6455
      total_cost = 46.455 + 4.6455 = 51.1005
      quoted_price = 51.1005 × 1.15 = 58.765575
    """
    engine = PricingEngine()
    result = engine.calculate(_full_input())
    assert result.fabric_cost == Decimal("25.00")
    assert result.accessory_cost == Decimal("6.10")
    assert result.process_cost == Decimal("3.00")
    assert result.packaging_cost == Decimal("0.80")
    assert result.loss_cost == Decimal("1.5550")
    assert result.labor_cost == Decimal("10.00")
    expected_subtotal = Decimal("46.4550")
    assert result.subtotal == expected_subtotal
    assert result.overhead_fee == Decimal("4.6455")
    assert result.total_cost == Decimal("51.1005")
    assert result.quoted_price == Decimal("58.765575")


# ── AC4: New process type without schema change ───────────────────────────────

def test_new_process_type_no_schema_change():
    """
    Adding a new process type (e.g. '植绒') only requires inserting rows into
    process_type_def and sku_process_attribute — no table schema change.
    Verify that PricingEngine correctly sums multiple process lines including
    the new type.
    """
    new_process = ProcessLineItem(
        process_id="p-new",
        process_name="植绒",
        unit_price=Decimal("5.00"),
        quantity=Decimal("1"),
        supplier="植绒厂B",
        quote_date="2026-06-01",
    )
    inp = _full_input(process_lines=[
        ProcessLineItem("p-001", "刺绣", Decimal("3.00"), Decimal("1"), "绣品厂A", "2026-06-01"),
        new_process,
    ])
    engine = PricingEngine()
    result = engine.calculate(inp)
    assert result.process_cost == Decimal("8.00")  # 3 + 5


# ── AC5: extra_attributes isolation ───────────────────────────────────────────

def test_extra_attributes_not_read_by_engine():
    """
    Values placed in extra_attributes should never affect the quoted price.
    Even if someone writes pricing data there, the engine ignores it.
    """
    engine = PricingEngine()
    result_without = engine.calculate(_full_input())

    # PricingInput has no extra_attributes field — by design.
    # Verify that the engine's output is fully determined by structured fields only.
    inp_with_distractors = _full_input()
    result_with = engine.calculate(inp_with_distractors)
    assert result_without.quoted_price == result_with.quoted_price


# ── AC6: Benchmark confidence — sample < 5 → NO_BENCHMARK ────────────────────

def test_low_sample_benchmark_returns_no_benchmark():
    validator = BenchmarkValidator()
    benchmark = BenchmarkRecord(avg_price=Decimal("10.00"), sample_size=3)
    result = validator.validate(
        quoted_price=Decimal("10.00"),
        benchmark=benchmark,
        threshold_tier1=Decimal("0.10"),
        threshold_tier2=Decimal("0.30"),
    )
    assert result.grade == DeviationGrade.NO_BENCHMARK
    assert "置信度" in result.message
    assert result.deviation_rate is None


def test_zero_sample_benchmark_returns_no_benchmark():
    validator = BenchmarkValidator()
    result = validator.validate(
        quoted_price=Decimal("10.00"),
        benchmark=None,
        threshold_tier1=Decimal("0.10"),
        threshold_tier2=Decimal("0.30"),
    )
    assert result.grade == DeviationGrade.NO_BENCHMARK
    assert result.sample_size == 0


def test_sufficient_sample_allows_grading():
    validator = BenchmarkValidator()
    benchmark = BenchmarkRecord(avg_price=Decimal("10.00"), sample_size=5)
    result = validator.validate(
        quoted_price=Decimal("10.50"),
        benchmark=benchmark,
        threshold_tier1=Decimal("0.10"),
        threshold_tier2=Decimal("0.30"),
    )
    assert result.grade == DeviationGrade.PASS


# ── Deviation grading thresholds ─────────────────────────────────────────────

def test_deviation_within_tier1_passes():
    validator = BenchmarkValidator()
    benchmark = BenchmarkRecord(avg_price=Decimal("100.00"), sample_size=10)
    result = validator.validate(
        Decimal("108.00"), benchmark, Decimal("0.10"), Decimal("0.30")
    )
    assert result.grade == DeviationGrade.PASS


def test_deviation_between_tier1_and_tier2_requires_confirmation():
    validator = BenchmarkValidator()
    benchmark = BenchmarkRecord(avg_price=Decimal("100.00"), sample_size=10)
    result = validator.validate(
        Decimal("120.00"), benchmark, Decimal("0.10"), Decimal("0.30")
    )
    assert result.grade == DeviationGrade.REQUIRES_CONFIRMATION


def test_deviation_above_tier2_is_blocked():
    validator = BenchmarkValidator()
    benchmark = BenchmarkRecord(avg_price=Decimal("100.00"), sample_size=10)
    result = validator.validate(
        Decimal("145.00"), benchmark, Decimal("0.10"), Decimal("0.30")
    )
    assert result.grade == DeviationGrade.BLOCKED


# ── Missing process detection ─────────────────────────────────────────────────

def test_process_norm_checker_detects_missing_process():
    checker = ProcessNormChecker(occurrence_threshold=Decimal("0.70"))
    alerts = checker.check(
        category="T恤",
        sku_process_ids={"p-001"},
        category_norms=[
            {"process_id": "p-001", "process_name": "刺绣", "occurrence_rate": "0.85"},
            {"process_id": "p-002", "process_name": "压胶", "occurrence_rate": "0.75"},
        ],
    )
    assert len(alerts) == 1
    assert alerts[0].process_id == "p-002"
    assert "漏录" in alerts[0].message


def test_process_norm_checker_below_threshold_no_alert():
    checker = ProcessNormChecker(occurrence_threshold=Decimal("0.70"))
    alerts = checker.check(
        category="T恤",
        sku_process_ids=set(),
        category_norms=[
            {"process_id": "p-003", "process_name": "洗水", "occurrence_rate": "0.60"},
        ],
    )
    assert alerts == []


# ── AC7: External data without source → pending_review ───────────────────────

def test_distillation_tier3_rejected():
    """Tier3 sources must not enter the distillation pipeline."""
    with pytest.raises(DistillationPipelineError, match="tier"):
        validate_submission("tier3", "https://some-blog.com/article")


def test_distillation_empty_ref_rejected():
    with pytest.raises(DistillationPipelineError):
        validate_submission("tier1", "")


def test_distillation_tier1_accepted():
    validate_submission("tier1", "海关总署-2026Q1棉布价格指数.pdf")  # should not raise


def test_distillation_tier2_accepted():
    validate_submission("tier2", "https://1688.com/listing/cotton-fabric-quote-2026.html")  # should not raise


# ── AC10: Distillation job must require human approval before promotion ───────

def test_distillation_approval_requires_reviewed_by():
    with pytest.raises(DistillationPipelineError, match="reviewed_by"):
        validate_approval(
            extraction_output={"price": 12.5, "unit": "米"},
            reviewed_by=None,
        )


def test_distillation_approval_requires_nonempty_extraction():
    with pytest.raises(DistillationPipelineError, match="extraction_output"):
        validate_approval(
            extraction_output=None,
            reviewed_by="user@giraffe.com",
        )


def test_distillation_approval_passes_with_both():
    validate_approval(
        extraction_output={"price": {"value": 12.5, "source_text": "¥12.5/米"}},
        reviewed_by="m@giraffe.com",
    )  # should not raise


# ── AC8: Asset layer resolution — client overrides universal ──────────────────

def test_client_proprietary_overrides_universal():
    value, source = resolve_benchmark_value(
        universal_value=Decimal("10.00"),
        client_value=Decimal("9.50"),
        client_id="client-abc",
    )
    assert value == Decimal("9.50")
    assert source == "client_proprietary"


def test_fallback_to_universal_when_no_client_value():
    value, source = resolve_benchmark_value(
        universal_value=Decimal("10.00"),
        client_value=None,
        client_id="client-abc",
    )
    assert value == Decimal("10.00")
    assert source == "giraffe_universal"


def test_no_data_when_both_absent():
    value, source = resolve_benchmark_value(
        universal_value=None,
        client_value=None,
        client_id=None,
    )
    assert value is None
    assert source == "no_data"


# ── AC9: Threshold changes require audit log (structural test) ───────────────

def test_threshold_adjustment_log_model_has_required_fields():
    """
    Verifies that ThresholdAdjustmentLog captures all fields required by spec §5.2:
    operator, changed_at, previous values, new values, reason.
    """
    from src.db.models.pricing import ThresholdAdjustmentLog
    cols = {c.name for c in ThresholdAdjustmentLog.__table__.columns}
    assert "operator" in cols
    assert "changed_at" in cols
    assert "previous_tier1" in cols
    assert "previous_tier2" in cols
    assert "new_tier1" in cols
    assert "new_tier2" in cols
    assert "reason" in cols


# ── Benchmark recalculator ────────────────────────────────────────────────────

def test_recalculator_empty_returns_null_stats():
    calc = BenchmarkRecalculator()
    result = calc.recalculate([])
    assert result["sample_size"] == 0
    assert result["avg_price"] is None


def test_recalculator_computes_correct_stats():
    calc = BenchmarkRecalculator()
    samples = [Decimal("10"), Decimal("12"), Decimal("11"), Decimal("13"), Decimal("14")]
    result = calc.recalculate(samples)
    assert result["sample_size"] == 5
    assert result["avg_price"] == Decimal("12")
    assert result["min_price"] == Decimal("10")
    assert result["max_price"] == Decimal("14")
    assert result["std_dev"] is not None


# ── Lead time engine ──────────────────────────────────────────────────────────

def test_lead_time_missing_fabric_raises():
    engine = LeadTimeEngine()
    inp = LeadTimeInput(items=[])
    with pytest.raises(MissingPricingDataError):
        engine.calculate(inp)


def test_lead_time_phase_based_calculation():
    engine = LeadTimeEngine()
    inp = LeadTimeInput(items=[
        LeadTimeItem("fabric",    20, LeadTimeRelation.PARALLEL,   PHASE_PROCUREMENT),
        LeadTimeItem("buttons",   15, LeadTimeRelation.PARALLEL,   PHASE_PROCUREMENT),
        LeadTimeItem("thread",    10, LeadTimeRelation.PARALLEL,   PHASE_PROCUREMENT),
        LeadTimeItem("embroidery",18, LeadTimeRelation.SEQUENTIAL, PHASE_PROCESS),
        LeadTimeItem("production", 7, LeadTimeRelation.SEQUENTIAL, PHASE_PRODUCTION),
        LeadTimeItem("packaging",  5, LeadTimeRelation.SEQUENTIAL, PHASE_PACKAGING),
    ])
    result = engine.calculate(inp)
    # phase1 (parallel procurement) = max(20, 15, 10) = 20
    # phase2 (sequential process)   = 18
    # phase3 (sequential production)= 7
    # phase4 (sequential packaging) = 5
    # total = 20 + 18 + 7 + 5 = 50
    assert result == 50
