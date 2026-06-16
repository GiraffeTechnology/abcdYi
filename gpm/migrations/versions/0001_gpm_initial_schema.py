"""GPM initial schema — gpm schema with all core tables

Revision ID: gpm0001
Revises:
Create Date: 2026-06-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "gpm0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS gpm")

    op.create_table(
        "fabric_db",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("fabric_type", sa.String(100), nullable=False),
        sa.Column("composition", sa.String(200), nullable=True),
        sa.Column("weight_gsm", sa.Float(), nullable=True),
        sa.Column("finish", sa.String(100), nullable=True),
        sa.Column("properties", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="gpm",
    )

    op.create_table(
        "sku_process_attribute",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("sku_id", sa.String(100), nullable=False),
        sa.Column("process_id", sa.String(100), nullable=False),
        sa.Column("attribute_key", sa.String(100), nullable=False),
        sa.Column("attribute_value", sa.String(200), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="gpm",
    )
    op.create_index("ix_sku_process_attribute_sku_id", "sku_process_attribute", ["sku_id"], schema="gpm")
    op.create_index("ix_sku_process_attribute_process_id", "sku_process_attribute", ["process_id"], schema="gpm")

    op.create_table(
        "verified_business_data",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("sku_id", sa.String(100), nullable=True),
        sa.Column("process_id", sa.String(100), nullable=False),
        sa.Column("param_key", sa.String(100), nullable=True),
        sa.Column("param_value", sa.String(200), nullable=True),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("supplier", sa.String(200), nullable=True),
        sa.Column("quote_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(300), nullable=True),
        sa.Column("target_layer", sa.String(50), nullable=False, server_default="universal"),
        sa.Column("client_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="gpm",
    )
    op.create_index("ix_verified_business_data_process_id", "verified_business_data", ["process_id"], schema="gpm")
    op.create_index("ix_verified_business_data_sku_id", "verified_business_data", ["sku_id"], schema="gpm")
    op.create_index("ix_verified_business_data_client_id", "verified_business_data", ["client_id"], schema="gpm")

    op.create_table(
        "process_benchmark",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("process_id", sa.String(100), nullable=False),
        sa.Column("sku_id", sa.String(100), nullable=True),
        sa.Column("param_key", sa.String(100), nullable=True),
        sa.Column("param_value", sa.String(200), nullable=True),
        sa.Column("avg_price", sa.Float(), nullable=False),
        sa.Column("std_dev", sa.Float(), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("last_calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="gpm",
    )
    op.create_index("ix_process_benchmark_process_id", "process_benchmark", ["process_id"], schema="gpm")
    op.create_index("ix_process_benchmark_sku_id", "process_benchmark", ["sku_id"], schema="gpm")

    op.create_table(
        "giraffe_universal_model",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("process_id", sa.String(100), nullable=False),
        sa.Column("param_key", sa.String(100), nullable=True),
        sa.Column("coefficient", sa.Float(), nullable=True),
        sa.Column("intercept", sa.Float(), nullable=True),
        sa.Column("r_squared", sa.Float(), nullable=True),
        sa.Column("training_sample_size", sa.Integer(), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        schema="gpm",
    )
    op.create_index("ix_giraffe_universal_model_process_id", "giraffe_universal_model", ["process_id"], schema="gpm")

    op.create_table(
        "incoming_order_data",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", sa.String(100), nullable=False),
        sa.Column("sku_id", sa.String(100), nullable=True),
        sa.Column("process_id", sa.String(100), nullable=False),
        sa.Column("param_key", sa.String(100), nullable=True),
        sa.Column("param_value", sa.String(200), nullable=True),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("supplier", sa.String(200), nullable=True),
        sa.Column("quote_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(300), nullable=True),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("target_layer", sa.String(50), nullable=False, server_default="universal"),
        sa.Column("client_id", sa.String(100), nullable=True),
        sa.Column("written_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("auto_confirmed", sa.Boolean(), nullable=False, server_default="false"),
        schema="gpm",
    )
    op.create_index("ix_incoming_order_data_order_id", "incoming_order_data", ["order_id"], schema="gpm")
    op.create_index("ix_incoming_order_data_process_id", "incoming_order_data", ["process_id"], schema="gpm")
    op.create_index("ix_incoming_order_data_sku_id", "incoming_order_data", ["sku_id"], schema="gpm")
    op.create_index("ix_incoming_order_data_review_status", "incoming_order_data", ["review_status"], schema="gpm")
    op.create_index("ix_incoming_order_data_client_id", "incoming_order_data", ["client_id"], schema="gpm")


def downgrade() -> None:
    op.drop_table("incoming_order_data", schema="gpm")
    op.drop_table("giraffe_universal_model", schema="gpm")
    op.drop_table("process_benchmark", schema="gpm")
    op.drop_table("verified_business_data", schema="gpm")
    op.drop_table("sku_process_attribute", schema="gpm")
    op.drop_table("fabric_db", schema="gpm")
    op.execute("DROP SCHEMA IF EXISTS gpm")
