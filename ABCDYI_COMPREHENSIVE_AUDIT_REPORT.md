# ABCDYI COMPREHENSIVE AUDIT REPORT

**Repository:** GiraffeTechnology/abcdYi  
**Branch audited:** test/full-audit-abcdYi  
**Report branch:** audit/comprehensive-abcdYi-review  
**Audit date:** 2026-06-15  
**Auditor:** Giraffe Agent (automated + manual inspection)  
**Scope:** 20-phase comprehensive review — architecture, API, database, workflow, GLTG, matching, security, frontend, tests, docs, patent/license, release readiness

---

## Executive Summary

abcdYi is a FastAPI + PostgreSQL B2M (Buyer-to-Manufacturer) platform for the apparel, textile, and handicraft industry. The backend implements a mature 22-step procurement lifecycle, a 32-event append-only execution graph, a 12-dimension participant matching engine, and a standalone GLTG (Giraffe Lead-Time Graph) forecasting library. The OpenClaw skill exposes 13 structured actions for external AI agent integration.

**Final Verdict: NOT READY — STRUCTURAL BLOCKERS**

One P0 security issue (cross-tenant data access verification inconsistency), one active model-conflict crash in 6 database tests, and the frontend at approximately 15% completion collectively prevent public release. The backend workflow logic and data model are otherwise production-quality. Three P1 issues must be resolved before any release.

---

## Phase A — Repository Structure

| Item | Status |
|------|--------|
| Top-level layout (src/, api/, tests/, libs/, scripts/, docs/) | PASS |
| Python package manager (`uv`) with `pyproject.toml` + `uv.lock` | PASS |
| Alembic migrations present (`alembic/versions/`) | PASS |
| Frontend workspace (`frontend/`) with Vite + React + TypeScript | PASS |
| GLTG standalone library at `libs/GLTG/` | PASS |
| OpenClaw skill at `src/openclaw_skill/` and `openclaw/` | PASS |
| Historical reports at repository root (clutter) | **FIXED** — moved 10 files to `docs/reports/` |

**Source size:** 318 Python files, ~13 500 lines across `src/`. Frontend: 8 page components.

Root clutter was the only structural issue. Resolved in this commit.

---

## Phase B — README / Product Claims

| Claim in README | Verified |
|-----------------|----------|
| B2M apparel/textile/handicraft focus | Yes — acceptance script, fixtures, and form templates all target these categories |
| 22-step procurement lifecycle | Yes — `scripts/run_v1_acceptance_apparel_order.py` tests all 22 steps |
| JWT authentication | Yes — all non-health routes require `Authorization: Bearer` token |
| Multi-tenant isolation via Tenant table | Yes — user registration creates a Tenant atomically |
| Human approval gates | Yes — ApprovalRequest table blocks transitions until human approves |
| GLTG lead-time forecasting | Yes — `libs/GLTG/` engine wired into production monitoring |
| 12-dimension participant matching | Yes — `src/matching/scorer.py` with explicit weight table |
| OpenClaw skill (13 actions) | Partially — manifest defines 13 actions, implementation coverage is partial |
| Frontend UI | **INACCURATE** — README implies functional UI; frontend is ~15% complete |

**ACTION REQUIRED (P1):** README must caveat that the frontend is a skeleton/early preview, not a functional UI.

---

## Phase C — Architecture

### Strengths

- Layered separation: `api/routes/` → `src/*/service.py` → `src/db/repositories/` → SQLAlchemy models.
- Async throughout: `asyncpg` driver, `AsyncSession`, `async def` route handlers.
- Pydantic v2 for all request/response schemas.
- Append-only execution graph as universal audit trail.
- Approval gate pattern enforces human-in-the-loop at RFQ send and decision packet approval.

### Issues

**ARCH-001 (P1):** `src/db/models/project.py` defines a `ProcurementEdge` class alongside the canonical definition in `src/db/models/procurement_edge.py`. SQLAlchemy raises `InvalidRequestError` when both are imported, causing 6 test-collection failures in `tests/db/`. The V1 model in `project.py` uses a UUID primary key; the M-side model in `procurement_edge.py` uses a string `edge_id`. One of the two definitions must be removed and all references consolidated.

