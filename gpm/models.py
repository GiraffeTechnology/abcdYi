import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, Text, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from gpm.db import GPMBase


class FabricDB(GPMBase):
    """Reference data for fabrics — weight, composition, finish properties."""
    __tablename__ = "fabric_db"
    __table_args__ = {"schema": "gpm"}

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fabric_type: Mapped[str] = mapped_column(String(100), nullable=False)
    composition: Mapped[str] = mapped_column(String(200), nullable=True)
    weight_gsm: Mapped[float] = mapped_column(Float, nullable=True)
    finish: Mapped[str] = mapped_column(String(100), nullable=True)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SKUProcessAttribute(GPMBase):
    """Maps SKUs to their required processes and associated attribute key/value pairs."""
    __tablename__ = "sku_process_attribute"
    __table_args__ = {"schema": "gpm"}

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    process_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    attribute_key: Mapped[str] = mapped_column(String(100), nullable=False)
    attribute_value: Mapped[str] = mapped_column(String(200), nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VerifiedBusinessData(GPMBase):
    """
    Confirmed order-pricing records that feed into process_benchmark computation.
    abcdyi has READ-ONLY access; rows are inserted only by GPM's internal promotion service.
    """
    __tablename__ = "verified_business_data"
    __table_args__ = {"schema": "gpm"}

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    process_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    param_key: Mapped[str] = mapped_column(String(100), nullable=True)
    param_value: Mapped[str] = mapped_column(String(200), nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    supplier: Mapped[str] = mapped_column(String(200), nullable=True)
    quote_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(300), nullable=True)
    target_layer: Mapped[str] = mapped_column(String(50), nullable=False, default="universal")
    client_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    batch_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    is_test_batch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProcessBenchmark(GPMBase):
    """
    Aggregated statistical benchmarks per process/param combination.
    Recomputed by GPM's internal scheduler after new data is promoted from incoming_order_data.
    abcdyi has READ-ONLY access.
    """
    __tablename__ = "process_benchmark"
    __table_args__ = {"schema": "gpm"}

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sku_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    param_key: Mapped[str] = mapped_column(String(100), nullable=True)
    param_value: Mapped[str] = mapped_column(String(200), nullable=True)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False)
    std_dev: Mapped[float] = mapped_column(Float, nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "internal" | "external" | "mixed"
    last_calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")


class GiraffeUniversalModel(GPMBase):
    """
    Trained model coefficients for the universal pricing model.
    Contains NO client-proprietary data unless client explicitly consented.
    abcdyi has READ-ONLY access.
    """
    __tablename__ = "giraffe_universal_model"
    __table_args__ = {"schema": "gpm"}

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    process_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    param_key: Mapped[str] = mapped_column(String(100), nullable=True)
    coefficient: Mapped[float] = mapped_column(Float, nullable=True)
    intercept: Mapped[float] = mapped_column(Float, nullable=True)
    r_squared: Mapped[float] = mapped_column(Float, nullable=True)
    training_sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str] = mapped_column(Text, nullable=True)


class IncomingOrderData(GPMBase):
    """
    Buffer table for order-pricing data submitted by abcdyi.
    abcdyi has INSERT access here ONLY.
    GPM's internal promotion service moves confirmed rows into verified_business_data.
    """
    __tablename__ = "incoming_order_data"
    __table_args__ = {"schema": "gpm"}

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sku_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    process_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    param_key: Mapped[str] = mapped_column(String(100), nullable=True)
    param_value: Mapped[str] = mapped_column(String(200), nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    supplier: Mapped[str] = mapped_column(String(200), nullable=True)
    quote_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(300), nullable=True)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")  # PENDING | CONFIRMED | REJECTED | test_auto_approved
    target_layer: Mapped[str] = mapped_column(String(50), nullable=False, default="universal")  # universal | client_proprietary
    client_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    written_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(100), nullable=True)
    review_notes: Mapped[str] = mapped_column(Text, nullable=True)
    auto_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    batch_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    is_test_batch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
