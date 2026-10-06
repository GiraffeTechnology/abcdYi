"""Add explicitly assigned execution-project memberships.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""
from alembic import op
import sqlalchemy as sa
revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('project_memberships',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('project_id', sa.Uuid(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.String(40), nullable=False),
        sa.Column('participant_id', sa.Uuid(), sa.ForeignKey('participants.id'), nullable=True),
        sa.Column('granted_by', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('project_id', 'user_id', name='uq_project_member'))


def downgrade():
    op.drop_table('project_memberships')
