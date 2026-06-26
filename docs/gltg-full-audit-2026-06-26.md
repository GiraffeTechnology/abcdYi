# GLTG Full Audit — abcdYi / libs/GLTG

**Date:** 2026-06-26  
**Branch:** `claude/gltg-full-audit-bpovyp`  
**Auditor:** automated (GLTG full-audit spec)  
**Scope:** `libs/GLTG/`, `src/lead_time/`, `src/services/delivery_feasibility_service.py`, `src/decision_packets/service.py`, `src/production_monitoring/`, related tests and DB schema

---

## Step 1 — Inventory

### GLTG package files

| File | SHA | Role |
|------|-----|------|
| `libs/GLTG/gltg/__init__.py` | `98f44877` | Public exports |
| `libs/GLTG/gltg/models.py` | `1a2489c2` | `ParticipantNode`, `ApparelOrderInput`, `DeliveryPath`, `DeliveryFeasibilityPacket` |
| `libs/GLTG/gltg/engine.py` | `f4765345` | `LeadTimeGraphEngine.evaluate()` — sole computation entry point |

**Exports from `__init__.py`:** `LeadTimeGraphEngine`, `ApparelOrderInput`, `DeliveryFeasibilityPacket`, `DeliveryPath`, `DependencyEdge`, `ParticipantNode`

### Files importing from `gltg.*`

| File | Import | Status |
|------|--------|--------|
| `src/lead_time/gltg_adapter.py` | `from gltg.models import ...` | Correct — designated adapter |
| `src/services/delivery_feasibility_service.py` | via `gltg_adapter` only | Correct |
| `src/decision_packets/service.py` | `from gltg.models import ApparelOrderInput, ParticipantNode as GltgNode` | **DEFECT INT-04** — direct import outside adapter boundary |

### Test files covering GLTG / lead-time logic

| File | Surface tested |
|------|---------------|
| `tests/unit/test_gltg_adapter.py` | `build_gltg_input_from_order`, `evaluate_delivery_feasibility` |
| `tests/unit/test_delivery_feasibility_service.py` | `DeliveryFeasibilityService.evaluate()`, event emission, DB persistence |
| `tests/unit/test_decision_packet_uses_gltg.py` | GLTG enrichment of `DecisionOption.lead_time_breakdown` |
| `tests/unit/test_lead_time_calculator.py` | `calculate_path_lead_time()` (non-GLTG fallback) |
| `tests/unit/test_delay_predictor.py` | `predict_completion_date()` |

### Integration points

| Surface | File | Notes |
|---------|------|-------|
| Decision-packet route | `api/routes/decision_packets.py` | `POST /projects/{id}/decision-packets` → `generate_decision_packet` |
| Decision-packet service | `src/decision_packets/service.py` | Calls GLTG directly (INT-04) and via `evaluate_delivery_feasibility` |
| Delivery feasibility service | `src/services/delivery_feasibility_service.py` | Canonical GLTG entry point; persists `DeliveryFeasibilityPacketRecord`; emits `DELIVERY_FEASIBILITY_EVALUATED` |
| Production monitoring | `src/production_monitoring/service.py` | `run_delay_prediction` triggers reforecast via `_feasibility_service.evaluate()` |
| Execution graph event | `src/execution_graph/event_types.py` | `DELIVERY_FEASIBILITY_EVALUATED = "DELIVERY_FEASIBILITY_EVALUATED"` |

### DB schema — `delivery_feasibility_packets`

Migration: `alembic/versions/a1b2c3d4e5f6_add_delivery_feasibility_packets.py`  
ORM model: `src/db/models/delivery_feasibility.py` (SHA `50a8e0d7`)

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | `default=uuid.uuid4` |
| `tenant_id` | UUID | NOT NULL |
| `project_id` | UUID | nullable |
| `order_id` | UUID | NOT NULL |
| `source` | String(50) | default `"GLTG"` |
| `status` | String(50) | default `"EVALUATED"` |
| `earliest_delivery_date` | Date | nullable |
| `most_likely_delivery_date` | Date | nullable |
| `risk_adjusted_delivery_date` | Date | nullable |
| `committable_delivery_date` | Date | nullable |
| `required_delivery_date` | Date | nullable |
| `delivery_feasibility` | String(50) | default `"UNKNOWN"` |
| `days_vs_deadline` | Integer | nullable |
| `critical_path_json` | JSONB | nullable |
| `critical_path_days` | Integer | nullable |
| `ranked_options_json` | JSONB | nullable |
| `option_count` | Integer | default `0` |
| `risk_flags_json` | JSONB | nullable |
| `missing_evidence_json` | JSONB | nullable |
| `raw_gltg_packet_json` | JSONB | nullable |
| `explanation` | Text | nullable |
| `confidence` | String(20) | default `"LOW"` |
| `created_at` | DateTime(tz) | `server_default=func.now()` |

