from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON, CheckConstraint, Date, DateTime, Index, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid, utcnow


# ── Section 1: Master Data Layer ─────────────────────────────────────────────

class FabricDB(Base):
    __tablename__ = "fabric_db"

    fabric_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    input_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AccessoryDB(Base):
    __tablename__ = "accessory_db"

    accessory_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    input_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProcessTypeDef(Base):
    __tablename__ = "process_type_def"

    process_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    process_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    pricing_method: Mapped[str] = mapped_column(String(32), nullable=False)
    category_scope: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "pricing_method IN ('per_piece', 'per_area', 'per_stitch_count')",
            name="ck_process_type_pricing_method",
        ),
    )


class SKUProcessAttribute(Base):
    """
    Dynamic process pricing detail per SKU.
    INVARIANT: unit_price, supplier, quote_date are all NOT NULL.
    New process types extend this table without schema changes (per spec §1.3).
    """
    __tablename__ = "sku_process_attribute"

    attr_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    sku_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    process_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    param_key: Mapped[str] = mapped_column(String(128), nullable=False)
    param_value: Mapped[str] = mapped_column(String(512), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    supplier: Mapped[str] = mapped_column(String(255), nullable=False)
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    input_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_sku_process_attr_sku_process", "sku_id", "process_id"),
    )


class PackagingDB(Base):
    __tablename__ = "packaging_db"

    packaging_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    packaging_type: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    input_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class LossRateRef(Base):
    __tablename__ = "loss_rate_ref"

    loss_rate_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    process_type: Mapped[str] = mapped_column(String(255), nullable=False)
    loss_rate: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    input_by: Mapped[str] = mapped_column(String(255), nullable=False)
    input_date: Mapped[date] = mapped_column(Date, nullable=False)


class LaborCostRef(Base):
    __tablename__ = "labor_cost_ref"

    labor_cost_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    operation: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False, default="per_hour")
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    input_by: Mapped[str] = mapped_column(String(255), nullable=False)


class OverheadProfitRef(Base):
    __tablename__ = "overhead_profit_ref"

    ref_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    client_type: Mapped[str] = mapped_column(String(128), nullable=False)
    order_scale_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    order_scale_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    overhead_rate: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    profit_rate: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    input_by: Mapped[str] = mapped_column(String(255), nullable=False)


class FactoryCapability(Base):
    __tablename__ = "factory_capability"

    factory_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    factory_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supported_process_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    capacity_per_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    moq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    historical_lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cooperation_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SKUMain(Base):
    """
    Fixed-structure SKU master record.
    INVARIANT: extra_attributes is display-only — the calculation engine never reads it.
    Any value that participates in the pricing formula MUST live in a named structured
    column here or in sku_process_attribute, never in extra_attributes (per spec §1.2).
    """
    __tablename__ = "sku_main"

    sku_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    sku_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)

    # Pricing formula fields — fixed structure, never dynamic
    fabric_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    accessory_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    process_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    packaging_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    loss_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6), nullable=True)
    labor_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    overhead_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6), nullable=True)
    profit_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6), nullable=True)

    # Display-only — calculation engine is explicitly prohibited from reading this field
    extra_attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_quoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Section 3: Benchmark Validation Layer ─────────────────────────────────────

class ProcessBenchmark(Base):
    __tablename__ = "process_benchmark"

    benchmark_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    process_id: Mapped[str] = mapped_column(String(36), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    param_key: Mapped[str] = mapped_column(String(128), nullable=False)
    avg_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    std_dev: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    max_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_note: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    last_calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("process_id", "category", "param_key", "source_type", name="uq_benchmark_key"),
        CheckConstraint(
            "source_type IN ('verified_business_data', 'client_provided', 'external_tier1', 'external_tier2')",
            name="ck_benchmark_source_type",
        ),
    )


class CategoryProcessNorm(Base):
    __tablename__ = "category_process_norm"

    norm_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    process_id: Mapped[str] = mapped_column(String(36), nullable=False)
    occurrence_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    last_calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("category", "process_id", name="uq_category_process_norm"),
    )


class ThresholdConfig(Base):
    """
    Deviation thresholds configurable by Giraffe admin (universal layer) or client admin
    (proprietary layer within Giraffe-set bounds). Every write must be paired with a
    ThresholdAdjustmentLog entry. No automated code path adjusts these values.
    """
    __tablename__ = "threshold_config"

    config_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_value: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    threshold_tier1: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    threshold_tier2: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('global', 'category', 'process')",
            name="ck_threshold_scope_type",
        ),
    )


class ThresholdAdjustmentLog(Base):
    """Immutable audit record for every threshold change. Never deleted."""
    __tablename__ = "threshold_adjustment_log"

    log_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    config_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    previous_tier1: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    previous_tier2: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    new_tier1: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    new_tier2: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


# ── Section 4: External Market Data ───────────────────────────────────────────

class ExternalMarketData(Base):
    __tablename__ = "external_market_data"

    data_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    process_id_or_material: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    data_source: Mapped[str] = mapped_column(String(512), nullable=False)
    source_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    collection_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_url_or_reference: Mapped[str] = mapped_column(Text, nullable=False)
    verification_method: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_review")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "source_tier IN ('tier1', 'tier2', 'tier3', 'pending_review')",
            name="ck_ext_data_source_tier",
        ),
        CheckConstraint(
            "verification_status IN ('pending_review', 'verified', 'rejected')",
            name="ck_ext_data_verification_status",
        ),
    )


class DistillationJob(Base):
    """
    LLM-assisted structured extraction from verified source documents.
    extraction_output stays 'pending' until a human sets review_status='approved'.
    No automated path writes extraction_output into external_market_data or process_benchmark.
    Rejected records are retained for error-pattern analysis (never deleted).
    """
    __tablename__ = "distillation_job"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_document_ref: Mapped[str] = mapped_column(Text, nullable=False)
    source_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(128), nullable=False)
    llm_model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    extraction_output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "source_tier IN ('tier1', 'tier2')",
            name="ck_distillation_source_tier",
        ),
        CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name="ck_distillation_review_status",
        ),
    )


# ── Section 5: Asset Layer Architecture ───────────────────────────────────────

class ClientDataConsent(Base):
    __tablename__ = "client_data_consent"

    consent_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    client_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    consented_by: Mapped[str] = mapped_column(String(255), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "consent_type IN ('proprietary_only', 'contribute_to_universal')",
            name="ck_consent_type",
        ),
    )


class AssetLayerVersionSnapshot(Base):
    """
    Immutable snapshot created each time benchmarks are auto-recalculated (Level-1 auto-learning).
    Provides full version history for traceability. Never updated in place.
    """
    __tablename__ = "asset_layer_version_snapshot"

    snapshot_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    layer_type: Mapped[str] = mapped_column(String(32), nullable=False)
    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    snapshot_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(64), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "layer_type IN ('universal', 'client_proprietary')",
            name="ck_snapshot_layer_type",
        ),
        CheckConstraint(
            "triggered_by IN ('auto_recalc', 'manual')",
            name="ck_snapshot_triggered_by",
        ),
    )
