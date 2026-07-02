"""reconcile projects role-switching columns

Brings the migrated ``projects`` table in line with the current ``Project``
model. These columns were added to the model for B/M-side role-switching but
were never reflected in an Alembic migration, leaving the migrated schema
unable to support the live ORM (every INSERT into ``projects`` referenced
``project_id`` which did not exist on a migrated database).

All columns are additive and nullable, so the migration is safe to apply to a
populated production database and is fully reversible.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-27 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COLUMNS = [
    ('project_id', sa.String(length=36)),
    ('original_buyer_actor_id', sa.String(length=36)),
    ('main_supplier_actor_id', sa.String(length=36)),
    ('category', sa.String(length=128)),
    ('product_summary', sa.Text()),
    ('quantity', sa.Integer()),
    ('product_tier', sa.String(length=32)),
    ('created_by_channel', sa.String(length=64)),
    ('metadata_json', sa.JSON()),
]


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column('projects', sa.Column(name, type_, nullable=True))
    op.create_unique_constraint('uq_projects_project_id', 'projects', ['project_id'])


def downgrade() -> None:
    op.drop_constraint('uq_projects_project_id', 'projects', type_='unique')
    for name, _ in reversed(_COLUMNS):
        op.drop_column('projects', name)