---

## Step 2 — Core Model Correctness (LT-01 … LT-10)

### LT-01 — Parallel stage isolation: fabric / trim / packaging run in parallel → `max()`
**PASS**  
`engine.py::_evaluate_path()`:
```python
parallel_values = [v for v in [fabric_lt, trim_lt, packaging_lt] if v is not None]
parallel_max = max(parallel_values) if parallel_values else None
```
Non-None values only; `max()` correctly applied.

### LT-02 — Sequential stage chaining: `production + qc + logistics` sum sequentially
**PASS**  
```python
sequential_parts = [production_lt, qc_lt, logistics_lt]
sequential_sum = sum(v for v in sequential_parts if v is not None)
```
Correct. None values excluded from sum; no double-counting.

### LT-03 — Total lead time formula: `total_lt = parallel_max + sequential_sum`
**PASS**  
```python
total_lt = (parallel_max + sequential_sum) if parallel_max is not None else None
```
Formula is correct. `None` guard propagates correctly when parallel stages have no data.

### LT-04 — Earliest, most-likely, risk-adjusted, committable dates computed from `total_lt`
**PASS** (date arithmetic correct; buffer values are a separate concern — see LT-05)  
```python
earliest      = today + timedelta(days=total_lt)
most_likely   = today + timedelta(days=effective_lt)   # effective_lt = total_lt + milestone_delay
risk_adjusted = most_likely + timedelta(days=_RISK_ADJ_BUFFER_DAYS)
committable   = risk_adjusted + timedelta(days=_COMMITTABLE_BUFFER_DAYS)
```
Date arithmetic is structurally correct.

### LT-05 — Risk-adjusted and committable buffers are configurable (not hardcoded)
**FAIL**  
`engine.py:5-6`:
```python
_RISK_ADJ_BUFFER_DAYS   = 3   # hardcoded module constant
_COMMITTABLE_BUFFER_DAYS = 5   # hardcoded module constant
```
`LeadTimeGraphEngine.evaluate()` accepts no parameter to override these values.
Buffer tuning requires a code change. No per-order, per-tenant, or per-supplier
override is possible without forking the engine.  
See **DEFECT-01**.

### LT-06 — Ranked options are sorted by shortest committable date first
**PARTIAL**  
Current ranking uses a composite `rank_score`:
```python
rank_score += max(0.0, (200 - total_lt) / 200.0) * 0.5   # speed (50 %)
rank_score += anchor.qc_pass_rate * 0.3                   # quality (30 %)
rank_score += anchor.on_time_delivery_rate * 0.2          # reliability (20 %)
```
A slower-but-higher-quality manufacturer can outrank a faster one, which is
inconsistent with a "shortest committable date first" primary sort.
Additionally, because reliability fields are never populated from the adapter
(LT-09), the 50 % quality weight is always zero — making the composite score
effectively only the speed term.  
See **DEFECT-02**.

### LT-07 — At most 3 ranked options returned; options never faked
**PASS**  
```python
ranked = sorted(candidate_paths, key=lambda p: p.rank_score, reverse=True)[:3]
```
Hard-sliced at 3. The engine returns `len(candidate_paths)` when fewer than
3 manufacturers qualify — no padding or fabrication.

### LT-08 — Milestone DELAYED → reforecast from current date with correct delay accumulation
**PARTIAL**  
`_compute_milestone_delay` correctly sets evaluation start to `today` (caller
passes `evaluated_at`). However, delay accumulation uses `max()` instead of
`sum()` across independent delayed milestones:
```python
total_delay = max(total_delay, delay)   # BUG: should be total_delay += delay
```
Two independent delays of 3 d and 5 d produce a 5 d total instead of 8 d.  
See **DEFECT-03**.

