"""
Unit tests for the GPM real-data availability test pipeline.

Covers:
  - submit_test_batch() fails if SKIP_HUMAN_REVIEW=False
  - submit_test_batch() fails if APP_ENV=production
  - submit_test_batch() succeeds with valid settings, inserts records with correct status/flags
  - recalculate_benchmarks() produces correct avg/std_dev/sample_size
  - Production guard raises at startup (config.validate_skip_human_review)

Uses SQLite in-memory via aiosqlite so no PostgreSQL is required.
"""

import math
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import String, Float, Integer, Text, DateTime, Boolean, TypeDecorator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, mapped_column, Mapped

from gpm.config import GPMSettings


# ---------------------------------------------------------------------------
# SQLite-compatible UUID type
# ---------------------------------------------------------------------------

class _SQLiteUUID(TypeDecorator):
    """Store UUID objects as hex strings in SQLite."""
    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value.hex
        return str(value).replace("-", "")

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return uuid.UUID(value)


# ---------------------------------------------------------------------------
# Lightweight test-only ORM models — no PostgreSQL types, no schema
# We define fresh classes that mirror the three tables needed, then import
# and use the service functions with these models. Service functions are
# imported AFTER we patch the module-level names.
# ---------------------------------------------------------------------------

class _TestBase(DeclarativeBase):
    pass


class _TestIncomingOrderData(_TestBase):
    __tablename__ = "incoming_order_data"

    id: Mapped[uuid.UUID] = mapped_column(_SQLiteUUID, primary_key=True)
    order_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sku_id: Mapped[str] = mapped_column(String(100), nullable=True)
    process_id: Mapped[str] = mapped_column(String(100), nullable=False)
    param_key: Mapped[str] = mapped_column(String(100), nullable=True)
    param_value: Mapped[str] = mapped_column(String(200), nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="CNY")
    supplier: Mapped[str] = mapped_column(String(200), nullable=True)
    quote_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(300), nullable=True)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    target_layer: Mapped[str] = mapped_column(String(50), nullable=False, default="universal")
    client_id: Mapped[str] = mapped_column(String(100), nullable=True)
    written_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(100), nullable=True)
    review_notes: Mapped[str] = mapped_column(Text, nullable=True)
    auto_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    batch_id: Mapped[str] = mapped_column(String(100), nullable=True)
    is_test_batch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class _TestVerifiedBusinessData(_TestBase):
    __tablename__ = "verified_business_data"

    id: Mapped[uuid.UUID] = mapped_column(_SQLiteUUID, primary_key=True)
    sku_id: Mapped[str] = mapped_column(String(100), nullable=True)
    process_id: Mapped[str] = mapped_column(String(100), nullable=False)
    param_key: Mapped[str] = mapped_column(String(100), nullable=True)
    param_value: Mapped[str] = mapped_column(String(200), nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="CNY")
    supplier: Mapped[str] = mapped_column(String(200), nullable=True)
    quote_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(300), nullable=True)
    target_layer: Mapped[str] = mapped_column(String(50), nullable=False, default="universal")
    client_id: Mapped[str] = mapped_column(String(100), nullable=True)
    batch_id: Mapped[str] = mapped_column(String(100), nullable=True)
    is_test_batch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class _TestProcessBenchmark(_TestBase):
    __tablename__ = "process_benchmark"

    id: Mapped[uuid.UUID] = mapped_column(_SQLiteUUID, primary_key=True)
    process_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sku_id: Mapped[str] = mapped_column(String(100), nullable=True)
    param_key: Mapped[str] = mapped_column(String(100), nullable=True)
    param_value: Mapped[str] = mapped_column(String(200), nullable=True)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False)
    std_dev: Mapped[float] = mapped_column(Float, nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="CNY")
    last_calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Patch gpm.service and gpm.models to use test models for the duration of tests
# ---------------------------------------------------------------------------