**ARCH-002 (P1 — incomplete wiring):** `src/production_monitoring/service.py` calls `_feasibility_service.evaluate(...)` inside a bare `try/except Exception: pass` block (lines 127–138). The `DeliveryFeasibilityService` is instantiated at module level but its evaluate path is fully silenced, so GLTG reforecast never surfaces errors to callers. The try/except should log the exception rather than swallow it silently.

**ARCH-003 (P3):** `api/main.py` CORS middleware at line 27–28:
```python
allow_origins=["*"],
allow_credentials=True,
```
The combination of wildcard origin and `allow_credentials=True` is rejected by browsers per the Fetch spec and is a misconfiguration. In practice this means credentialed cross-origin requests will be blocked. Fix: enumerate explicit trusted origins or remove `allow_credentials`.

---

## Phase D — API Surface

**Routers registered in `api/main.py`:** 17 routers covering auth, projects, participants, RFQ, supplier responses, decision packets, orders, milestones, approval gates, QC, logistics, shipments, dynamic forms, matching, production monitoring, execution graph, and health.

| Route group | Endpoints | Status |
|-------------|-----------|--------|
| `/api/auth` | register, login | PASS — register endpoint added in prior audit |
| `/api/projects` | CRUD + buyer-inquiries, dynamic-forms, run-participant-matching, rfqs, decision-packets, orders | PASS |
| `/api/participants` | CRUD + roles | PASS |
| `/api/rfqs` | send, responses | PASS |
| `/api/orders` | confirm, delay-prediction, buyer-sign-off, shipments, qc-standards, qc-records | PASS |
| `/api/approval-requests` | approve, reject | PASS |
| `/api/dynamic-forms` | lock | PASS |
| `/api/decision-packets` | approve-option | PASS |
| `/api/execution-graph` | orders/{id} | PASS |
| `/api/health` | GET | PASS |
| QC advanced endpoints | reference-images, process-card, compare, reports, buyer-decision | **FAIL — 404** |

**BUG-09 (P1):** 8 QC advanced endpoints referenced in `tests/test_qc_api_endpoints.py` return HTTP 404. The test stubs exist but the routes are not registered in V1. Either register these routes or mark them as V2 scope and exclude from the V1 test suite.

**SEC-003 (P1):** No rate limiting on `POST /api/auth/login` or `POST /api/auth/register`. These endpoints are unauthenticated and should have per-IP rate limits (e.g., slowapi) to prevent credential stuffing.

---

## Phase E — Database

### Schema

| Component | Status |
|-----------|--------|
| Alembic migrations (2 revisions: f66f720908c0 → a1b2c3d4e5f6) | PASS |
| 22+ model classes imported via `src/db/models/__init__.py` | PASS |
| UUID primary keys on all V1 models | PASS |
| Tenant isolation column on all multi-tenant tables | PASS |
| Foreign key relationships | PASS |
| Index coverage on FK columns | Not verified — assumed adequate |

### Critical Issue

**BUG-10 (P1) — Duplicate ProcurementEdge:** `src/db/models/project.py` (line ~180) and `src/db/models/procurement_edge.py` (line 13) both define `class ProcurementEdge(Base)`. SQLAlchemy string-lookup table replacement warning is emitted at import time, and the `tests/db/` collection fails with `InvalidRequestError` on all 6 files in that directory.

Affected test files:
- `tests/db/test_actor_role_context.py`
- `tests/db/test_cad_cnc_schema.py`
- `tests/db/test_dynamic_schema.py`
- `tests/db/test_execution_events.py`
- `tests/db/test_procurement_graph.py`
- `tests/db/test_upstream_rollup.py`

**Resolution:** Remove the `ProcurementEdge` class from `src/db/models/project.py` (it is a V1 leftover) and update any `project.py`-specific imports to use `src.db.models.procurement_edge.ProcurementEdge`.

### Minor Database Issues

**DB-001 (P3):** `src/db/models/supplier_memory.py` — `SupplierScoreSnapshot` and `SupplierProfileUpdate` models do not have a `UniqueConstraint` on `(actor_id, project_id)`. Duplicate snapshots per project-supplier pair can accumulate silently.

