"""Record selected-provider execution revision and verified snapshot identity.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""
from alembic import op
import sqlalchemy as sa
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("provider_order_associations", sa.Column("execution_revision", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("provider_order_associations", sa.Column("execution_snapshot_hash", sa.String(64), nullable=True))


def downgrade():
    op.drop_column("provider_order_associations", "execution_snapshot_hash")
    op.drop_column("provider_order_associations", "execution_revision")
