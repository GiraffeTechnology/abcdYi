# GLTG Full Audit — abcdYi
**Repository:** GiraffeTechnology/abcdYi  
**Audit Date:** 2026-06-27  
**Auditor:** Automated audit session (branch `claude/gltg-full-audit-bpovyp`)  
**Scope:** `libs/GLTG/` (Python library), `src/lead_time/gltg_adapter.py`, `src/services/delivery_feasibility_service.py`, `src/decision_packets/service.py`, `src/production_monitoring/service.py`, `api/` (FastAPI host)

---

## Step 1 — Repository Inventory

### 1.1 GLTG Library (`libs/GLTG/`)

```
libs/GLTG/
├── gltg/
│   ├── __init__.py          (exports: LeadTimeGraphEngine, ApparelOrderInput,
│   │                          DeliveryFeasibilityPacket, DeliveryPath,
│   │                          DependencyEdge, ParticipantNode)
│   ├── engine.py            (LeadTimeGraphEngine.evaluate + helpers)
│   └── models.py            (all dataclasses)
└── pyproject.toml           (name=gltg, version=0.1.0, no runtime deps)
```

### 1.2 `libs/GLTG/pyproject.toml`

| Field | Value |
|---|---|
| Project name | `gltg` |
| Version | `0.1.0` |
| Python requires | `>=3.11` |
| Runtime dependencies | none |
| Build backend | `hatchling` |

### 1.3 Integration touchpoints

| File | Role |
|---|---|
| `src/lead_time/gltg_adapter.py` | Canonical adapter — builds `ApparelOrderInput` from DB, calls `LeadTimeGraphEngine` |
| `src/services/delivery_feasibility_service.py` | Service layer — calls adapter, persists `DeliveryFeasibilityPacketRecord`, emits event |
| `src/decision_packets/service.py` | **Violation** — imports `gltg.models` directly, bypasses adapter |
| `src/production_monitoring/service.py` | Calls `DeliveryFeasibilityService.evaluate()` after delay detection |
| `src/db/models/delivery_feasibility.py` | SQLAlchemy model for `delivery_feasibility_packets` table |
| `alembic/versions/a1b2c3d4e5f6_add_delivery_feasibility_packets.py` | Migration that creates the table |

### 1.4 Test files

| File | Type | Status |
|---|---|---|
| `tests/unit/test_gltg_engine_date_buffers.py` | Unit | 3 × `xfail` stubs (created this audit) |
| `tests/unit/test_gltg_adapter_reliability.py` | Unit | 1 × `xfail` stub (created this audit) |
| `tests/integration/test_gltg_reforecast_integration.py` | Integration | 3 × `xfail` stubs (created this audit) |

---

## Step 2 — API Surface Exposed by abcdYi

> **Note:** The GLTG library has no HTTP interface of its own. It is embedded in abcdYi
> (`api/main.py`, version `1.0.0`). The GLTG-relevant HTTP endpoints are listed below.

### `GET /health`

| Field | Value |
|---|---|
| Handler | `api/routes/health.py::health_check` |
| Response | `{"status": "ok", "product": "abcdYi — Giraffe Agent Apparel..."}` |
| Version field | **None** |

### `POST /api/projects/{project_id}/decision-packets`

| Field | Value |
|---|---|
| Handler | `api/routes/decision_packets.py::create_decision_packet` |
| Request body | `{"rfq_id": "<uuid>"}` |
| Auth | JWT bearer, `tenant_id` claim required |
| GLTG path | Calls `generate_decision_packet()` → **direct** `gltg.models` import (architecture violation) |
| Response on success | `{"packet": DecisionPacketOut, "approval_request_id": "<uuid>"}` |
| GLTG result surfaced | `DecisionOption.lead_time_breakdown["gltg"]` (not persisted to `delivery_feasibility_packets`) |

### `POST /api/projects/{project_id}/delivery-feasibility` (via service)

