"""add approval_requests.consumed_at for replay protection

Adds a one-time-consumption marker to ``approval_requests``. Once an approval
has been spent to authorise an external action, ``consumed_at`` is stamped and
the same approval can never authorise a second action (replay protection).

Additive and nullable, safe on a populated database and reversible.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-27 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'approval_requests',
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('approval_requests', 'consumed_at')
