# Test Baseline Report — abcdYi (Stage 1)

## Classification

| Category | Location | Count (files) | Notes |
|---|---|---|---|
| unit | `tests/unit/` | 44 | pure logic, no I/O |
| contract | GLTG CI mock (`tests/gltg_fake.py` + `tests/ci_gltg_server.py`) consumers | — | explicitly marked CI-only mock, never a runtime fallback |
| api | `tests/api/` | 16 | route-layer security incl. tenant isolation, auth |
| integration | `tests/integration/` (+ `integration` marker) | 12 | requires live migrated PostgreSQL |
| db | `tests/db/` | 6 | schema/migration behavior |
| e2e / component | root `tests/test_*` incl. `TestE2EScript` (subprocess role-switching script) and the AIVAN runtime suite | 36 | business-chain + component level |
| live / hardware-external | GPM smoke scripts; `scripts/run_aivan_private_domain_rfq_e2e.py` (needs the live GLTG service — its AIVAN-side GLTG API surface differs from the CI mock) | — | require real services/keys; excluded from CI by design |

No mock test is presented as live validation.

## Protected categories — retained and passing

Tenant isolation, approval replay protection (`consumed_at`), append-only
events, role switching, no silent fallback, migration up/down/up, API auth,
fail-closed startup guard, AIVAN human-approval / draft-only email policies.

## Core business E2E — retained and passing

`buyer requirement → canonical requirement → supplier selection → RFQ draft →
human approval → supplier response → quote comparison → GLTG feasibility →
decision packet → human approval → order/execution state` via the
role-switching E2E script plus `tests/api`/`tests/integration` suites.

## AIVAN product-level validation (integrated + standalone)

| Check | Result |
|---|---|
| Integrated entry: clean install → `uv run aivan --help` → `uv run aivan serve` → `GET /api/health` 200 `{"product":"AIVAN"}` | PASS |
| AIVAN → abcdYi workflow E2E (`scripts/run_aivan_e2e.py`): natural-language instruction → requirement structuring → supplier inquiry/reply → approval-gated draft ("Draft awaiting approval") → buyer options returned | PASS |
| Marketplace sourcing E2E (`scripts/run_aivan_marketplace_e2e.py`) | PASS |
| Standalone/API boundary: OpenClaw plugin smoke against the live AIVAN server (`scripts/run_aivan_openclaw_plugin_smoke_test.py`: health, event forwarding → project_id + recognised safety action, draft listing, approval-gate 404, no secret leakage) | PASS |
| Private-domain RFQ E2E | live/external — requires the real GLTG service |

## Continuous validation

Environment: clean `uv venv --python 3.11`, PostgreSQL 16 (fresh container),
GLTG CI mock on :8090 — same as CI. Five consecutive full-suite runs, no code
changes between runs (subsequent commits touched only documentation and the
wheel-packaging table, neither read by any test; a confirmation run after the
packaging fix also passed):

```
clean install:        PASS
compileall:           PASS
migration up/down/up: PASS (fresh database)
RUN 1: 1078 passed, 7 skipped   (122.64s)
RUN 2: 1078 passed, 7 skipped   (130.47s)
RUN 3: 1078 passed, 7 skipped   (125.00s)
RUN 4: 1078 passed, 7 skipped   (123.69s)
RUN 5: 1078 passed, 7 skipped   (124.31s)
confirmation run:     1078 passed, 7 skipped
wheel build:          PASS (src, api, and top-level aivan packages verified in the archive)
```

The 7 skips are environment-gated live tests, explicitly marked.

## Baseline comparison

Main (`574d28c`) in the same environment: 1078 passed / 7 skipped.
After Stage 1: identical — no behavioral test was added, removed, or changed;
the suite simply now runs on a consistent Python 3.11 dependency baseline.