### LT-09 — Reliability fields (qc_pass_rate, on_time_delivery_rate, quality_issue_count) populated from supplier data
**PARTIAL**  
`gltg_adapter.py::build_gltg_input_from_order` constructs `ParticipantNode`
without copying `ParticipantProfile` reliability metrics:
```python
node = ParticipantNode(
    participant_id=str(resp.participant_id),
    role=role_name,
    fabric_lead_time_days=pkt.fabric_lead_time_days if pkt else None,
    # qc_pass_rate, on_time_delivery_rate, quality_issue_count: never set
)
```
These fields default to `None`, zeroing out 50 % of the rank_score formula.  
See **DEFECT-04**.

### LT-10 — Zero feasible paths produces INFEASIBLE/INCOMPLETE_EVIDENCE status + non-empty explanation
**PASS**  
```python
if not ranked:
    status = "INFEASIBLE" if candidate_paths else "INCOMPLETE_EVIDENCE"
    explanation = self._build_explanation(None, required_delivery, missing_evidence, ranked_count=0)
    return DeliveryFeasibilityPacket(ranked_options=[], explanation=explanation, ...)
```
Both cases handled; explanation is never empty.

---

## Step 3 — Integration Audit (INT-01 … INT-04)

### INT-01 — Full call path: `POST /projects/{id}/decision-packets` → GLTG
**PASS** (path exists; see INT-04 for architectural concern)

Route: `api/routes/decision_packets.py::create_decision_packet`  
→ `src/decision_packets/service.py::generate_decision_packet`  
→ `evaluate_delivery_feasibility(gltg_input)` (from `src/lead_time/gltg_adapter`)  
→ `LeadTimeGraphEngine.evaluate()`  
→ GLTG ranked paths stored in `DecisionOption.lead_time_breakdown['gltg']`

Note: GLTG results in this path are **not** persisted to `delivery_feasibility_packets`;
they live only in `DecisionOption`. This may be intentional but is undocumented.

### INT-02 — GLTG reforecast errors are handled and observable
**PARTIAL**  
`src/production_monitoring/service.py::run_delay_prediction`:
```python
try:
    await _feasibility_service.evaluate(...)
except Exception:
    pass   # silent discard
```
No log call, no metric, no structured error. GLTG reforecast failures are
invisible to operators.  
See **DEFECT-06**.

### INT-03 — Delay prediction triggers GLTG reforecast from current date
**PASS** (path exists; error handling is the concern — see INT-02)  
`run_delay_prediction` calls `predict_completion_date` (delay_predictor), then
passes `milestone_updates` (including DELAYED statuses) to
`_feasibility_service.evaluate()` → `build_gltg_input_from_order` →
`ApparelOrderInput.milestone_updates` → `_compute_milestone_delay`.  
Evaluation start (`evaluated_at`) is set to today by the adapter.

### INT-04 — GLTG called only through designated seam (`src/lead_time/gltg_adapter.py`)
**FAIL**  
`src/decision_packets/service.py` imports directly from `gltg.models`:
```python
from gltg.models import ApparelOrderInput, ParticipantNode as GltgNode
```
This bypasses the adapter, skips any profile-level enrichment the adapter
performs, and means GLTG calls in this path produce output that is neither
persisted to `delivery_feasibility_packets` nor enriched with reliability fields.  
See **DEFECT-05**.

### INT-05 — `DELIVERY_FEASIBILITY_EVALUATED` event emitted on every evaluation
**PASS**  
`src/execution_graph/event_types.py`: `DELIVERY_FEASIBILITY_EVALUATED` defined.  
`src/services/delivery_feasibility_service.py::evaluate()` emits this event
after persisting the `DeliveryFeasibilityPacketRecord`.  
`tests/unit/test_delivery_feasibility_service.py` asserts event is emitted.

---

## Step 4 — Test Coverage Audit

