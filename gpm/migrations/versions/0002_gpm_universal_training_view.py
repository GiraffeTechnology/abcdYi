"""GPM: add v_training_data_universal view — structural guard for §5.4 client isolation

Revision ID: gpm0002
Revises: gpm0001
Create Date: 2026-06-16

The view exposes ONLY rows from verified_business_data where
target_layer = 'universal'.  Any process that populates giraffe_universal_model
MUST SELECT FROM gpm.v_training_data_universal, not from the base table.
This makes client_proprietary exclusion structural, not just conventional.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "gpm0002"
down_revision: Union[str, None] = "gpm0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_VIEW_DDL = """
CREATE OR REPLACE VIEW gpm.v_training_data_universal AS
SELECT
    id,
    sku_id,
    process_id,
    param_key,
    param_value,
    unit_price,
    currency,
    supplier,
    quote_date,
    source,
    created_at
FROM gpm.verified_business_data
WHERE target_layer = 'universal'
  AND client_id IS NULL;
"""

_VIEW_DROP = "DROP VIEW IF EXISTS gpm.v_training_data_universal;"

_COMMENT = """
COMMENT ON VIEW gpm.v_training_data_universal IS
'Safe training-data feed for giraffe_universal_model.
Client-proprietary rows (target_layer <> ''universal'' or client_id IS NOT NULL)
are excluded at the view level. Universal model training pipelines must
SELECT from this view, never from verified_business_data directly.';
"""


def upgrade() -> None:
    op.execute(_VIEW_DDL)
    op.execute(_COMMENT)
    # Revoke direct SELECT on verified_business_data from any future
    # automated training role — it should only see the view.
    # (abcdyi_service already has SELECT on verified_business_data for auditing;
    #  that grant is unaffected here.)
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'gpm_training_role') THEN "
        "  REVOKE SELECT ON gpm.verified_business_data FROM gpm_training_role; "
        "  GRANT SELECT ON gpm.v_training_data_universal TO gpm_training_role; "
        "END IF; END $$;"
    )


def downgrade() -> None:
    op.execute(_VIEW_DROP)