| Field | Value |
|---|---|
| Entry point | `DeliveryFeasibilityService.evaluate(db, order, rfq_id, tenant_id)` — called from production monitoring |
| GLTG path | Canonical: adapter → engine → persists `DeliveryFeasibilityPacketRecord` → emits event |
| Trigger | `run_delay_prediction()` on DELAYED milestone detection |

---

## Step 3 — Core Logic Audit

Rules audited against `libs/GLTG/gltg/engine.py`.

| Rule | Verdict | Location | Notes |
|---|---|---|---|
| LT-01 Parallel stage isolation (`max` of fabric/trim/packaging) | **PASS** | `engine.py:_evaluate_path` | `parallel_max = max(parallel_values)` — correct |
| LT-02 Sequential stage chaining (`production + QC + logistics` summed) | **PASS** | `engine.py:_evaluate_path` | `sequential_sum = sum(v for v in sequential_parts if v is not None)` — correct |
| LT-03 Total lead time formula (`parallel_max + sequential_sum`) | **PASS** | `engine.py:_evaluate_path` | `total_lt = parallel_max + sequential_sum` — correct |
| LT-04 Three output dates (`most_likely`, `risk_adjusted`, `committable`) | **PASS** | `engine.py:_evaluate_path` | All four dates computed (earliest/most_likely/risk_adjusted/committable) |
| LT-05 Risk buffer source | **FAIL** | `engine.py:7-8` | `_RISK_ADJ_BUFFER_DAYS = 3`, `_COMMITTABLE_BUFFER_DAYS = 5` — module-level constants, no per-call override; see DEFECT-03 |
| LT-06 Ranked path output (≤3 paths, ranking criteria) | **PARTIAL** | `engine.py:_evaluate_path, evaluate` | `ranked[:3]` never faked ✓; rank formula correct ✓; reliability inputs always `None` from adapter ✗; see DEFECT-02, DEFECT-04 |
| LT-07 Zero-supplier / zero-path edge cases | **PASS** | `engine.py:evaluate` | Zero nodes → `INCOMPLETE_EVIDENCE`; zero feasible paths → `INFEASIBLE` with explanation |
| LT-08 Reforecast from current date (not original start date) | **FAIL** | `engine.py:_compute_milestone_delay` | Uses `max()` across independent DELAYED milestones instead of `sum()`; see DEFECT-01 |
| LT-09 Input validation (422 on bad input, not 500) | **PARTIAL** | `api/main.py` | FastAPI/Pydantic validates request body (422 automatic); no global exception handler; GLTG engine errors return HTTP 200 with embedded `status` field, not HTTP 4xx/5xx |
| LT-10 `deadline_days` → target date conversion | **N/A** | — | Engine accepts `required_delivery_date` (a `date` object). No `deadline_days` integer-to-date conversion exists in this codebase. |

---

## Step 4 — Test Coverage Audit

### Coverage gap table

| Scenario | Covered? | Test location |
|---|---|---|
| Parallel max — fabric is bottleneck | YES | (existing unit tests in `tests/unit/`) |
| Parallel max — trim is bottleneck | YES | (existing unit tests) |
| Parallel max — packaging is bottleneck | YES | (existing unit tests) |
| Sequential sum correctness | YES | (existing unit tests) |
| All three output dates present | YES | (existing unit tests) |
| 3 feasible paths returned and ranked | YES | (existing unit tests) |
| Fewer than 3 paths (no fabrication) | YES | (existing unit tests) |
| 0 suppliers → human-readable error | NO | `tests/integration/test_gltg_reforecast_integration.py` (xfail stub) |
| Risk buffer from parameter (not hardcoded) | NO | `tests/unit/test_gltg_engine_date_buffers.py::test_risk_buffer_is_configurable_per_call` (xfail) |
| Milestone DELAYED → reforecast from today | NO | `tests/unit/test_gltg_engine_date_buffers.py::test_two_independent_delayed_milestones_accumulate_via_sum` (xfail) |
| Malformed request → 422, not 500 | NO | (no test) |
| Adapter maps reliability fields end-to-end | NO | `tests/unit/test_gltg_adapter_reliability.py::test_adapter_maps_reliability_fields_from_participant_profile` (xfail) |
| Reforecast error logged, not silently swallowed | NO | `tests/integration/test_gltg_reforecast_integration.py::test_gltg_reforecast_error_is_logged_not_silently_swallowed` (xfail) |

