# Test Baseline Report — abcdYi (Stage 1)

## Classification (Phase E.1)

| Category | Location | Count (files) | Notes |
|---|---|---|---|
| unit | `tests/unit/` | 44 | pure logic, no I/O |
| contract | `tests/gltg_fake.py` + `tests/ci_gltg_server.py` consumers (`tests/unit/test_gltg_*`, feasibility/rollup suites) | — | GLTG contract mock, **explicitly marked CI-only**, never a runtime fallback |
| api | `tests/api/` | 16 | route-layer security incl. tenant isolation, auth |
| integration | `tests/integration/` (+ `integration` pytest marker) | 12 | requires live migrated PostgreSQL |
| db | `tests/db/` | 6 | schema/migration behavior |
| e2e | root `tests/test_*` incl. `TestE2EScript` (runs `scripts/run_role_switching_mvp.py` as subprocess) | 35 | full business-chain scripts |
| live / hardware-external | GPM smoke scripts (`scripts/run_gpm_*`), not in default suite | — | require real keys/models; excluded from CI by design |

No mock test is presented as live validation; the GLTG mock server carries an
explicit "CI/test infrastructure only" docstring.

## Deleted tests (Phase E.2)

- `tests/test_aivan_embedded_runtime.py` — verified only the deleted embedded
  AIVAN runtime (PRD-deletable category: "only verifies a deleted implementation").

Protected categories all retained and passing: tenant isolation, approval
replay protection (consumed_at), append-only events, role switching, no silent
fallback, migration up/down/up, API auth, fail-closed startup guard.

## Core E2E chain (Phase E.3) — retained and passing

`buyer requirement → canonical requirement → supplier selection → RFQ draft →
human approval → supplier response → quote comparison → GLTG feasibility →
decision packet → human approval → order/execution state` is exercised by the
role-switching E2E script test plus `tests/api`/`tests/integration` suites
(RFQ, supplier_responses, decision_packets, approval_gates, orders,
execution_graph). GLTG feasibility runs against the marked contract mock when
the live service is absent.

## Continuous validation (Phase E.4)

Environment: clean `uv venv --python 3.11`, PostgreSQL 16 (fresh container),
GLTG CI mock on :8090. All five runs from commit `207c741`, no code changes
between runs:

```
clean install:        PASS
compileall:           PASS
migration up/down/up: PASS (fresh database)
core E2E:             PASS (within suite)
RUN 1: 1077 passed, 7 skipped   (96.25s)
RUN 2: 1077 passed, 7 skipped   (95.09s)
RUN 3: 1077 passed, 7 skipped   (98.15s)
RUN 4: 1077 passed, 7 skipped   (97.64s)
RUN 5: 1077 passed, 7 skipped   (99.20s)
```

The 7 skips are environment-gated live tests (real GLTG integration etc.),
explicitly marked.

## Baseline comparison

- Before (main `574d28c`): 1081 passed / 7 skipped (same environment; includes
  the 4 embed-only tests deleted with `src/aivan`).
- After: 1077 passed / 7 skipped, 0 failed — no behavioral test lost; the
  delta is exactly the deleted embed-only test file.
