"""add_giraffe_pricing_model_v1

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-16 12:00:00.000000

Creates all 16 tables for the Giraffe industry pricing model (v1):
  Master data layer, deterministic calculation support tables,
  benchmark validation layer, external market data channel,
  asset layer architecture.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Section 1: Master Data Layer ─────────────────────────────────────────

    op.create_table(
        'fabric_db',
        sa.Column('fabric_id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('supplier', sa.String(255), nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('unit', sa.String(64), nullable=False),
        sa.Column('quote_date', sa.Date(), nullable=False),
        sa.Column('lead_time_days', sa.Integer(), nullable=False),
        sa.Column('input_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    op.create_table(
        'accessory_db',
        sa.Column('accessory_id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('supplier', sa.String(255), nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('unit', sa.String(64), nullable=False),
        sa.Column('quote_date', sa.Date(), nullable=False),
        sa.Column('lead_time_days', sa.Integer(), nullable=False),
        sa.Column('input_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    op.create_table(
        'process_type_def',
        sa.Column('process_id', sa.String(36), primary_key=True),
        sa.Column('process_name', sa.String(255), nullable=False, unique=True),
        sa.Column('pricing_method', sa.String(32), nullable=False),
        sa.Column('category_scope', sa.String(255), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "pricing_method IN ('per_piece', 'per_area', 'per_stitch_count')",
            name='ck_process_type_pricing_method'
        ),
    )

    op.create_table(
        'sku_process_attribute',
        sa.Column('attr_id', sa.String(36), primary_key=True),
        sa.Column('sku_id', sa.String(36), nullable=False),
        sa.Column('process_id', sa.String(36), nullable=False),
        sa.Column('param_key', sa.String(128), nullable=False),
        sa.Column('param_value', sa.String(512), nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('supplier', sa.String(255), nullable=False),
        sa.Column('quote_date', sa.Date(), nullable=False),
        sa.Column('lead_time_days', sa.Integer(), nullable=False),
        sa.Column('input_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_sku_process_attr_sku_id', 'sku_process_attribute', ['sku_id'])
    op.create_index('ix_sku_process_attr_process_id', 'sku_process_attribute', ['process_id'])
    op.create_index('ix_sku_process_attr_sku_process', 'sku_process_attribute', ['sku_id', 'process_id'])

    op.create_table(
        'packaging_db',
        sa.Column('packaging_id', sa.String(36), primary_key=True),
        sa.Column('packaging_type', sa.String(255), nullable=False),
        sa.Column('supplier', sa.String(255), nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('unit', sa.String(64), nullable=False),
        sa.Column('quote_date', sa.Date(), nullable=False),
        sa.Column('lead_time_days', sa.Integer(), nullable=False),
        sa.Column('input_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    op.create_table(
        'loss_rate_ref',
        sa.Column('loss_rate_id', sa.String(36), primary_key=True),
        sa.Column('category', sa.String(255), nullable=False),
        sa.Column('process_type', sa.String(255), nullable=False),
        sa.Column('loss_rate', sa.Numeric(8, 6), nullable=False),
        sa.Column('input_by', sa.String(255), nullable=False),
        sa.Column('input_date', sa.Date(), nullable=False),
    )

    op.create_table(
        'labor_cost_ref',
        sa.Column('labor_cost_id', sa.String(36), primary_key=True),
        sa.Column('operation', sa.String(255), nullable=False),
        sa.Column('region', sa.String(255), nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('unit', sa.String(64), nullable=False, server_default='per_hour'),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('input_by', sa.String(255), nullable=False),
    )

    op.create_table(
        'overhead_profit_ref',
        sa.Column('ref_id', sa.String(36), primary_key=True),
        sa.Column('client_type', sa.String(128), nullable=False),
        sa.Column('order_scale_min', sa.Integer(), nullable=True),
        sa.Column('order_scale_max', sa.Integer(), nullable=True),
        sa.Column('overhead_rate', sa.Numeric(8, 6), nullable=False),
        sa.Column('profit_rate', sa.Numeric(8, 6), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('input_by', sa.String(255), nullable=False),
    )

    op.create_table(
        'factory_capability',
        sa.Column('factory_id', sa.String(36), primary_key=True),
        sa.Column('factory_name', sa.String(255), nullable=False),
        sa.Column('supported_process_ids', sa.JSON(), nullable=False),
        sa.Column('capacity_per_day', sa.Integer(), nullable=True),
        sa.Column('moq', sa.Integer(), nullable=True),
        sa.Column('historical_lead_time_days', sa.Integer(), nullable=True),
        sa.Column('cooperation_score', sa.Numeric(4, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    op.create_table(
        'sku_main',
        sa.Column('sku_id', sa.String(36), primary_key=True),
        sa.Column('sku_name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(128), nullable=False),
        sa.Column('fabric_cost', sa.Numeric(14, 4), nullable=True),
        sa.Column('accessory_cost', sa.Numeric(14, 4), nullable=True),
        sa.Column('process_cost', sa.Numeric(14, 4), nullable=True),
        sa.Column('packaging_cost', sa.Numeric(14, 4), nullable=True),
        sa.Column('loss_rate', sa.Numeric(8, 6), nullable=True),
        sa.Column('labor_cost', sa.Numeric(14, 4), nullable=True),
        sa.Column('overhead_rate', sa.Numeric(8, 6), nullable=True),
        sa.Column('profit_rate', sa.Numeric(8, 6), nullable=True),
        sa.Column('extra_attributes', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('last_quoted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── Section 3: Benchmark Validation Layer ─────────────────────────────────

    op.create_table(
        'process_benchmark',
        sa.Column('benchmark_id', sa.String(36), primary_key=True),
        sa.Column('process_id', sa.String(36), nullable=False),
        sa.Column('category', sa.String(128), nullable=False),
        sa.Column('param_key', sa.String(128), nullable=False),
        sa.Column('avg_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('std_dev', sa.Numeric(12, 4), nullable=True),
        sa.Column('min_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('max_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source_type', sa.String(64), nullable=False),
        sa.Column('confidence_note', sa.String(512), nullable=True),
        sa.Column('last_calculated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('process_id', 'category', 'param_key', 'source_type',
                            name='uq_benchmark_key'),
        sa.CheckConstraint(
            "source_type IN ('verified_business_data', 'client_provided', 'external_tier1', 'external_tier2')",
            name='ck_benchmark_source_type'
        ),
    )

    op.create_table(
        'category_process_norm',
        sa.Column('norm_id', sa.String(36), primary_key=True),
        sa.Column('category', sa.String(128), nullable=False),
        sa.Column('process_id', sa.String(36), nullable=False),
        sa.Column('occurrence_rate', sa.Numeric(6, 4), nullable=False),
        sa.Column('last_calculated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('category', 'process_id', name='uq_category_process_norm'),
    )

    op.create_table(
        'threshold_config',
        sa.Column('config_id', sa.String(36), primary_key=True),
        sa.Column('scope_type', sa.String(32), nullable=False),
        sa.Column('scope_value', sa.String(128), nullable=True),
        sa.Column('threshold_tier1', sa.Numeric(6, 4), nullable=False),
        sa.Column('threshold_tier2', sa.Numeric(6, 4), nullable=False),
        sa.Column('client_id', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(255), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "scope_type IN ('global', 'category', 'process')",
            name='ck_threshold_scope_type'
        ),
    )

    op.create_table(
        'threshold_adjustment_log',
        sa.Column('log_id', sa.String(36), primary_key=True),
        sa.Column('config_id', sa.String(36), nullable=False),
        sa.Column('operator', sa.String(255), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('previous_tier1', sa.Numeric(6, 4), nullable=False),
        sa.Column('previous_tier2', sa.Numeric(6, 4), nullable=False),
        sa.Column('new_tier1', sa.Numeric(6, 4), nullable=False),
        sa.Column('new_tier2', sa.Numeric(6, 4), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
    )
    op.create_index('ix_threshold_adj_log_config_id', 'threshold_adjustment_log', ['config_id'])

    # ── Section 4: External Market Data ───────────────────────────────────────

    op.create_table(
        'external_market_data',
        sa.Column('data_id', sa.String(36), primary_key=True),
        sa.Column('category', sa.String(128), nullable=False),
        sa.Column('process_id_or_material', sa.String(255), nullable=False),
        sa.Column('price', sa.Numeric(12, 4), nullable=False),
        sa.Column('unit', sa.String(64), nullable=False),
        sa.Column('data_source', sa.String(512), nullable=False),
        sa.Column('source_tier', sa.String(16), nullable=False),
        sa.Column('collection_date', sa.Date(), nullable=False),
        sa.Column('source_url_or_reference', sa.Text(), nullable=False),
        sa.Column('verification_method', sa.Text(), nullable=True),
        sa.Column('verification_status', sa.String(32), nullable=False,
                  server_default='pending_review'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.CheckConstraint(
            "source_tier IN ('tier1', 'tier2', 'tier3', 'pending_review')",
            name='ck_ext_data_source_tier'
        ),
        sa.CheckConstraint(
            "verification_status IN ('pending_review', 'verified', 'rejected')",
            name='ck_ext_data_verification_status'
        ),
    )

    op.create_table(
        'distillation_job',
        sa.Column('job_id', sa.String(36), primary_key=True),
        sa.Column('source_document_ref', sa.Text(), nullable=False),
        sa.Column('source_tier', sa.String(16), nullable=False),
        sa.Column('llm_provider', sa.String(128), nullable=False),
        sa.Column('llm_model_version', sa.String(128), nullable=False),
        sa.Column('extraction_output', sa.JSON(), nullable=True),
        sa.Column('review_status', sa.String(32), nullable=False, server_default='pending'),
        sa.Column('reviewed_by', sa.String(255), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "source_tier IN ('tier1', 'tier2')",
            name='ck_distillation_source_tier'
        ),
        sa.CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name='ck_distillation_review_status'
        ),
    )

    # ── Section 5: Asset Layer Architecture ───────────────────────────────────

    op.create_table(
        'client_data_consent',
        sa.Column('consent_id', sa.String(36), primary_key=True),
        sa.Column('client_id', sa.String(36), nullable=False),
        sa.Column('consent_type', sa.String(64), nullable=False),
        sa.Column('consented_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('consented_by', sa.String(255), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "consent_type IN ('proprietary_only', 'contribute_to_universal')",
            name='ck_consent_type'
        ),
    )
    op.create_index('ix_client_data_consent_client_id', 'client_data_consent', ['client_id'])

    op.create_table(
        'asset_layer_version_snapshot',
        sa.Column('snapshot_id', sa.String(36), primary_key=True),
        sa.Column('layer_type', sa.String(32), nullable=False),
        sa.Column('client_id', sa.String(36), nullable=True),
        sa.Column('snapshot_data', sa.JSON(), nullable=False),
        sa.Column('triggered_by', sa.String(64), nullable=False),
        sa.Column('record_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "layer_type IN ('universal', 'client_proprietary')",
            name='ck_snapshot_layer_type'
        ),
        sa.CheckConstraint(
            "triggered_by IN ('auto_recalc', 'manual')",
            name='ck_snapshot_triggered_by'
        ),
    )


def downgrade() -> None:
    op.drop_table('asset_layer_version_snapshot')
    op.drop_index('ix_client_data_consent_client_id', table_name='client_data_consent')
    op.drop_table('client_data_consent')
    op.drop_table('distillation_job')
    op.drop_table('external_market_data')
    op.drop_index('ix_threshold_adj_log_config_id', table_name='threshold_adjustment_log')
    op.drop_table('threshold_adjustment_log')
    op.drop_table('threshold_config')
    op.drop_table('category_process_norm')
    op.drop_table('process_benchmark')
    op.drop_table('sku_main')
    op.drop_table('factory_capability')
    op.drop_table('overhead_profit_ref')
    op.drop_table('labor_cost_ref')
    op.drop_table('loss_rate_ref')
    op.drop_table('packaging_db')
    op.drop_index('ix_sku_process_attr_sku_process', table_name='sku_process_attribute')
    op.drop_index('ix_sku_process_attr_process_id', table_name='sku_process_attribute')
    op.drop_index('ix_sku_process_attr_sku_id', table_name='sku_process_attribute')
    op.drop_table('sku_process_attribute')
    op.drop_table('process_type_def')
    op.drop_table('accessory_db')
    op.drop_table('fabric_db')