import gpm.models as _gpm_models
import gpm.service as _gpm_service


@pytest_asyncio.fixture
async def sqlite_session():
    """
    Create a fresh in-memory SQLite database and patch the GPM service to use
    lightweight SQLite-compatible ORM models instead of the PostgreSQL ones.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(_TestBase.metadata.create_all)

    # Patch gpm.service module references to point at test models
    _orig_incoming = _gpm_service.IncomingOrderData
    _orig_verified = _gpm_service.VerifiedBusinessData
    _orig_benchmark = _gpm_service.ProcessBenchmark

    _gpm_service.IncomingOrderData = _TestIncomingOrderData
    _gpm_service.VerifiedBusinessData = _TestVerifiedBusinessData
    _gpm_service.ProcessBenchmark = _TestProcessBenchmark

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            yield session
    finally:
        # Restore original model references
        _gpm_service.IncomingOrderData = _orig_incoming
        _gpm_service.VerifiedBusinessData = _orig_verified
        _gpm_service.ProcessBenchmark = _orig_benchmark
        await engine.dispose()


# Import service functions AFTER the fixture is defined (they're called at runtime)
from gpm.service import (
    get_test_batch_summary,
    recalculate_benchmarks,
    submit_test_batch,
)


# ---------------------------------------------------------------------------
# Sample records helper
# ---------------------------------------------------------------------------

def _make_records(n: int = 5, process_id: str = "sewing_process") -> list[dict]:
    """Return n simple pricing records for testing."""
    records = []
    for i in range(n):
        records.append({
            "process_id": process_id,
            "param_key": "basic_stitch",
            "param_value": "T-shirt",
            "unit_price": 2.50 + i * 0.10,  # slight variation
            "currency": "CNY",
            "source": "中国服装行业协会价格报告 2023",
        })
    return records


# ---------------------------------------------------------------------------
# Config guard tests
# ---------------------------------------------------------------------------

class TestConfigGuard:
    def test_production_guard_raises_when_skip_review_in_production(self):
        """validate_skip_human_review() must raise RuntimeError in production."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="production")
        with pytest.raises(RuntimeError, match="not allowed in production"):
            cfg.validate_skip_human_review()

    def test_production_guard_ok_when_skip_review_in_staging(self):
        """validate_skip_human_review() must not raise in staging."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="staging")
        cfg.validate_skip_human_review()  # should not raise

    def test_production_guard_ok_when_skip_review_false_in_production(self):
        """validate_skip_human_review() must not raise when SKIP=False, even in production."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=False, APP_ENV="production")
        cfg.validate_skip_human_review()  # should not raise

    def test_production_guard_ok_in_development(self):
        """validate_skip_human_review() must not raise in development regardless."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="development")
        cfg.validate_skip_human_review()  # should not raise


# ---------------------------------------------------------------------------
# submit_test_batch() tests
# ---------------------------------------------------------------------------

class TestSubmitTestBatch:
    @pytest.mark.asyncio
    async def test_fails_when_skip_human_review_is_false(self, sqlite_session):
        """submit_test_batch() must raise ValueError if SKIP_HUMAN_REVIEW=False."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=False, APP_ENV="staging")
        records = _make_records(2)
        with pytest.raises(ValueError, match="SKIP_HUMAN_REVIEW"):
            await submit_test_batch(sqlite_session, records, "batch-test-001", cfg=cfg)

    @pytest.mark.asyncio
    async def test_fails_when_app_env_is_production(self, sqlite_session):
        """submit_test_batch() must raise ValueError if APP_ENV=production."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="production")
        records = _make_records(2)
        with pytest.raises(ValueError, match="production"):
            await submit_test_batch(sqlite_session, records, "batch-test-002", cfg=cfg)

    @pytest.mark.asyncio
    async def test_succeeds_with_valid_settings(self, sqlite_session):
        """submit_test_batch() succeeds with SKIP_HUMAN_REVIEW=True and non-production env."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="staging")
        records = _make_records(5)
        batch_id = "batch-test-003"

        count = await submit_test_batch(sqlite_session, records, batch_id, cfg=cfg)
        assert count == 5

    @pytest.mark.asyncio
    async def test_records_have_correct_review_status(self, sqlite_session):
        """Inserted IncomingOrderData rows must have review_status='test_auto_approved'."""
        from sqlalchemy import select

        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="staging")
        records = _make_records(3)
        batch_id = "batch-test-004"

        await submit_test_batch(sqlite_session, records, batch_id, cfg=cfg)

        result = await sqlite_session.execute(
            select(_TestIncomingOrderData).where(_TestIncomingOrderData.batch_id == batch_id)
        )
        rows = result.scalars().all()
        assert len(rows) == 3
        for row in rows:
            assert row.review_status == "test_auto_approved"
            assert row.is_test_batch is True
            assert row.auto_confirmed is True
            assert row.batch_id == batch_id

    @pytest.mark.asyncio
    async def test_records_promoted_to_verified(self, sqlite_session):
        """submit_test_batch() must also insert rows into VerifiedBusinessData."""
        from sqlalchemy import select

        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="staging")
        records = _make_records(4)
        batch_id = "batch-test-005"

        await submit_test_batch(sqlite_session, records, batch_id, cfg=cfg)

        result = await sqlite_session.execute(
            select(_TestVerifiedBusinessData).where(_TestVerifiedBusinessData.batch_id == batch_id)
        )
        verified_rows = result.scalars().all()
        assert len(verified_rows) == 4
        for row in verified_rows:
            assert row.is_test_batch is True
            assert row.batch_id == batch_id

    @pytest.mark.asyncio
    async def test_returns_correct_count(self, sqlite_session):
        """submit_test_batch() must return the exact number of records inserted."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="development")
        n = 7
        records = _make_records(n)
        batch_id = "batch-test-006"

        count = await submit_test_batch(sqlite_session, records, batch_id, cfg=cfg)
        assert count == n


# ---------------------------------------------------------------------------
# recalculate_benchmarks() tests
# ---------------------------------------------------------------------------

class TestRecalculateBenchmarks:
    @pytest.mark.asyncio
    async def test_correct_avg_and_sample_size(self, sqlite_session):
        """recalculate_benchmarks() must produce the correct average and sample size."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="staging")
        batch_id = "bench-test-001"

        # 3 records with known unit prices
        records = [
            {"process_id": "printing_process", "param_key": "screen_print", "unit_price": 3.0,
             "currency": "CNY", "source": "中国印花协会报告 2023"},
            {"process_id": "printing_process", "param_key": "screen_print", "unit_price": 5.0,
             "currency": "CNY", "source": "中国印花协会报告 2023"},
            {"process_id": "printing_process", "param_key": "screen_print", "unit_price": 7.0,
             "currency": "CNY", "source": "中国印花协会报告 2023"},
        ]
        await submit_test_batch(sqlite_session, records, batch_id, cfg=cfg)

        stats = await recalculate_benchmarks(sqlite_session, process_ids=["printing_process"])

        assert "printing_process" in stats
        process_stats = {s["param_key"]: s for s in stats["printing_process"]}
        assert "screen_print" in process_stats
        s = process_stats["screen_print"]
        assert s["sample_size"] == 3
        assert abs(s["avg_price"] - 5.0) < 1e-9  # (3+5+7)/3 = 5.0

    @pytest.mark.asyncio
    async def test_correct_std_dev(self, sqlite_session):
        """recalculate_benchmarks() must compute the correct sample standard deviation."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="staging")
        batch_id = "bench-test-002"

        # 4 known prices: 2, 4, 4, 4, 4 → avg=3.6, sample std ≈ 0.894
        # Using simpler: 2, 4, 6 → avg=4, sample std = sqrt(((4+0+4)/2)) = sqrt(4) = 2
        records = [
            {"process_id": "embroidery_process", "param_key": "flat_embroidery", "unit_price": 2.0,
             "currency": "CNY", "source": "中国刺绣行业报告 2022"},
            {"process_id": "embroidery_process", "param_key": "flat_embroidery", "unit_price": 4.0,
             "currency": "CNY", "source": "中国刺绣行业报告 2022"},
            {"process_id": "embroidery_process", "param_key": "flat_embroidery", "unit_price": 6.0,
             "currency": "CNY", "source": "中国刺绣行业报告 2022"},
        ]
        await submit_test_batch(sqlite_session, records, batch_id, cfg=cfg)

        stats = await recalculate_benchmarks(sqlite_session, process_ids=["embroidery_process"])
        s = {x["param_key"]: x for x in stats["embroidery_process"]}["flat_embroidery"]

        expected_avg = 4.0
        expected_std = math.sqrt(((2 - 4) ** 2 + (4 - 4) ** 2 + (6 - 4) ** 2) / (3 - 1))  # = 2.0

        assert abs(s["avg_price"] - expected_avg) < 1e-9
        assert abs(s["std_dev"] - expected_std) < 1e-9

    @pytest.mark.asyncio
    async def test_single_record_std_dev_is_zero(self, sqlite_session):
        """With a single record, std_dev should be 0."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="staging")
        batch_id = "bench-test-003"

        records = [
            {"process_id": "accessory_cost", "param_key": "button", "unit_price": 0.12,
             "currency": "CNY", "source": "中国辅料协会市场报告 2023"},
        ]
        await submit_test_batch(sqlite_session, records, batch_id, cfg=cfg)

        stats = await recalculate_benchmarks(sqlite_session, process_ids=["accessory_cost"])
        s = {x["param_key"]: x for x in stats["accessory_cost"]}["button"]

        assert s["sample_size"] == 1
        assert s["std_dev"] == 0.0
        assert abs(s["avg_price"] - 0.12) < 1e-9

    @pytest.mark.asyncio
    async def test_multiple_process_ids(self, sqlite_session):
        """recalculate_benchmarks() handles multiple process_ids in one call."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="staging")
        batch_id = "bench-test-004"

        records = [
            {"process_id": "fabric_cost", "param_key": "cotton", "unit_price": 18.0,
             "currency": "CNY", "source": "中纺联 2023"},
            {"process_id": "fabric_cost", "param_key": "cotton", "unit_price": 20.0,
             "currency": "CNY", "source": "中纺联 2023"},
            {"process_id": "packaging_cost", "param_key": "poly_bag", "unit_price": 0.30,
             "currency": "CNY", "source": "纸箱包装协会报告 2023"},
        ]
        await submit_test_batch(sqlite_session, records, batch_id, cfg=cfg)

        stats = await recalculate_benchmarks(
            sqlite_session,
            process_ids=["fabric_cost", "packaging_cost"],
        )

        assert "fabric_cost" in stats
        assert "packaging_cost" in stats

        cotton = {x["param_key"]: x for x in stats["fabric_cost"]}["cotton"]
        assert cotton["sample_size"] == 2
        assert abs(cotton["avg_price"] - 19.0) < 1e-9

        poly = {x["param_key"]: x for x in stats["packaging_cost"]}["poly_bag"]
        assert poly["sample_size"] == 1
        assert abs(poly["avg_price"] - 0.30) < 1e-9

    @pytest.mark.asyncio
    async def test_no_process_ids_recalculates_all(self, sqlite_session):
        """When process_ids=None, all process IDs in the DB are recalculated."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="staging")
        batch_id = "bench-test-005"

        records = [
            {"process_id": "sewing_process", "param_key": "overlock", "unit_price": 1.5,
             "currency": "CNY", "source": "中国服装协会 2023"},
            {"process_id": "sewing_process", "param_key": "overlock", "unit_price": 2.0,
             "currency": "CNY", "source": "中国服装协会 2023"},
        ]
        await submit_test_batch(sqlite_session, records, batch_id, cfg=cfg)

        # process_ids=None — should still pick up sewing_process
        stats = await recalculate_benchmarks(sqlite_session, process_ids=None)
        assert "sewing_process" in stats

    @pytest.mark.asyncio
    async def test_upserts_existing_benchmark(self, sqlite_session):
        """A second call to recalculate_benchmarks() must UPDATE the existing row."""
        from sqlalchemy import select as sa_select

        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="staging")

        # First batch: 2 records
        records_a = [
            {"process_id": "printing_process", "param_key": "digital_print", "unit_price": 6.0,
             "currency": "CNY", "source": "广东数码印花协会报告 2023"},
            {"process_id": "printing_process", "param_key": "digital_print", "unit_price": 8.0,
             "currency": "CNY", "source": "广东数码印花协会报告 2023"},
        ]
        await submit_test_batch(sqlite_session, records_a, "upsert-batch-a", cfg=cfg)
        await recalculate_benchmarks(sqlite_session, process_ids=["printing_process"])

        # Second batch: 1 more record
        records_b = [
            {"process_id": "printing_process", "param_key": "digital_print", "unit_price": 10.0,
             "currency": "CNY", "source": "广东数码印花协会报告 2023"},
        ]
        await submit_test_batch(sqlite_session, records_b, "upsert-batch-b", cfg=cfg)
        stats2 = await recalculate_benchmarks(sqlite_session, process_ids=["printing_process"])

        dp = {x["param_key"]: x for x in stats2["printing_process"]}["digital_print"]
        # Now 3 records: 6, 8, 10 → avg = 8.0
        assert dp["sample_size"] == 3
        assert abs(dp["avg_price"] - 8.0) < 1e-9

        # Only one ProcessBenchmark row should exist (upserted, not duplicated)
        result = await sqlite_session.execute(
            sa_select(_TestProcessBenchmark).where(
                _TestProcessBenchmark.process_id == "printing_process",
                _TestProcessBenchmark.param_key == "digital_print",
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1, f"Expected 1 benchmark row but found {len(rows)}"


# ---------------------------------------------------------------------------
# get_test_batch_summary() tests
# ---------------------------------------------------------------------------

class TestGetTestBatchSummary:
    @pytest.mark.asyncio
    async def test_summary_totals(self, sqlite_session):
        """get_test_batch_summary() must return correct total_records."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="staging")
        batch_id = "summary-test-001"

        records = _make_records(6)
        await submit_test_batch(sqlite_session, records, batch_id, cfg=cfg)

        summary = await get_test_batch_summary(sqlite_session, batch_id)

        assert summary["batch_id"] == batch_id
        assert summary["total_records"] == 6

    @pytest.mark.asyncio
    async def test_summary_process_breakdown(self, sqlite_session):
        """get_test_batch_summary() must include per-process_id counts."""
        cfg = GPMSettings(SKIP_HUMAN_REVIEW=True, APP_ENV="staging")
        batch_id = "summary-test-002"

        records = (
            _make_records(3, process_id="sewing_process")
            + _make_records(2, process_id="embroidery_process")
        )
        await submit_test_batch(sqlite_session, records, batch_id, cfg=cfg)

        summary = await get_test_batch_summary(sqlite_session, batch_id)

        assert summary["process_breakdown"]["sewing_process"] == 3
        assert summary["process_breakdown"]["embroidery_process"] == 2

    @pytest.mark.asyncio
    async def test_summary_empty_batch(self, sqlite_session):
        """get_test_batch_summary() for an unknown batch_id must return zero records."""
        summary = await get_test_batch_summary(sqlite_session, "nonexistent-batch")
        assert summary["total_records"] == 0
        assert summary["process_breakdown"] == {}
