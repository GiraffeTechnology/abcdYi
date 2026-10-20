"""Execute the actual backend API workflow; the shared GLTG fixture is a mock.

This regression is not evidence of live MyAivan/dependency/channel integration.
"""
import ast
from pathlib import Path

from httpx import ASGITransport

from api.main import app
from scripts.run_v1_acceptance_apparel_order import run_acceptance


async def test_apparel_acceptance_uses_natural_api_transitions(seed_user, monkeypatch):
    async def synthetic_response(raw_text, rfq_content):
        assert "Unit price USD 8.50" in raw_text
        return {"unit_price": 8.5, "currency": "USD", "moq": 500,
            "fabric_lead_time_days": 20, "trim_lead_time_days": 15, "production_time_days": 25,
            "qc_time_days": 5, "logistics_time_days": 7, "total_lead_time_days": 52,
            "capacity_available": 15000, "missing_fields": ["sample_time_days", "packaging_time_days"],
            "evidence_source": {"source": "synthetic response parser fixture; not a live model result"}}
    monkeypatch.setattr("src.supplier_responses.service.normalize_supplier_response", synthetic_response)
    assert await run_acceptance(
        email=seed_user["email"], password=seed_user["password"], transport=ASGITransport(app=app),
    )


def test_acceptance_script_has_no_direct_database_dependency():
    script = Path(__file__).resolve().parents[2] / "scripts/run_v1_acceptance_apparel_order.py"
    imports = [node for node in ast.walk(ast.parse(script.read_text())) if isinstance(node, (ast.Import, ast.ImportFrom))]
    modules = [node.module or "" for node in imports if isinstance(node, ast.ImportFrom)]
    modules += [alias.name for node in imports if isinstance(node, ast.Import) for alias in node.names]
    assert not any(name.startswith(("src.db", "sqlalchemy", "sqlite3", "asyncpg", "psycopg")) for name in modules)