**Summary:** 7 of 13 scenarios covered. 6 have `xfail` stubs ready for promotion once the underlying defects are fixed.

---

## Step 5 — CI Audit

| Item | Finding |
|---|---|
| CI configuration | Not inspected (`.github/workflows/` not audited in this session) |
| Test runner | `pytest`, `asyncio_mode = "auto"` (`pyproject.toml`) |
| Test command | `pytest tests/` |
| GLTG-specific smoke tests | None found in API route tests |
| Missing assertions | Endpoint-level smoke tests for GLTG output fields; see DEFECT-06 |

---

## Step 6 — Defect Report

---

### DEFECT-01

**Title:** `_compute_milestone_delay` uses `max()` instead of `sum()` — underestimates multi-delay orders  
**Severity:** CRITICAL  
**Rule:** LT-08  
**Location:** `libs/GLTG/gltg/engine.py:_compute_milestone_delay`  
**Status:** OPEN

**Description**  
When an order has multiple independently DELAYED milestones (e.g., fabric sourcing delayed 3 days AND trim sourcing delayed 5 days), the engine takes the maximum delay (5 days) instead of summing them (8 days). The two delays affect different parallel-path segments and both materially extend the effective lead time. The result is a systematically optimistic `most_likely_delivery_date` for any order with more than one concurrent delay.

**Evidence**
```python
# engine.py — _compute_milestone_delay
total_delay = 0
for ms in milestone_updates:
    if ms.get("status") == "DELAYED":
        ...
        delay = (predicted - planned).days
        if delay > 0:
            total_delay = max(total_delay, delay)  # BUG: should be +=
return total_delay
```

**Root Cause**  
Initializes `total_delay = 0` and updates with `max()` instead of accumulating with `+=`.

**Recommended Fix**
```python
total_delay += delay  # replace max(total_delay, delay)
```

---

### DEFECT-02

**Title:** Adapter never populates reliability fields — supplier quality data excluded from ranking  
**Severity:** CRITICAL  
**Rule:** LT-06  
**Location:** `src/lead_time/gltg_adapter.py:build_gltg_input_from_order`  
**Status:** OPEN

**Description**  
`ParticipantNode` has three reliability fields (`qc_pass_rate`, `on_time_delivery_rate`, `quality_issue_count`) that the engine uses in `rank_score` with a combined 50% weight (0.3 + 0.2). The adapter that constructs `ParticipantNode` from DB records never reads these values from `ParticipantProfile`. All three fields default to `None`. The ranking formula reduces to speed-only at runtime, and any downstream consumer of `ranked_options[0]` receives the fastest supplier, not the best-scored one.

**Evidence**
```python
# gltg_adapter.py — ParticipantNode construction
node = ParticipantNode(
    participant_id=str(resp.participant_id),
    role=role_name,
    fabric_lead_time_days=pkt.fabric_lead_time_days if pkt else None,
    # qc_pass_rate           ← NOT SET
    # on_time_delivery_rate  ← NOT SET
    # quality_issue_count    ← NOT SET
)
```

**Root Cause**  
Adapter was written to pull lead-time packet fields only; no subsequent pass added the profile-level reliability fields.

**Recommended Fix**  
After loading `rfq_resp.participant.profile`, map the three fields:
```python
profile = getattr(resp.participant, "profile", None)
node = ParticipantNode(
    ...
    qc_pass_rate=profile.qc_pass_rate if profile else None,
    on_time_delivery_rate=profile.on_time_delivery_rate if profile else None,
    quality_issue_count=profile.quality_issue_count if profile else 0,
)
```

---

### DEFECT-03

