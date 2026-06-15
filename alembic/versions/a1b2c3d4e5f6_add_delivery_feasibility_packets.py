"""add_delivery_feasibility_packets

Revision ID: a1b2c3d4e5f6
Revises: f66f720908c0
Create Date: 2026-06-15 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f66f720908c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'delivery_feasibility_packets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('order_id', sa.Uuid(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('earliest_delivery_date', sa.Date(), nullable=True),
        sa.Column('most_likely_delivery_date', sa.Date(), nullable=True),
        sa.Column('risk_adjusted_delivery_date', sa.Date(), nullable=True),
        sa.Column('committable_delivery_date', sa.Date(), nullable=True),
        sa.Column('required_delivery_date', sa.Date(), nullable=True),
        sa.Column('delivery_feasibility', sa.String(length=50), nullable=True),
        sa.Column('days_vs_deadline', sa.Integer(), nullable=True),
        sa.Column('critical_path_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('critical_path_days', sa.Integer(), nullable=True),
        sa.Column('ranked_options_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('option_count', sa.Integer(), nullable=True),
        sa.Column('risk_flags_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('missing_evidence_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_gltg_packet_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dfp_order_id', 'delivery_feasibility_packets', ['order_id'])
    op.create_index('ix_dfp_tenant_id', 'delivery_feasibility_packets', ['tenant_id'])


def downgrade() -> None:
    op.drop_index('ix_dfp_tenant_id', table_name='delivery_feasibility_packets')
    op.drop_index('ix_dfp_order_id', table_name='delivery_feasibility_packets')
    op.drop_table('delivery_feasibility_packets')
