# abcdYi Validation Report

## Product Positioning Fix

- Repositioned from C2M to B2M across README, PATENT_NOTICE.md, docs/product_scope.md, docs/patent_alignment_matrix.md, docs/user_manual.md, docs/release_notes_v1.md, docs/acceptance_criteria_v1.md, docs/final_status_report.md, docs/product_scope_v1.md, src/legal/patent_notice.py.
- Removed blockchain, virtual fitting, AR, and VR references from README and all primary product docs.
- Official patent titles preserved unchanged as registered legal titles.
- Added "Why B2M" section defining buyer role explicitly.
- Added core user statement: "The core user is not an end consumer."
- Clarification added: official patent titles retain C2M as registered legal titles; abcdYi product implementation is B2M.
- Dockerfile.api fixed: copies libs/GLTG before uv sync.
- scripts/run_clean_db_validation.sh updated to 8-step validation.
- Makefile updated: test-unit, test-integration, validate, docker-validate targets.

## Test Organisation Fix

- Moved `tests/unit/test_migrations.py` (DB-dependent) to `tests/integration/test_migrations.py`.
- Both migration tests marked `@pytest.mark.integration`.
- Added `delivery_feasibility_packets` to expected tables list.
- Registered `integration` marker in `pyproject.toml`.
- Unit test command: `uv run pytest tests/unit/ -v -m "not integration"` — runs without any database.
- Integration test command: `uv run pytest tests/integration/ -v` — requires migrated PostgreSQL.

---

## grep — Forbidden Terms Scan

Command:
```bash
grep -Rni "C2M\|blockchain\|virtual fitting\|AR/VR" README.md PATENT_NOTICE.md LICENSE_NOTICE.md docs src api tests || true
```

Result: **No product-level matches.** C2M appears only inside official patent titles (registered legal titles in Chinese and Japanese). No blockchain, virtual fitting, AR/VR in any product positioning file.

---

## Validation Runs

All three runs were executed against a live PostgreSQL 16 instance with fresh Alembic migrations applied.

Migration applied before runs:
```
INFO  Running upgrade  -> f66f720908c0, iter1_initial_schema
INFO  Running upgrade f66f720908c0 -> a1b2c3d4e5f6, add_delivery_feasibility_packets
```

### Run 1

```bash
uv run pytest tests/unit/ -v -m "not integration"
# 50 passed, 2 warnings in 0.13s

DATABASE_URL="postgresql+asyncpg://giraffe:giraffe@localhost:5432/apparel_textile" \
  SECRET_KEY="test-secret" \
  uv run pytest tests/integration/ -v
# 2 passed, 2 warnings in 0.11s
```

Unit tests: **52 items total — 50 unit + 2 integration**
- `tests/integration/test_migrations.py::test_all_tables_exist` PASSED
- `tests/integration/test_migrations.py::test_execution_events_table_has_no_pk_update` PASSED

### Run 2

```bash
uv run pytest tests/unit/ -q -m "not integration"
# 50 passed, 2 warnings in 0.09s

DATABASE_URL="postgresql+asyncpg://giraffe:giraffe@localhost:5432/apparel_textile" \
  SECRET_KEY="test-secret" \
  uv run pytest tests/integration/ -q
# 2 passed, 2 warnings in 0.09s
```

### Run 3

```bash
uv run pytest tests/unit/ -q -m "not integration"
# 50 passed, 2 warnings in 0.09s

DATABASE_URL="postgresql+asyncpg://giraffe:giraffe@localhost:5432/apparel_textile" \
  SECRET_KEY="test-secret" \
  uv run pytest tests/integration/ -q
# 2 passed, 2 warnings in 0.10s
```

---

## Validation Status

| Check | Status | Notes |
|---|---|---|
| Unit tests (50 tests, no DB) | **PASS** | 50/50 across all 3 runs |
| Integration tests (2 migration tests) | **PASS** | 2/2 across all 3 runs; requires migrated PostgreSQL |
| Alembic migration | **PASS** | Both migrations applied cleanly (iter1_initial_schema → add_delivery_feasibility_packets) |
| Docker build | **PENDING** | Docker daemon not available in this environment; Dockerfile.api is ready with GLTG fix |
| API health check | **PENDING** | Requires Docker or running API process |
| Full clean validation run 1 | **PASS** (unit + integration) | See run 1 above |
| Full clean validation run 2 | **PASS** (unit + integration) | See run 2 above |
| Full clean validation run 3 | **PASS** (unit + integration) | See run 3 above |
| C2M grep clean (product-level) | **PASS** | No product-level C2M outside official patent titles |
| blockchain / virtual fitting grep | **PASS** | No forbidden terms in product positioning docs |

## Final Result

**Unit tests: PASS — 50/50, 3 consecutive runs.**

**Integration tests: PASS — 2/2, 3 consecutive runs.**

**Docker build and API health check: PENDING** — Docker daemon is not available in this remote execution environment. The `scripts/run_clean_db_validation.sh` script is ready and must be run in an environment with Docker to complete the full 8-step validation including Docker build and API health check.

Do not mark the full `scripts/run_clean_db_validation.sh` path as PASS until all 8 steps complete successfully across 3 consecutive runs in a Docker environment.