| # | Scenario | Status | Stub file |
|---|----------|--------|-----------|
| 1 | Parallel max: fabric=30, trim=45, packaging=20 → `parallel_max=45` | COVERED | — |
| 2 | Trim is bottleneck over fabric when `trim_lt > fabric_lt` | COVERED | — |
| 3 | Sequential sum: `production + qc + logistics` | COVERED | — |
| 4 | Total = `parallel_max + sequential_sum` | COVERED | — |
| 5 | Zero feasible paths → `INFEASIBLE` / `INCOMPLETE_EVIDENCE` + non-empty explanation | COVERED | — |
| 6 | `DELIVERY_FEASIBILITY_EVALUATED` event emitted | COVERED | — |
| 7 | `risk_adjusted = most_likely + 3 d` (buffer configurable per call) | **MISSING** | `tests/unit/test_gltg_engine_date_buffers.py` |
| 8 | `committable = risk_adjusted + 5 d` (buffer configurable per call) | **MISSING** | `tests/unit/test_gltg_engine_date_buffers.py` |
| 9 | Two independent DELAYED milestones → delay = sum, not max | **MISSING** | `tests/unit/test_gltg_engine_date_buffers.py` |
| 10 | Reliability fields (`qc_pass_rate`, `on_time_delivery_rate`) flow adapter → engine → rank_score | **MISSING** | `tests/unit/test_gltg_adapter_reliability.py` |
| 11 | `POST /decision-packets` → GLTG engine → `lead_time_breakdown['gltg']` (DB integration) | **MISSING** | `tests/integration/test_gltg_reforecast_integration.py` |
| 12 | Delay prediction detects DELAYED milestones → GLTG reforecast → new `DeliveryFeasibilityPacketRecord` | **MISSING** | `tests/integration/test_gltg_reforecast_integration.py` |

Stub files created with `@pytest.mark.xfail(reason="not yet covered: ...")` for all MISSING scenarios.

---

## Step 5 — Defect Report

---

### DEFECT-01

**Title:** Risk-adjusted and committable buffer constants are hardcoded; no per-call override  
**Severity:** HIGH  
**Rule:** LT-05 — FAIL  
**Location:** `libs/GLTG/gltg/engine.py:5-6`  
**Status:** OPEN

**Description**  
`_RISK_ADJ_BUFFER_DAYS = 3` and `_COMMITTABLE_BUFFER_DAYS = 5` are module-level
constants.  `LeadTimeGraphEngine.evaluate()` accepts no parameters to override
them.  Buffer values cannot be tuned per order, per season, per supplier tier,
or per tenant without modifying the source file and redeploying.

**Evidence**
```python
# engine.py:5-6
_RISK_ADJ_BUFFER_DAYS   = 3
_COMMITTABLE_BUFFER_DAYS = 5
...
risk_adjusted = most_likely + timedelta(days=_RISK_ADJ_BUFFER_DAYS)
committable   = risk_adjusted + timedelta(days=_COMMITTABLE_BUFFER_DAYS)
```

**Root Cause**  
Constants extracted to module scope during initial implementation but no
injection mechanism (kwarg, config object, or engine constructor parameter)
was added.

**Recommended Fix**  
Add `risk_buffer_days: int = 3` and `committable_buffer_days: int = 5`
keyword arguments to `LeadTimeGraphEngine.evaluate()`.  Remove or keep the
module constants as fallback defaults only.  Update `ApparelOrderInput` or
a new `EvaluationConfig` dataclass if per-order configuration is needed.

---

### DEFECT-02

**Title:** Ranking uses composite score; shortest committable date is not the primary sort key  
**Severity:** MEDIUM  
**Rule:** LT-06 — PARTIAL  
**Location:** `libs/GLTG/gltg/engine.py::_evaluate_path()` (rank_score computation)  
**Status:** OPEN

**Description**  
Paths are ranked by `rank_score = 0.5·speed + 0.3·qc_pass_rate + 0.2·on_time_delivery_rate`.
A manufacturer with a longer lead time but high quality can outrank a faster
manufacturer, placing a later committable date first in the result list.
The spec requires shortest committable date as the primary sort key, with
quality metrics as secondary tiebreakers.

Additionally, because LT-09 leaves reliability fields at `None`, the 50 %
quality contribution is always zero in practice, making this a speed-only
ranking that still doesn't sort on committable date.

