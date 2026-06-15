#!/usr/bin/env bash
# run_clean_db_validation.sh — Reproducible clean-state validation for abcdYi
set -euo pipefail
echo "=== abcdYi — Clean DB Validation ==="
echo "[1/7] Tearing down existing containers and volumes..."
docker compose down -v
echo "[2/7] Building images..."
docker compose build
echo "[3/7] Starting fresh database..."
docker compose up -d db
echo "[4/7] Running Alembic migrations..."
docker compose run --rm migrate
echo "[5/7] Starting API..."
docker compose up -d api
echo "[6/7] Checking API health..."
sleep 5
curl -f http://localhost:8000/health
echo "[7/7] Running test suite..."
uv run pytest tests/api/ tests/unit/ -v
echo "=== Validation complete ==="
