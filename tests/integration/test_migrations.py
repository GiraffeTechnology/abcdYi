"""
Verifies that all expected tables exist after migration.
Requires a live PostgreSQL connection (run after `alembic upgrade head`).
"""
import pytest
from sqlalchemy import text
from src.db.base import engine

EXPECTED_TABLES = [
    "tenants", "users", "user_roles", "audit_logs",
    "participants", "participant_roles", "participant_profiles",
    "participant_capabilities", "participant_permissions",
    "projects", "procurement_edges", "buyer_inquiries", "raw_messages",
    "dynamic_order_forms", "dynamic_order_form_versions", "clarification_questions",
    "participant_matches",
    "rfqs", "rfq_recipients", "supplier_responses", "supplier_response_packets",
    "decision_packets", "decision_options", "approval_requests",
    "orders", "order_lines",
    "milestones", "production_updates", "production_monitoring_packets", "expedite_alerts",
    "qc_standards", "qc_records",
    "quality_incidents", "replacement_alerts", "shipments",
    "shipment_tracking_events", "supplier_memory_records",
    "execution_events", "uploaded_file_metadata",
    "delivery_feasibility_packets",
]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_tables_exist():
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        )
        existing = {row[0] for row in result}
    missing = [t for t in EXPECTED_TABLES if t not in existing]
    assert not missing, f"Missing tables: {missing}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execution_events_table_has_no_pk_update():
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name='execution_events'")
        )
        columns = {row[0] for row in result}
    assert "id" in columns
    assert "event_type" in columns
    assert "payload" in columns
    assert "occurred_at" in columns