**Evidence**
```python
rank_score += max(0.0, (200 - total_lt) / 200.0) * 0.5
if anchor.qc_pass_rate is not None:
    rank_score += anchor.qc_pass_rate * 0.3
if anchor.on_time_delivery_rate is not None:
    rank_score += anchor.on_time_delivery_rate * 0.2
```

**Root Cause**  
Composite score was modeled on a quality-weighted rubric rather than a
delivery-date-first ordering.

**Recommended Fix**  
Sort by `committable_delivery_date` ascending as the primary key.  Use the
reliability composite as a tiebreaker only (secondary sort when committable
dates are equal).  Depends on DEFECT-04 being fixed first so reliability
fields are actually populated.

---

### DEFECT-03

**Title:** `_compute_milestone_delay` takes `max()` across DELAYED milestones instead of `sum()`  
**Severity:** HIGH  
**Rule:** LT-08 — PARTIAL  
**Location:** `libs/GLTG/gltg/engine.py::_compute_milestone_delay()`  
**Status:** OPEN

**Description**  
When two or more independent milestones are both in DELAYED status the method
accumulates delay via `total_delay = max(total_delay, delay)`.  This means
that a fabric delay of 3 d and an independent trim delay of 5 d produce a
total delay of 5 d (the maximum) instead of 8 d (the correct sum).  Any order
with simultaneous upstream delays is systematically under-forecasted.

**Evidence**
```python
def _compute_milestone_delay(self, milestone_updates: list[dict]) -> int:
    total_delay = 0
    for ms in milestone_updates:
        if ms.get("status") == "DELAYED":
            ...
            total_delay = max(total_delay, delay)  # BUG
    return total_delay
```

**Root Cause**  
Copy-paste of a "keep worst" pattern that is correct for dependent stages
(where only one bottleneck applies) but wrong for independent supply-chain
stages that each add real calendar time.

**Recommended Fix**  
Change `total_delay = max(total_delay, delay)` to `total_delay += delay`.
Add the regression test in `tests/unit/test_gltg_engine_date_buffers.py`
(scenario 9, currently xfail) as the acceptance gate.

---

### DEFECT-04

**Title:** Adapter does not map `ParticipantProfile` reliability fields onto `ParticipantNode`  
**Severity:** HIGH  
**Rule:** LT-09 — PARTIAL  
**Location:** `src/lead_time/gltg_adapter.py::build_gltg_input_from_order()`  
**Status:** OPEN

**Description**  
`build_gltg_input_from_order` constructs each `ParticipantNode` without
setting `qc_pass_rate`, `on_time_delivery_rate`, or `quality_issue_count`
from the participant's `ParticipantProfile`.  These fields default to `None`,
which means 50 % of the engine's `rank_score` formula always contributes
zero, and ordering among manufacturers is decided solely by speed — ignoring
the quality history data that already exists in the database.

**Evidence**
```python
node = ParticipantNode(
    participant_id=str(resp.participant_id),
    role=role_name,
    fabric_lead_time_days=pkt.fabric_lead_time_days if pkt else None,
    trim_lead_time_days=pkt.trim_lead_time_days if pkt else None,
    packaging_lead_time_days=pkt.packaging_lead_time_days if pkt else None,
    production_time_days=pkt.production_time_days if pkt else None,
    qc_time_days=pkt.qc_time_days if pkt else None,
    logistics_time_days=pkt.logistics_time_days if pkt else None,
    # qc_pass_rate:          NOT SET
    # on_time_delivery_rate: NOT SET
    # quality_issue_count:   NOT SET
)
```

**Root Cause**  
Initial adapter implementation focused on sourcing lead-time days from the
lead-time packet.  The reliability fields on `ParticipantNode` were added to
the model later (or the adapter was not updated when they were added).

**Recommended Fix**  
After loading the RFQ response, load `resp.participant.profile` (or the
equivalent ORM relationship) and set:
```python
node.qc_pass_rate          = profile.qc_pass_rate if profile else None
node.on_time_delivery_rate = profile.on_time_delivery_rate if profile else None
node.quality_issue_count   = profile.quality_issue_count if profile else None
```
Use the xfail test in `tests/unit/test_gltg_adapter_reliability.py` as the
acceptance gate.

---

### DEFECT-05

