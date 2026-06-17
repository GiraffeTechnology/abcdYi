"""GPM: add batch_id and is_test_batch to incoming_order_data and verified_business_data

Revision ID: gpm0003
Revises: gpm0002
Create Date: 2026-06-17

Adds two columns to support the GPM real-data availability test pipeline:
  - batch_id (String 100, nullable, indexed): identifies which test batch a row belongs to
  - is_test_batch (Boolean, default False): hard flag marking rows inserted via submit_test_batch()
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "gpm0003"
down_revision: Union[str, None] = "gpm0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # incoming_order_data
    op.add_column(
        "incoming_order_data",
        sa.Column("batch_id", sa.String(100), nullable=True),
        schema="gpm",
    )
    op.add_column(
        "incoming_order_data",
        sa.Column("is_test_batch", sa.Boolean(), nullable=False, server_default="false"),
        schema="gpm",
    )
    op.create_index(
        "ix_incoming_order_data_batch_id",
        "incoming_order_data",
        ["batch_id"],
        schema="gpm",
    )

    # verified_business_data
    op.add_column(
        "verified_business_data",
        sa.Column("batch_id", sa.String(100), nullable=True),
        schema="gpm",
    )
    op.add_column(
        "verified_business_data",
        sa.Column("is_test_batch", sa.Boolean(), nullable=False, server_default="false"),
        schema="gpm",
    )
    op.create_index(
        "ix_verified_business_data_batch_id",
        "verified_business_data",
        ["batch_id"],
        schema="gpm",
    )


def downgrade() -> None:
    op.drop_index("ix_verified_business_data_batch_id", table_name="verified_business_data", schema="gpm")
    op.drop_column("verified_business_data", "is_test_batch", schema="gpm")
    op.drop_column("verified_business_data", "batch_id", schema="gpm")

    op.drop_index("ix_incoming_order_data_batch_id", table_name="incoming_order_data", schema="gpm")
    op.drop_column("incoming_order_data", "is_test_batch", schema="gpm")
    op.drop_column("incoming_order_data", "batch_id", schema="gpm")