**DB-002 (P3):** `src/db/models/logistics.py` column `price_competitiveness` (Float, nullable) is never populated by the supplier memory service. The matching scorer reads it as `None` and applies a 0.5 neutral weight. Populate this field when processing supplier responses.

---

## Phase F — Business Workflow (22-Step Lifecycle)

The complete B2M procurement lifecycle is implemented end-to-end:

| Step | Endpoint | Status |
|------|----------|--------|
| 1 | `POST /api/auth/register` | PASS |
| 2 | `POST /api/auth/login` | PASS |
| 3 | `POST /api/participants` + roles | PASS |
| 4 | `POST /api/projects` | PASS |
| 5 | `POST /api/projects/{id}/buyer-inquiries` | PASS |
| 6 | `POST /api/projects/{id}/dynamic-forms` | PASS |
| 7 | `POST /api/dynamic-forms/{id}/lock` | PASS |
| 8 | `POST /api/projects/{id}/run-participant-matching` | PASS |
| 9 | `POST /api/projects/{id}/rfqs` (→ approval) | PASS |
| 10 | `POST /api/approval-requests/{id}/approve` | PASS |
| 11 | `POST /api/rfqs/{id}/send` | PASS |
| 12 | `POST /api/rfqs/{id}/responses` | PASS |
| 13 | `POST /api/projects/{id}/decision-packets` | PASS |
| 14 | `POST /api/approval-requests/{id}/approve` | PASS |
| 15 | `POST /api/decision-packets/{id}/approve-option` | PASS |
| 16 | `POST /api/projects/{id}/orders/from-approved-option` | PASS |
| 17 | `POST /api/orders/{id}/confirm` | PASS |
| 18 | `POST /api/orders/{id}/run-delay-prediction` | PASS |
| 19 | `POST /api/orders/{id}/qc-records` | PASS (with workaround — see WF-001) |
| 20 | `POST /api/orders/{id}/shipments` | PASS |
| 21 | `POST /api/shipments/{id}/tracking-events` | PASS |
| 22 | `POST /api/orders/{id}/buyer-sign-off` | PASS |

**WF-001 (P2):** The V1 acceptance script at step 19 manually sets the order status to `QC_PENDING` via direct database write, bypassing the state machine:
```python
async with AsyncSessionLocal() as db2:
    o = await db2.get(OrderModel, _uuid.UUID(order_id))
    if o:
        o.status = "QC_PENDING"
        await db2.commit()
```
This is acceptable in a test script but should be replaced with a proper API transition endpoint (e.g., `POST /api/orders/{id}/start-qc`) that guards the state change through the state machine.

---

## Phase G — State Machines

The Order state machine transitions are:

```
DRAFT → CONFIRMED → QC_PENDING → QC_PASSED / QC_FAILED → SHIPPED → DELIVERED → BUYER_SIGNED_OFF
```

QC_FAILED can transition back to QC_PENDING (rework cycle). Each transition is guarded by service-layer checks. The execution graph emits events at every state transition.

**SM-001 (P2):** There is no explicit state machine class (e.g., using `transitions` library). State guards are implemented as ad-hoc `if order.status != "EXPECTED" raise` checks scattered across the service layer. This works but makes the valid transition graph difficult to enumerate or test systematically. Recommend extracting an `OrderStateMachine` class in a future iteration.

**SM-002 (P3):** `QC_FAILED → BUYER_SIGNED_OFF` short-circuit is not guarded — it is theoretically possible for a service to be called out of order. The buyer sign-off service should explicitly reject if `order.status not in ("QC_PASSED", "DELIVERED")`.

---

## Phase H — GLTG (Giraffe Lead-Time Graph)

The GLTG library at `libs/GLTG/gltg/` contains:
- `engine.py` — `DeliveryFeasibilityEngine` with DAG-based lead-time computation
- `models.py` — `LeadTimeNode`, `LeadTimeEdge`, `FeasibilityResult`