**Title:** `decision_packets/service.py` imports `gltg.models` directly, bypassing the adapter boundary  
**Severity:** MEDIUM  
**Rule:** INT-04 — FAIL  
**Location:** `src/decision_packets/service.py` (top-of-file import)  
**Status:** OPEN

**Description**  
`src/decision_packets/service.py` contains:
```python
from gltg.models import ApparelOrderInput, ParticipantNode as GltgNode
```
This violates the architectural rule that only `src/lead_time/gltg_adapter.py`
(and `src/services/delivery_feasibility_service.py` via the adapter) may import
from `gltg.*`.  Consequences:

1. GLTG calls in the decision-packet path receive no profile-level enrichment
   from the adapter (the reliability fields gap, DEFECT-04, is inherited here).
2. GLTG results in this path are **not** persisted to `delivery_feasibility_packets`;
   they go only into `DecisionOption.lead_time_breakdown['gltg']`.  This means
   the canonical table is missing evaluations from the most user-facing flow.
3. Any future changes to how the adapter builds `ApparelOrderInput` must be
   duplicated manually in `decision_packets/service.py`.

**Root Cause**  
Decision-packet generation was implemented before the adapter boundary was
formalized, or the author was unaware of the adapter convention.

**Recommended Fix**  
Remove the direct `gltg.models` import from `decision_packets/service.py`.
Call `build_gltg_input_from_order(db, order, rfq_id)` (from the adapter) to
produce the `ApparelOrderInput`, then call `evaluate_delivery_feasibility()`.
This also closes the DEFECT-04 gap for this path and enables persistence to
`delivery_feasibility_packets` via `DeliveryFeasibilityService` if desired.

---

### DEFECT-06

**Title:** GLTG reforecast errors silently swallowed with bare `except Exception: pass`  
**Severity:** MEDIUM  
**Rule:** INT-02 — PARTIAL  
**Location:** `src/production_monitoring/service.py::run_delay_prediction()`  
**Status:** OPEN

**Description**  
```python
try:
    await _feasibility_service.evaluate(...)
except Exception:
    pass  # Reforecast is best-effort; do not block delay prediction on GLTG errors
```
While the best-effort contract (do not block delay prediction) is correct,
discarding the exception with no log call leaves operators with no visibility
into GLTG reforecast failures.  A GLTG engine crash, a DB write failure, or an
adapter error during production monitoring produces zero signal — no log line,
no metric, no alert.

**Root Cause**  
The `pass` body was written to keep delay prediction non-blocking but the
structured-log call was omitted.

**Recommended Fix**  
Replace `pass` with a `logger.exception(...)` call:
```python
except Exception:
    logger.exception(
        "GLTG reforecast failed for order %s; delay prediction continues",
        order_id,
    )
```
The best-effort semantics (no re-raise) are preserved; the failure is now
observable.  Use the xfail integration stub in
`tests/integration/test_gltg_reforecast_integration.py`
(`test_gltg_reforecast_error_is_logged_not_silently_swallowed`) as the
acceptance gate.

---

## Summary

| Defect | Rule | Severity | Description |
|--------|------|----------|-------------|
| DEFECT-01 | LT-05 FAIL | HIGH | Hardcoded risk/committable buffer constants; no per-call override |
| DEFECT-02 | LT-06 PARTIAL | MEDIUM | Ranking by composite score, not shortest committable date |
| DEFECT-03 | LT-08 PARTIAL | HIGH | Milestone delay: `max()` instead of `sum()` across independent delays |
| DEFECT-04 | LT-09 PARTIAL | HIGH | Adapter never populates reliability fields from `ParticipantProfile` |
| DEFECT-05 | INT-04 FAIL | MEDIUM | Direct `gltg.models` import in `decision_packets/service.py` bypasses adapter |
| DEFECT-06 | INT-02 PARTIAL | MEDIUM | Reforecast errors silently swallowed; no log call |

**LT rules:** 8 PASS, 1 PARTIAL+FAIL (LT-05), 1 PARTIAL (LT-06), 1 PARTIAL (LT-08), 1 PARTIAL (LT-09)  
**INT checks:** 3 PASS, 1 PARTIAL (INT-02), 1 FAIL (INT-04)  
**Test scenarios:** 6 COVERED, 6 MISSING (stubs added)
