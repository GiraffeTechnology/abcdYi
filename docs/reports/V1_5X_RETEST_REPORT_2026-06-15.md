# abcdYi V1 Acceptance — 5× Clean-State Retest Report

**Date:** 2026-06-15 20:06 UTC  
**Branch:** audit/comprehensive-abcdYi-review  
**Environment:** PostgreSQL 16 (local), FastAPI + asyncpg, Python 3.11, uv  
**Script:** `scripts/run_v1_acceptance_apparel_order.py` (22-step B2M lifecycle)

---

## Method

Each run used a fully clean state:

1. Kill running server
2. `DROP DATABASE apparel_textile`
3. `CREATE DATABASE apparel_textile OWNER giraffe`
4. `uv run alembic upgrade head` (2 migrations: f66f720908c0 → a1b2c3d4e5f6)
5. Start `uvicorn api.main:app`
6. Verify `GET /health` → 200 OK
7. Run acceptance script

---

## 22-Step Acceptance Results

| Run | User | Step 17 Status | Step 18 Risk | Step 19 QC | Final Status | Result |
|-----|------|----------------|--------------|------------|--------------|--------|
| 1 | acceptance-200258@giraffe.technology | IN_PRODUCTION | ON_TRACK | QC_PASSED | BUYER_SIGNED_OFF | **PASS** |
| 2 | acceptance-200344@giraffe.technology | IN_PRODUCTION | ON_TRACK | QC_PASSED | BUYER_SIGNED_OFF | **PASS** |
| 3 | acceptance-200358@giraffe.technology | IN_PRODUCTION | ON_TRACK | QC_PASSED | BUYER_SIGNED_OFF | **PASS** |
| 4 | acceptance-200411@giraffe.technology | IN_PRODUCTION | ON_TRACK | QC_PASSED | BUYER_SIGNED_OFF | **PASS** |
| 5 | acceptance-200426@giraffe.technology | IN_PRODUCTION | ON_TRACK | QC_PASSED | BUYER_SIGNED_OFF | **PASS** |

**5 / 5 PASS — execution graph recorded 10 events per run**

---

## Step-by-Step Trace (Representative — Run 1)

```
[01] User registered: acceptance-200258@giraffe.technology
[02] Logged in, token acquired
[03] Participant created: 018262f7...
[04] Project created: 6473e7f2...
[05] Buyer inquiry created: 34a26423...
[06] Dynamic form created: fe3366f8...
[07] Form locked
[08] Participant matching run: 1 matches
[09] RFQ created: 69a1be0c... (approval: fee8c806...)
[10] RFQ send approved
[11] RFQ sent to supplier
[12] Supplier response recorded
[13] Decision packet generated: faffac4a...
[14] Decision packet approved
[15] Option approved
[16] Order created: 534050f5...
[17] Order confirmed — status: IN_PRODUCTION
[18] Delay prediction: ON_TRACK
[19] QC record submitted — result: QC_PASSED
[20] Shipment created: 9590c4c1...
[21] Delivery event recorded — order now DELIVERED
[22] Buyer signed off — final status: BUYER_SIGNED_OFF
[22] Execution graph: 10 events recorded

GIRAFFE APPAREL & TEXTILE V1 ACCEPTANCE: PASS
```

---

## pytest Suite Results

Run against the same final DB state after Run 5 (server still up).

### Passing suite (excluding known-broken files)

```
uv run pytest tests/ --ignore=tests/db \
  --ignore=tests/test_qc_api_endpoints.py \
  --ignore=tests/test_mside_role_switching.py -q
```

**515 passed, 3 warnings in 78.78s**

### Known-failing tests (pre-existing issues, not regressions)

| File | Count | Root cause | Severity |
|------|-------|------------|----------|
| `tests/db/test_actor_role_context.py` | ERROR (collection) | Duplicate `ProcurementEdge` SQLAlchemy model | P1 |
| `tests/db/test_cad_cnc_schema.py` | ERROR (collection) | Same | P1 |
| `tests/db/test_dynamic_schema.py` | ERROR (collection) | Same | P1 |
| `tests/db/test_execution_events.py` | ERROR (collection) | Same | P1 |
| `tests/db/test_procurement_graph.py` | ERROR (collection) | Same | P1 |
| `tests/db/test_upstream_rollup.py` | ERROR (collection) | Same | P1 |
| `tests/test_qc_api_endpoints.py` (8 tests) | 8 FAIL | Advanced QC routes not implemented in V1 (HTTP 404) | P1 |
| `tests/test_mside_role_switching.py` (2 tests) | 2 FAIL | Stale legacy architecture tests; M-side role-switching replaced by B2M model | P3 |

**Total failures: 10 FAIL + 6 collection errors** — identical to prior audit. No regressions introduced.

### Warnings (non-blocking)

| Warning | Source | Impact |
|---------|--------|--------|
| `PydanticDeprecatedSince20` — class-based config | `src/db/base.py:6` | None — works in Pydantic V2, removed in V3 |
| `DeprecationWarning: 'crypt' is deprecated` | passlib + Python 3.13 | None — Python 3.11 in use |
| `DeprecationWarning: HTTP_422_UNPROCESSABLE_ENTITY` | FastAPI routing | None — cosmetic |

---

## Summary

| Metric | Result |
|--------|--------|
| 5× clean-state acceptance runs | **5 / 5 PASS** |
| pytest passing (scoped) | **515 / 515** |
| pytest known-failing (pre-existing) | 10 FAIL + 6 errors |
| New regressions introduced | **0** |
| Final order status in all runs | **BUYER_SIGNED_OFF** |
| Delay risk in all runs | **ON_TRACK** |
| QC result in all runs | **QC_PASSED** |

The V1 B2M acceptance lifecycle is stable across 5 independent clean-state runs. All failures are pre-existing, documented in `ABCDYI_COMPREHENSIVE_AUDIT_REPORT.md`, and unchanged from the prior audit session.