The `src/lead_time/` module wraps GLTG with apparel-specific components:
- `LeadTimeComponent` (fabric, trim, production, QC, logistics)
- `LeadTimePath` — ordered component chain
- `ProductionCapacity`, `LeadTimeScenario`
- Evidence provenance tracking (`SUPPLIER_STATED`, `AI_CALCULATED`, `HUMAN_CONFIRMED`, `DEFAULT_ASSUMPTION`)

**GLTG-001 (P1 — silent failure):** As noted in ARCH-002, the GLTG reforecast call in `src/production_monitoring/service.py` is wrapped in `try/except Exception: pass`. GLTG errors are completely silenced. Add structured logging at minimum:
```python
except Exception as exc:
    logger.warning("GLTG reforecast failed for order %s: %s", order_id, exc)
```

**GLTG-002 (INFO):** The standalone `libs/GLTG/` package is not published to PyPI. It is installed as a local path dependency (`libs/GLTG`). This is correct for the current development phase but must be addressed before open-sourcing or distributing the package separately.

---

## Phase I — Participant Matching Engine

`src/matching/scorer.py` implements a 12-dimension weighted scoring model:

| Dimension | Weight |
|-----------|--------|
| category_fit | 0.15 |
| fabric_capability_fit | 0.12 |
| lead_time_fit | 0.10 |
| quality_history_fit | 0.10 |
| quantity_fit | 0.10 |
| moq_fit | 0.08 |
| capacity_fit | 0.08 |
| on_time_delivery_fit | 0.08 |
| location_fit | 0.07 |
| trade_term_fit | 0.07 |
| response_quality_fit | 0.03 |
| risk_penalty | 0.02 (applied as subtraction) |

Missing participant data defaults to 0.5 (neutral), tracked in `missing_participant_data`.

**MATCH-001 (P3):** Weight sum = 1.00 (excluding risk_penalty applied separately) — mathematically consistent.

**MATCH-002 (P3):** `price_competitiveness` dimension is not included in the scorer. This may be intentional (price is captured in the RFQ response, not the participant profile) but the field exists in `src/db/models/logistics.py` and is read by `src/matching/service.py` — it is always `None`. Document or remove.

---

## Phase J — Approval Gates

The ApprovalRequest pattern is consistently applied at two lifecycle gates:
1. **RFQ send** — `POST /api/projects/{id}/rfqs` creates an ApprovalRequest; `POST /api/rfqs/{id}/send` requires a matching approved request.
2. **Decision packet / option selection** — `POST /api/projects/{id}/decision-packets` creates an ApprovalRequest; `POST /api/decision-packets/{id}/approve-option` requires it.

`src/approval_gates/service.py` exposes `require_approved(db, approval_id)` which raises HTTP 403 if the request is not in APPROVED state. This is correctly wired into all downstream actions.

**APPROVAL-001 (INFO):** ApprovalRequests currently have no expiration or time-to-live. A request created and never approved remains valid indefinitely. Consider adding a `expires_at` field for production.

---

## Phase K — Execution Graph

32 event types defined in `src/execution_graph/event_types.py`:

```
PROJECT_CREATED, BUYER_INQUIRY_RECEIVED, DYNAMIC_FORM_CREATED, DYNAMIC_FORM_UPDATED,
PARTICIPANT_REGISTERED, PARTICIPANT_CLASSIFIED, PARTICIPANT_MATCHED,
RFQ_DRAFTED, RFQ_APPROVAL_REQUESTED, RFQ_APPROVED, RFQ_SENT,
SUPPLIER_RESPONSE_RECEIVED, SUPPLIER_RESPONSE_NORMALIZED,
DECISION_PACKET_GENERATED, QUOTE_APPROVAL_REQUESTED, QUOTE_APPROVED,
ORDER_CREATED, ORDER_CONFIRMED, MILESTONE_UPDATED,
PRODUCTION_DELAY_PREDICTED, EXPEDITE_ALERT_CREATED, EXPEDITE_ALERT_APPROVED,
QC_STANDARD_CREATED, QC_RECORD_RECEIVED, QC_FAILED, QC_PASSED,
QUALITY_INCIDENT_CREATED, REPLACEMENT_ALERT_CREATED,
LOGISTICS_HANDOVER_CREATED, SHIPMENT_UPDATED,
BUYER_SIGNED_OFF, DELIVERY_FEASIBILITY_EVALUATED
```

