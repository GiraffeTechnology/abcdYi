#!/usr/bin/env bash
# run_clean_db_validation.sh — Reproducible clean-state validation for abcdYi
set -euo pipefail
echo "=== abcdYi — Clean DB Validation ==="
echo "[1/8] Tearing down existing containers and volumes..."
docker compose down -v
echo "[2/8] Building images..."
docker compose build
echo "[3/8] Starting fresh database..."
docker compose up -d db
echo "[4/8] Running Alembic migrations..."
docker compose run --rm migrate
echo "[5/8] Starting API..."
docker compose up -d api
echo "[6/8] Checking API health..."
sleep 5
curl -f http://localhost:8000/health
echo ""
echo "[7/8] Running unit tests (no DB required)..."
uv run pytest tests/unit/ -v -m "not integration"
echo "[8/8] Running integration tests (requires migrated DB)..."
uv run pytest tests/integration/ -v
echo "=== Validation complete ==="
