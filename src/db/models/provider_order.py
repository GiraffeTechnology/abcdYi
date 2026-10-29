"""Durable association between an execution order and its provider-confirmed PO."""
import uuid
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base
from src.db.json_type import PortableJSON


class ProviderOrderAssociation(Base):
    __tablename__ = "provider_order_associations"
    __table_args__ = (UniqueConstraint("tenant_id", "provider_id", "source_po_id", name="uq_provider_order_source"),)

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_po_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_quote_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_snapshot: Mapped[dict] = mapped_column(PortableJSON, nullable=False)

    execution_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    execution_snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