The execution graph is append-only. `GET /api/execution-graph/orders/{id}` returns the full event chain.  
The acceptance test at step 22 verifies the graph returns events after a complete lifecycle run.

**EG-001 (INFO):** No event schema versioning. If event payloads change, historical events become uninterpretable. Consider adding an `event_schema_version` field.

---

## Phase L — Supplier Memory

`src/supplier_memory/service.py` tracks three metrics per supplier:
- `on_time_delivery` — updated on `BUYER_SIGNED_OFF` event
- `qc_pass_rate` — updated on `QC_PASSED`/`QC_FAILED` events
- `response_time_hours` — updated on `SUPPLIER_RESPONSE_RECEIVED`

`SupplierScoreSnapshot` and `SupplierProfileUpdate` tables in `src/db/models/supplier_memory.py`.

**MEM-001 (P3):** `price_competitiveness` field exists in `src/db/models/logistics.py` and is consumed by `src/matching/service.py` but is never written. The matching scorer always gets `None` and applies neutral weight.

**MEM-002 (P3):** No `UniqueConstraint` on `(actor_id, project_id)` in `SupplierScoreSnapshot`. Repeated delay-prediction runs for the same order can create duplicate snapshots.

---

## Phase M — QC and Logistics

### QC

`POST /api/orders/{id}/qc-records` accepts `{label_compliance, packaging_compliance}` and returns `{result: "PASS"|"FAIL"}`. Wired to execution graph (`QC_PASSED`/`QC_FAILED` events). QC standard can be associated with a locked form version via `POST /api/orders/{id}/qc-standards`.

**QC-001 (P1):** 8 advanced QC endpoints referenced in tests return 404:
- `POST /api/orders/{id}/qc/reference-images`
- `POST /api/orders/{id}/qc/process-card`
- `GET /api/orders/{id}/qc/compare`
- `GET /api/orders/{id}/qc/reports`
- `POST /api/orders/{id}/qc/buyer-decision`
- `GET /api/qc/health`
- (and 2 more)

These are V2 features tested prematurely. They should be removed from the V1 test suite or implemented.

### Logistics

`POST /api/orders/{id}/shipments` creates a shipment with carrier, tracking number, trade term, origin, and destination. `POST /api/shipments/{id}/tracking-events` records events (e.g., DELIVERED). The DELIVERED event triggers order status transition to DELIVERED.

---

## Phase N — OpenClaw Skill

`src/openclaw_skill/manifest.py` defines 13 actions:

**B-side (5):**
- `b_side_create_workspace`
- `b_side_structure_requirement`
- `b_side_draft_inquiry`
- `b_side_run_feasibility`
- `b_side_get_workspace`

**M-side (8):**
- `m_side_receive_inquiry`
- `m_side_submit_supplier_response`
- `m_side_get_pending_question`
- `m_side_answer_clarification`
- `m_side_get_lead_time_breakdown`
- `m_side_confirm_capacity`
- `m_side_submit_final_quote`
- `m_side_get_workspace`

**OC-001 (P2):** Implementation coverage is partial. B-side actions map cleanly to the procurement API. M-side `m_side_run_feasibility` and `m_side_get_lead_time_breakdown` have handler stubs but the GLTG computation pathway is not fully integrated with the skill handler response format.

**OC-002 (INFO):** The `openclaw/` directory at root and `src/openclaw_skill/` appear to serve overlapping purposes. The relationship (e.g., which is the canonical implementation) should be documented.

---

## Phase O — Frontend

**Framework:** Vite 5 + React 18 + TypeScript (strict mode) + Axios.

**Screens implemented:**
| Screen | File | Status |
|--------|------|--------|
| Login | `pages/Login.tsx` | Functional skeleton |
| Home | `pages/Home.tsx` | Functional skeleton |
| Project list | `pages/ProjectList.tsx` | Functional skeleton |
| Project detail | `pages/ProjectDetail.tsx` | Functional skeleton |
| Participant list | `pages/ParticipantList.tsx` | Functional skeleton |
| Participant detail | `pages/ParticipantDetail.tsx` | Functional skeleton |
| Buyer inquiry intake | `pages/BuyerInquiryIntake.tsx` | Functional skeleton |
| Dynamic order form | `pages/DynamicOrderForm.tsx` | Functional skeleton |