**Title:** Risk and commitment buffers hardcoded — cannot be configured per order or tenant  
**Severity:** HIGH  
**Rule:** LT-05  
**Location:** `libs/GLTG/gltg/engine.py:7-8`  
**Status:** OPEN

**Description**  
`_RISK_ADJ_BUFFER_DAYS = 3` and `_COMMITTABLE_BUFFER_DAYS = 5` are module-level constants. `LeadTimeGraphEngine.evaluate()` accepts no override parameters. Every order — regardless of order value, customer tier, product category, or risk classification — gets the same buffers. Callers cannot experiment with different buffer strategies without forking the library.

**Evidence**
```python
# engine.py:7-8
_RISK_ADJ_BUFFER_DAYS = 3
_COMMITTABLE_BUFFER_DAYS = 5
```

**Root Cause**  
Constants were chosen as safe defaults but no parameter plumbing was added.

**Recommended Fix**  
Add optional parameters to `evaluate()`:
```python
def evaluate(
    self,
    order_input: ApparelOrderInput,
    risk_buffer_days: int = 3,
    commitment_buffer_days: int = 5,
) -> DeliveryFeasibilityPacket:
```

---

### DEFECT-04

**Title:** Ranking primary key is composite `rank_score`; product design requires earliest committable date  
**Severity:** MEDIUM  
**Rule:** LT-06  
**Location:** `libs/GLTG/gltg/engine.py:evaluate`  
**Status:** OPEN

**Description**  
Paths are ranked by `rank_score` descending (speed 50%, QC 30%, on-time 20%). A supplier with a better quality record but a one-day-slower committable date outranks a faster supplier, which conflicts with the product specification that the primary ordering criterion is the earliest `committable_delivery_date`. This defect has no meaningful impact until DEFECT-02 is fixed (reliability fields are currently all `None`), but the ranking logic will misbehave once reliability data flows.

**Recommended Fix**  
Sort by `committable_delivery_date` ascending as primary key; use `rank_score` as tiebreaker.

---

### DEFECT-05

**Title:** GLTG reforecast errors silently discarded — no log, no metric  
**Severity:** MEDIUM  
**Rule:** INT-02  
**Location:** `src/production_monitoring/service.py:run_delay_prediction`  
**Status:** OPEN

**Description**  
When `run_delay_prediction` detects a DELAYED milestone and triggers `DeliveryFeasibilityService.evaluate()`, any exception is caught by a bare `except Exception: pass`. Operators have no way to know a reforecast failed. Orders with GLTG errors remain on stale delivery dates with no alert.

**Evidence**
```python
try:
    await _feasibility_service.evaluate(...)
except Exception:
    pass  # silent discard
```

**Recommended Fix**
```python
except Exception:
    logger.exception("GLTG reforecast failed for order %s", order_id)
```

---

### DEFECT-06

**Title:** Decision-packet generation imports GLTG models directly, bypassing the service layer  
**Severity:** MEDIUM  
**Rule:** INT-04  
**Location:** `src/decision_packets/service.py`  
**Status:** OPEN

**Description**  
`generate_decision_packet()` imports `from gltg.models import ApparelOrderInput, ParticipantNode as GltgNode` directly. This bypasses `DeliveryFeasibilityService` and means: (1) the same reliability-field gap (DEFECT-02) affects this path, (2) results are not persisted to `delivery_feasibility_packets`, leaving a blind spot in analytics and audit trails.

**Recommended Fix**  
Route decision-packet generation through `DeliveryFeasibilityService.evaluate()`. Remove the direct `gltg.models` import.

---

## Step 7 — Integration Readiness Assessment

### 7.1 Versioning

- **abcdYi service version**: `1.0.0` — declared in `pyproject.toml` and in `FastAPI(version="1.0.0")` in `api/main.py`. Exposed only via the OpenAPI schema at `/openapi.json` (`info.version`). **No `/version` HTTP endpoint exists.**
- **GLTG library version**: `0.1.0` — declared in `libs/GLTG/pyproject.toml`. Not exposed at runtime through any API surface.
- **Verdict**: Callers cannot query the deployed version programmatically without hitting `/openapi.json`. Adding a lightweight `GET /version → {"version": "1.0.0", "gltg_engine": "0.1.0"}` endpoint is recommended before external integration.

