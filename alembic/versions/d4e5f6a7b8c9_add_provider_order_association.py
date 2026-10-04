"""Add tenant-bound provider-confirmed order associations.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""
from alembic import op
import sqlalchemy as sa
from src.db.json_type import PortableJSON

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "provider_order_associations",
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("orders.id"), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("provider_id", sa.String(255), nullable=False),
        sa.Column("provider_tenant_id", sa.String(255), nullable=False),
        sa.Column("source_po_id", sa.String(255), nullable=False),
        sa.Column("source_quote_id", sa.String(255), nullable=False),
        sa.Column("source_snapshot_hash", sa.String(64), nullable=False),
        sa.Column("source_snapshot", PortableJSON(), nullable=False),
        sa.UniqueConstraint("tenant_id", "provider_id", "source_po_id", name="uq_provider_order_source"),
    )


def downgrade():
    op.drop_table("provider_order_associations")