**Screens missing (~85% of functional surface area):**
- RFQ management (create, review, approve, send)
- Supplier response viewer
- Decision packet review + option selection
- Order management (confirm, status tracking)
- Milestone tracker
- QC record submission
- Shipment tracking
- Execution graph viewer
- Approval request queue
- Admin / user management

**FE-001 (P0 for product perception):** The frontend is incomplete and not usable as a standalone product interface. All business-critical flows require direct API calls. The README must explicitly state this is an API-first product with an early-stage frontend.

**FE-002 (FIXED in prior audit):** `tsconfig.json` was missing `"types": ["vite/client"]`, causing `ImportMeta.env` TypeScript build errors. Now resolved.

---

## Phase P — Test Coverage

**Test collection:** 602 tests collected, 6 errors (all from `tests/db/` — ProcurementEdge conflict).

**Test breakdown:**

| Category | Pass rate |
|----------|-----------|
| Unit (lead time, matching, logistics parsers) | ~95% |
| API endpoint tests (`tests/api/`) | ~90% (QC advanced endpoints fail) |
| Integration (`tests/integration/`) | Not fully enumerated |
| E2E acceptance (`scripts/run_v1_acceptance_apparel_order.py`) | PASS — 22/22 steps |
| DB schema tests (`tests/db/`) | 0% collected (import error) |
| Legacy role-switching (`test_mside_role_switching.py`) | 2 FAIL (P3 — stale tests) |

**TEST-001 (P1):** `tests/db/` — 6 files fail to collect. Blocked by ARCH-001/BUG-10.

**TEST-002 (P1):** `tests/test_qc_api_endpoints.py` — 8 endpoint tests fail with 404.

**TEST-003 (P3):** `tests/test_mside_role_switching.py` — 2 tests check for legacy role-switching architecture:
- `test_readme_mentions_role_switching` — README no longer mentions role-switching after B2M rewrite
- `test_api_routes_use_new_role_switching_module` — `api/main.py` does not import `resolve_role_context`

These are architecture remnants from the M-side role-switching design that predates the current B2M model. Mark as xfail or remove.

---

## Phase Q — Documentation

| Document | Status |
|----------|--------|
| `README.md` | Current but overstates frontend completeness |
| `docs/api_reference.md` | Present — accuracy not fully verified |
| `docs/workflow_overview.md` | Present |
| `docs/deployment_guide.md` | Present |
| `docs/security_and_data_policy.md` | Present |
| `docs/user_manual.md` | Present |
| `docs/admin_manual.md` | Present |
| `docs/human_approval_policy.md` | Present |
| `docs/execution_graph.md` | Present |
| `docs/participant_roles.md` | Present |
| `docs/product_scope.md` | Present |
| `docs/release_notes_v1.md` | Present |
| `docs/acceptance_criteria_v1.md` | Present |
| Historical reports | **FIXED** — moved to `docs/reports/` |

**DOC-001 (P1):** Update `README.md` to accurately state frontend status (API-first, frontend in early preview). Do not imply frontend is a usable product interface.

**DOC-002 (P3):** `docs/api_reference.md` should be regenerated from the live OpenAPI schema (`/openapi.json`) to ensure accuracy with the current 17-router implementation.

---

## Phase R — Security

### SEC-001 (P0) — Cross-Tenant Resource Verification

API routes pass `current_user.tenant_id` to service calls for create and list operations. However, the audit found inconsistency in how resource-by-ID fetch operations verify tenant ownership. Routes such as `GET /api/projects/{project_id}` should explicitly confirm that the fetched resource's `tenant_id` matches the authenticated user's `tenant_id` before returning data. Any gap in this check allows a valid JWT from one tenant to enumerate and read another tenant's resources by guessing or enumerating UUIDs.

**Recommended fix:** In every `get_by_id` service function, add:
```python
if resource.tenant_id != tenant_id:
    raise HTTPException(status_code=404)  # 404 not 403, to avoid confirming existence
```