### 7.2 Error contract

No global exception handler is registered in `api/main.py`. Error response shapes are inconsistent across the API:

| Error class | HTTP status | Body shape | Example |
|---|---|---|---|
| Route-level not-found | 404 | `{"detail": "<string>"}` | `{"detail": "No decision packet found"}` |
| Auth/permission | 403 | `{"detail": "<string>"}` | `{"detail": "Action requires prior human approval."}` |
| Request body validation | 422 | `{"detail": [{type, loc, msg, input, url}]}` | FastAPI/Pydantic default |
| GLTG engine failure | **200 / 201** | `DeliveryFeasibilityPacket` with `status="INCOMPLETE_EVIDENCE"` | Embedded in success response |
| Unhandled exception | 500 | FastAPI default HTML/JSON | No structured error body |

**Verdict**: No unified `{"error": "...", "code": "..."}` shape. GLTG failures are not surfaced as HTTP errors — callers must inspect `packet.status` and `packet.delivery_feasibility` inside a 200 response. This dual-status design makes it easy to miss a failed GLTG evaluation.

### 7.3 Caller assumptions

A caller integrating with the abcdYi GLTG surface must know:

1. **Date format**: All dates are ISO 8601 `YYYY-MM-DD` strings (Python `date` serialized by Pydantic v2). No timezone suffix on date fields.
2. **Timezone**: `evaluated_at` uses UTC (`datetime.now(timezone.utc)`). All output date fields are naive calendar dates interpreted as UTC-relative.
3. **Lead-time units**: Integer calendar days. No normalization for weekends or public holidays.
4. **Two orthogonal status fields** on `DeliveryFeasibilityPacket`:
   - `status`: `EVALUATED` | `INFEASIBLE` | `INCOMPLETE_EVIDENCE` — whether the engine completed computation
   - `delivery_feasibility`: `FEASIBLE` | `AT_RISK` | `INFEASIBLE` | `UNKNOWN` — whether the best path meets the deadline
   - Both must be checked; `delivery_feasibility=FEASIBLE` with `status=INCOMPLETE_EVIDENCE` is theoretically impossible but the fields are independent.
5. **`ranked_options` cardinality**: 0–3 paths. Never fabricated. Callers must handle empty array (INFEASIBLE/INCOMPLETE_EVIDENCE cases).
6. **Risk threshold values**: `AT_RISK` when `days_vs_deadline > 0`; `INFEASIBLE` when `> 7`. Hardcoded in engine — callers cannot configure.
7. **Auth**: JWT bearer required on all routes except `GET /health`. Token must carry a `tenant_id` claim used for row-level isolation.
8. **Risk buffers**: No per-request override available. Both buffers (risk: +3 days, committable: +5 days) are engine constants (DEFECT-03).

### 7.4 Breaking change risk

| Field / behaviour | Stability | Risk driver |
|---|---|---|
| `order_id`, `status`, `delivery_feasibility` string values | **Stable** | Core contract — no planned change |
| `earliest_delivery_date` | **Stable** | Computed from raw `total_lt`, no buffer |
| `most_likely_delivery_date` | **Will change** | DEFECT-01 fix (max→sum) will shift this field for any order with multiple concurrent delays |
| `risk_adjusted_delivery_date` | **Will change** | DEFECT-03 fix will make the +3-day buffer configurable; default will stay 3 but callers who assumed immutability will be surprised |
| `committable_delivery_date` | **Will change** | Same as risk_adjusted |
| `ranked_options` order / `ranked_options[0]` | **Will change** | DEFECT-02 fix will weight quality 50%; currently speed-only. Any system caching `ranked_options[0]` as the selected supplier will silently receive a different supplier after fix. **High breakage risk for downstream.** |
| `days_vs_deadline` | **Stable** | Arithmetic — unlikely to change |
| `explanation` (string) | **Unstable** | Human-readable prose; treat as display-only, never parse |

