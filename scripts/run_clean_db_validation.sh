#!/usr/bin/env bash
# run_clean_db_validation.sh — Reproducible clean-state test run
# Usage: ./scripts/run_clean_db_validation.sh
set -euo pipefail

echo "=== abcdYi — Clean DB Validation ==="
echo ""

echo "[1/5] Tearing down existing containers and volumes..."
docker compose down -v

echo "[2/5] Starting fresh database..."
docker compose up -d db

echo "[3/5] Waiting for database to be ready..."
sleep 6

echo "[4/5] Running Alembic migrations..."
uv run alembic upgrade head

echo "[5/5] Running test suite..."
uv run pytest tests/api/ tests/unit/ -v

echo ""
echo "=== Validation complete ==="
