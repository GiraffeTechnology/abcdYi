"""add_lead_time_relation_phase

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-16 13:00:00.000000

Adds lead_time_relation (VARCHAR 20, nullable) and lead_time_phase (INTEGER, nullable)
to fabric_db, accessory_db, packaging_db, and sku_process_attribute tables.
These columns support the GLTM industry knowledge learning feature (phase-based
critical path calculation).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ('fabric_db', 'accessory_db', 'packaging_db', 'sku_process_attribute'):
        op.add_column(table, sa.Column('lead_time_relation', sa.String(20), nullable=True))
        op.add_column(table, sa.Column('lead_time_phase', sa.Integer(), nullable=True))


def downgrade() -> None:
    for table in ('sku_process_attribute', 'packaging_db', 'accessory_db', 'fabric_db'):
        op.drop_column(table, 'lead_time_phase')
        op.drop_column(table, 'lead_time_relation')