---

## Step 8 — Summary

### A. Audit Scorecard

| Check | Status | Defect IDs |
|---|---|---|
| LT-01 Parallel isolation | **PASS** | — |
| LT-02 Sequential chaining | **PASS** | — |
| LT-03 Formula | **PASS** | — |
| LT-04 Three dates | **PASS** | — |
| LT-05 Risk buffer | **FAIL** | DEFECT-03 |
| LT-06 Ranked paths | **PARTIAL** | DEFECT-02, DEFECT-04 |
| LT-07 Edge cases | **PASS** | — |
| LT-08 Reforecast | **FAIL** | DEFECT-01 |
| LT-09 Input validation | **PARTIAL** | — (FastAPI 422 fires; GLTG failures return 200; no global error handler) |
| LT-10 `deadline_days` conversion | **N/A** | — (engine uses `required_delivery_date` date field; no integer conversion exists) |
| CI / test coverage | **PARTIAL** | DEFECT-06 |
| Integration readiness | **PARTIAL** | DEFECT-01, DEFECT-02, DEFECT-03 (silent behavioral breaks pending fixes) |

**Score: 4 PASS / 2 FAIL / 3 PARTIAL / 1 N/A** out of 10 core rules.  
**Defects: 2 CRITICAL · 1 HIGH · 3 MEDIUM**

---

### B. Recommended Fixes (Priority Order)

#### Must-fix this iteration (P0)

| # | Defect | Effort | Location |
|---|---|---|---|
| 1 | **DEFECT-01** — `max()` → `sum()` in `_compute_milestone_delay` | Trivial (<1 hr) | `libs/GLTG/gltg/engine.py:_compute_milestone_delay` |
| 2 | **DEFECT-02** — Populate `qc_pass_rate`, `on_time_delivery_rate`, `quality_issue_count` from `ParticipantProfile` in adapter | Small (half day) | `src/lead_time/gltg_adapter.py` |

> **Warning**: Fixing DEFECT-01 will change `most_likely_delivery_date` for any order with ≥2 concurrent delayed milestones. Notify downstream consumers before deploying.  
> **Warning**: Fixing DEFECT-02 will reorder `ranked_options`. Any downstream system reading `ranked_options[0]` as the selected supplier will silently receive a different supplier.

#### Fix next iteration (P1)

| # | Defect | Effort | Location |
|---|---|---|---|
| 3 | **DEFECT-03** — Make risk/commitment buffers configurable via `evaluate()` kwargs | Small (half day) | `libs/GLTG/gltg/engine.py` |
| 4 | **DEFECT-04** — Change ranking primary key to earliest `committable_delivery_date`; `rank_score` as tiebreaker | Small (half day) | `libs/GLTG/gltg/engine.py:evaluate` — depends on DEFECT-02 fix |
| 5 | **INT** — Add `GET /version` endpoint returning `{"version": "1.0.0", "gltg_engine": "0.1.0"}` | Trivial (<1 hr) | `api/routes/` |
| 6 | **INT** — Register global exception handler in `api/main.py` with unified `{"error": str, "code": str}` shape | Trivial (<1 hr) | `api/main.py` |

#### Tech debt (P2)

| # | Defect | Effort | Location |
|---|---|---|---|
| 7 | **DEFECT-05** — Replace `except Exception: pass` with `logger.exception(...)` | Trivial (<1 hr) | `src/production_monitoring/service.py` |
| 8 | **DEFECT-06** — Route decision-packet GLTG call through `DeliveryFeasibilityService`; remove direct `gltg.models` import | Medium (1 day) | `src/decision_packets/service.py` |
| 9 | Promote 6 `xfail` stub tests to real tests after P0/P1 fixes | Small (half day) | `tests/unit/`, `tests/integration/` |

---

*Audit complete. All findings based solely on source code read during this session. No production data accessed.*  
*Branch: `claude/gltg-full-audit-bpovyp` · Commit: `f3077e6` (prior audit artifacts)*
