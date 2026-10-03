"""Execute the actual backend API workflow; the shared GLTG fixture is a mock.

This regression is not evidence of live MyAivan/dependency/channel integration.
"""
import ast
from pathlib import Path

from httpx import ASGITransport

from api.main import app
from scripts.run_v1_acceptance_apparel_order import run_acceptance


async def test_apparel_acceptance_uses_natural_api_transitions(seed_user):
    assert await run_acceptance(
        email=seed_user["email"], password=seed_user["password"], transport=ASGITransport(app=app),
    )


def test_acceptance_script_has_no_direct_database_dependency():
    script = Path(__file__).resolve().parents[2] / "scripts/run_v1_acceptance_apparel_order.py"
    imports = [node for node in ast.walk(ast.parse(script.read_text())) if isinstance(node, (ast.Import, ast.ImportFrom))]
    modules = [node.module or "" for node in imports if isinstance(node, ast.ImportFrom)]
    modules += [alias.name for node in imports if isinstance(node, ast.Import) for alias in node.names]
    assert not any(name.startswith(("src.db", "sqlalchemy", "sqlite3", "asyncpg", "psycopg")) for name in modules)