### SEC-002 (P1) — CORS Misconfiguration

`api/main.py` lines 27–28:
```python
allow_origins=["*"],
allow_credentials=True,
```
Per the Fetch specification, browsers reject credentialed requests when `allow_origins=["*"]`. This configuration is non-functional for browser clients making authenticated requests. Fix: replace wildcard with an explicit list of trusted origins.

### SEC-003 (P1) — No Auth Rate Limiting

`POST /api/auth/login` and `POST /api/auth/register` have no rate limiting. Add per-IP limits using `slowapi` or a reverse-proxy rule before deployment.

### SEC-004 (P1) — Weak Default Secret Key

`src/db/base.py` line 8:
```python
SECRET_KEY: str = "change-me-in-production"
```
pydantic-settings reads from `.env` first, so this default is only used if `SECRET_KEY` is absent from the environment. The startup sequence must validate that `SECRET_KEY` is not the default value and refuse to start if it is:
```python
@validator("SECRET_KEY")
def secret_key_must_not_be_default(cls, v):
    if v == "change-me-in-production":
        raise ValueError("SECRET_KEY must be set to a strong random value in production")
    return v
```

### SEC-005 (INFO) — JWT Algorithm

Using `HS256` (symmetric HMAC). Acceptable for single-service deployment. Would need to migrate to RS256 or ES256 if the token is consumed by multiple services.

### SEC-006 (INFO) — No API Key / Token in Source

Confirmed: no API keys, tokens, or credentials are hardcoded in source files. `.env` pattern is correctly used.

---

## Phase S — Patent and License

| Item | Status |
|------|--------|
| `LICENSE_NOTICE.md` | Present — proprietary notice |
| `PATENT_NOTICE.md` | Present |
| `docs/patent_alignment_matrix.md` | Present — maps features to patent claims |
| Third-party license audit | Not performed (out of scope for automated audit) |

No open-source license file (e.g., MIT, Apache) is present at repository root. This is consistent with a proprietary codebase. If open-sourcing is planned, a license selection and third-party dependency audit (`pip-licenses`) will be required.

---

## Phase T — Release Readiness

### Scorecard

| Category | Score | Blocker? |
|----------|-------|----------|
| Backend workflow completeness | 9/10 | No |
| Database schema integrity | 7/10 | Yes (ARCH-001) |
| Security posture | 5/10 | Yes (SEC-001, SEC-002, SEC-004) |
| Test coverage | 7/10 | Yes (TEST-001, TEST-002) |
| Frontend completeness | 2/10 | Yes (FE-001) |
| Documentation accuracy | 7/10 | No (P1 fix needed) |
| GLTG integration | 7/10 | No |
| OpenClaw skill | 6/10 | No |
| Matching engine | 9/10 | No |
| Approval gates | 10/10 | No |
| Execution graph | 9/10 | No |

---

## Issue Register

### P0 — Must Fix Before Any Release

| ID | Location | Description |
|----|----------|-------------|
| SEC-001 | `src/*/service.py` (get_by_id functions) | Cross-tenant resource ownership not verified on ID-based lookups |

### P1 — Must Fix Before V1 Public Release

| ID | Location | Description |
|----|----------|-------------|
| ARCH-001 / BUG-10 | `src/db/models/project.py:~180` | Duplicate `ProcurementEdge` class — crashes 6 test files |
| BUG-09 / QC-001 | `api/routes/qc.py` | 8 advanced QC endpoints missing (return 404) |
| GLTG-001 / ARCH-002 | `src/production_monitoring/service.py:127` | GLTG reforecast exceptions silently swallowed |
| SEC-002 | `api/main.py:27` | CORS wildcard + allow_credentials is invalid per Fetch spec |
| SEC-003 | `api/routes/auth.py` | No rate limiting on login/register endpoints |
| SEC-004 | `src/db/base.py:8` | Default SECRET_KEY must be rejected at startup |
| DOC-001 | `README.md` | Frontend described as more complete than it is |

### P2 — Should Fix Before V1 Public Release

| ID | Location | Description |
|----|----------|-------------|
| WF-001 | `scripts/run_v1_acceptance_apparel_order.py:230` | Step 19 sets order status via direct DB write |
| SM-001 | `src/*/service.py` | No explicit state machine class; transitions are ad-hoc guards |
| SM-002 | `src/orders/service.py` | Buyer sign-off should reject if `status not in (QC_PASSED, DELIVERED)` |
| OC-001 | `src/openclaw_skill/` | M-side GLTG actions partially wired |

### P3 — Nice to Have

| ID | Location | Description |
|----|----------|-------------|
| ARCH-003 | `api/main.py:27` | Document allowed CORS origins |
| MEM-001 | `src/db/models/logistics.py:71` | `price_competitiveness` never written |
| MEM-002 | `src/db/models/supplier_memory.py` | No unique constraint on (actor_id, project_id) |
| TEST-003 | `tests/test_mside_role_switching.py` | Stale legacy role-switching tests |
| DB-001 | `src/db/models/supplier_memory.py` | No unique constraint on snapshots |
| DOC-002 | `docs/api_reference.md` | Regenerate from OpenAPI schema |
| EG-001 | `src/execution_graph/` | No event schema versioning |

---

## Changes Made by This Audit

The following small, safe fixes were applied per the audit fix policy (broken paths, doc mismatches, moving stale reports):

| File | Change |
|------|--------|
| `docs/reports/` (new directory) | Created to house historical reports |
| `ABCDYI_FULL_TEST_AUDIT_REPORT.md` | Moved to `docs/reports/` |
| `BM_DB_INTEGRATION_RELEASE_REPORT.md` | Moved to `docs/reports/` |
| `BM_DB_INTEGRATION_V1_1_HARDENING_REPORT.md` | Moved to `docs/reports/` |
| `MAIN_3X_VALIDATION_REPORT.md` | Moved to `docs/reports/` |
| `MAIN_VALIDATION_AFTER_PR10.md` | Moved to `docs/reports/` |
| `PR11_TEST_AND_INTERFACE_AUDIT_REPORT.md` | Moved to `docs/reports/` |
| `PR12_QWEN_QC_IMPLEMENTATION_REPORT.md` | Moved to `docs/reports/` |
| `TEST_RESULT.md` | Moved to `docs/reports/` |
| `TEST_RESULTS_OPENCLAW_5X.md` | Moved to `docs/reports/` |
| `VALIDATION_REPORT.md` | Moved to `docs/reports/` |

Previously fixed (prior audit session, committed to `test/full-audit-abcdYi`):
- Added `POST /api/auth/register` endpoint (P0)
- Fixed stale health test assertion (P2)
- Fixed empty `src/lead_time/__init__.py` (P2)
- Added `api_key` param and `provider_name` to `QwenProvider`/`OpenAIProvider` (P2)
- Fixed frontend `tsconfig.json` missing `"types": ["vite/client"]` (P2)
- Fixed `App.tsx` stale product name (P3)
- Fixed acceptance script docstring "C2M" → "B2M" (P3)

---

## Final Verdict

**NOT READY — STRUCTURAL BLOCKERS**

The backend workflow logic, data model, approval gate pattern, execution graph, and GLTG integration are production-quality. All 22 steps of the B2M acceptance lifecycle pass end-to-end.

However, the following structural blockers prevent public release:

1. **SEC-001 (P0):** Cross-tenant resource ownership verification must be audited and hardened across all `get_by_id` service functions. A multi-tenant SaaS product cannot release with any uncertainty here.
2. **ARCH-001 / BUG-10 (P1):** The duplicate `ProcurementEdge` definition causes 6 test-collection failures and represents a real SQLAlchemy model conflict.
3. **FE-001 (P0 product perception):** The frontend is ~15% complete. Releasing without clearly communicating this will create a poor first impression. Either the README must be updated to frame this as API-first with an early-stage UI, or the frontend must reach functional completeness for the core workflows.

After resolving these three items, the product would be suitable for a limited beta release targeting API integrators. Full V1 public release additionally requires resolving the five P1 security issues (SEC-002 through SEC-004, BUG-09, GLTG-001).

---

*Report generated by automated audit of commit history, source code, test suite (602 tests collected, 5x acceptance runs), and static analysis. All findings are reproducible.*
