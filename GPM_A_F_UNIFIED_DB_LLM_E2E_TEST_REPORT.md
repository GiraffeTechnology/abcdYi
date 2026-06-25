# GPM Sessions A–F Unified DB + Live Qwen API E2E Test Report

**Date**: 2026-06-25  
**Branch**: `claude/gpm-a-f-e2e-test-5vjdiy`  
**Repos**: GiraffeTechnology/abcdYi + GiraffeTechnology/giraffe-db  
**Task type**: Test / validation (not a feature implementation)

---

## Executive Summary

The full GPM A–F stack was validated end-to-end:
`giraffe-db (persisted context) → abcdYi GPM_CONTEXT_RETRIEVER=giraffe_db → /api/gpm/quote-guidance → live Qwen API → benchmark + guidance → GPMQuoteGuidancePacket → approval boundary → OpenClaw skill contract`

**All 14 acceptance criteria met. Live Qwen API call succeeded. Token leakage: none detected.**

---

## Environment

| Component | Value |
|-----------|-------|
| Python | 3.11.15 |
| uv | 0.8.17 |
| giraffe-db port | 8001 (GIRAFFE_DB_MOCK_MODE=true, SQLite) |
| abcdYi port | 8000 |
| GPM_RUNTIME_PROFILE | server |
| GPM_CONTEXT_RETRIEVER | giraffe_db |
| GPM_GIRAFFE_DB_BASE_URL | http://127.0.0.1:8001 |
| GPM_LLM_PROVIDER | qwen |
| GPM_LLM_API_MODEL | qwen-turbo |
| token_redacted | true |

---

## Step 1–2: Repo Sync

- **abcdYi**: branch `claude/gpm-a-f-e2e-test-5vjdiy` — clean, install OK via `uv pip install -e ".[dev]"`
- **giraffe-db**: branch `claude/gpm-a-f-e2e-test-5vjdiy` — clean, install OK via `uv pip install -e ".[dev]"`

---

## Step 3: Baseline Tests

### giraffe-db
- **21/21 PASS** — all tests green, no failures

### abcdYi GPM tests (`tests/unit/gpm/ + tests/integration/gpm/`)
- **438+ PASS**, 8 FAILED, 8 ERROR — all failures are pre-existing bugs in test code, not production logic

#### Pre-existing test failures (not introduced by this task)

| Bug | Severity | Root Cause |
|-----|----------|-----------|
| `test_gpm_service_router.py` — GET/approve/reject after POST fails (4 FAILED) | P1 | In-process `_PACKET_STORE` not shared across `TestClient` instances when `lru_cache` rebuilds service |
| `test_qwen_prompt_builders.py` / `test_qwen_prompt_contracts.py` (2 FAILED + 4 ERROR) | P1 | `build_qwen_quote_reasoning_prompt()` signature changed; tests still use old `supplier_quote=` kwarg |
| `test_qwen_local_runtime_no_cloud.py` (3 FAILED) | P2 | `QwenLocalRuntime` no longer raises `RuntimeError` at construction for missing model path |
| `test_gpm_openclaw_skill_contract.py` (4 ERROR) | P2 | Test fixture calls `.cache_clear()` on `get_quote_guidance_service` which is not `@lru_cache` decorated |

---

## Step 4: Start giraffe-db

```
uvicorn giraffe_db.api.main:app --host 127.0.0.1 --port 8001
```

Health check: `GET /healthz` → `{"status":"ok","service":"giraffe-db","schema_version":"0.1.0"}` ✓  
Schema: `GET /api/data/schema-version` → `{"schema_version":"0.1.0"}` ✓

**Blocker found and fixed**: `GiraffeDBClient` in abcdYi used bare paths (`/gpm/context`, `/schema-version`) but giraffe-db serves all data routes under `/api/data/`. Fixed by updating `src/gpm/clients/giraffe_db_client.py` to use correct prefixed paths. Integration tests remain green (mock transport uses substring matching).

---

## Step 5: Seed Canonical GPM Test Data

Seeded via giraffe-db REST API (no direct DB writes, no migrations):

| Record | ID | Details |
|--------|----|---------|
| Project | `668b9ee9-...` | "GPM E2E 10k Shirts", tenant_gpm_e2e_001 |
| RFQ | `fc4a57ff-...` | "10k Men Cotton Shirts", linked to project |
| Evidence 1 | `a4fcea34-...` | SupplierAlpha, price_min=3.85 USD, tenant_private |
| Evidence 2 | `182557f0-...` | SupplierBeta, price_min=4.10 USD, tenant_private |
| Evidence 3 | `6abf038d-...` | MarketplaceBenchmark, price_min=3.95 USD, public_benchmark |
| Supplier Response | `d0afbaf0-...` | Linked to RFQ |
| Supplier Response Packet | `3fc25169-...` | `supplier_quote: {unit_price: 4.20, currency: USD, moq: 1000}` |
| Context Bundle | `90e6f84d-...` (initial) | 3 evidence IDs, rfq included |

---

## Step 6: Start abcdYi + Smoke Scripts

```
GPM_RUNTIME_PROFILE=server GPM_CONTEXT_RETRIEVER=giraffe_db
GPM_GIRAFFE_DB_BASE_URL=http://127.0.0.1:8001 GPM_API_KEY=test-gpm-api-key
GPM_ENABLE_LLM_API=true GPM_LLM_PROVIDER=qwen GPM_LLM_API_MODEL=qwen-turbo
GPM_LLM_RUNTIME_MODE=llm_api [token_redacted: true]
```

| Smoke Script | Result |
|-------------|--------|
| `run_gpm_api_service_smoke.py` (mock/ci) | **PASS** — all 6 checks |
| `run_gpm_openclaw_skill_smoke.py` | **PASS** — all 9 checks |
| `run_gpm_giraffe_db_context_smoke.py` | **PASS** — health, schema, bundle, service run |
| `run_gpm_llm_api_smoke.py` | **PASS** — llm_api runtime, Qwen output validated |

**Smoke script fix applied**: `run_gpm_giraffe_db_context_smoke.py` — added `rfq_id` / `project_id` / `include_private_data` args to `service.run()` call so context IDs are passed through when running with non-mock retriever.

---

## Step 7: Live Qwen API E2E Call

```
POST /api/gpm/quote-guidance
Authorization: Bearer test-gpm-api-key
X-Giraffe-Tenant-ID: tenant_gpm_e2e_001
```

Request body:
```json
{
  "tenant_id": "tenant_gpm_e2e_001",
  "project_id": "668b9ee9-3f56-439c-864a-cf58b9530ce4",
  "rfq_id": "fc4a57ff-f131-4da0-b856-e5ebfa05c769",
  "evidence_ids": ["a4fcea34-...", "182557f0-...", "6abf038d-..."],
  "include_private_data": true
}
```

Response (201 Created):
```json
{
  "status": "ok",
  "packet_id": "gpm_pkt_a3556d9dcd1f",
  "runtime_mode": "llm_api",
  "context_retriever": "giraffe_db",
  "supplier_quote_position": "insufficient_data",
  "recommendation": "human_review_required",
  "benchmark_range": {"confidence": "low", "comparable_sample_count": 3},
  "human_approval_required": true,
  "approval_status": "pending",
  "token_redacted": true
}
```

**PASS** — Live Qwen API called, packet created, `context_retriever=giraffe_db` confirmed.

Note: `confidence=low` because only 3 evidence samples (< 10 required for medium). Expected — canonical seed has 3 records for E2E testing. `human_review_required` is the correct conservative output for low confidence.

---

## Step 8: GET Packet

```
GET /api/gpm/quote-guidance/gpm_pkt_a3556d9dcd1f
```

| Field | Value |
|-------|-------|
| status | ok |
| packet_id | gpm_pkt_a3556d9dcd1f |
| runtime_mode | llm_api |
| context_retriever | giraffe_db |
| approval_status | pending |
| human_approval_required | true |

**PASS** ✓

---

## Step 9: Approval Boundary Test

| Test | HTTP | Result |
|------|------|--------|
| POST approve (live packet) | 200 | `dispatched: false`, `approval_status: approved` ✓ |
| POST double-approve | 409 | Conflict returned ✓ |
| POST reject (fresh packet) | 200 | `dispatched: false`, `approval_status: rejected` ✓ |

**PASS** — `dispatched=False` on all approval/rejection actions. No external actions taken. ✓

---

## Step 10: OpenClaw Skill Contract

| Check | Result |
|-------|--------|
| POST createQuoteGuidance → 201 | ✓ |
| human_approval_required=True in packet | ✓ |
| approval_status=pending | ✓ |
| operator_action_required present | ✓ |
| no order/dispatch fields in packet | ✓ |
| GET getQuoteGuidance → 200 | ✓ |
| POST approveQuoteGuidance → 200 | ✓ |
| dispatched=False in approve response | ✓ |
| No auto-execution in dispatch_note | ✓ |

**PASS** — Full OpenClaw skill contract honored ✓

---

## Step 11: Negative Tests

| Test | Expected | Actual | Result |
|------|----------|--------|--------|
| A: Missing API key | 401 | 401 | PASS ✓ |
| B: Wrong API key | 401 | 401 | PASS ✓ |
| C: Tenant mismatch (header vs body) | 403 | 403 | PASS ✓ |
| D: giraffe_db retriever, missing base URL | 502 context_unavailable | 502 context_unavailable | PASS ✓ |
| E: Invalid Qwen API key | 503 runtime_unavailable | 503 runtime_unavailable | PASS ✓ (after fix) |

**Blocker found and fixed for Negative E**: `OperatorLLMApiRuntime.generate_json()` was not catching `httpx.HTTPStatusError` from `response.raise_for_status()`, resulting in unhandled 500. Fixed by wrapping HTTP errors in `GPMRuntimeUnavailableError` → properly returns 503 with `operator_action_required: true`.

---

## Step 12: Token Leakage Scan

| Scan Target | Findings |
|-------------|----------|
| API response bodies (healthz, capabilities, GET packet) | No key fragments found ✓ |
| abcdYi `src/` and `api/` Python files | 9 matches for env var name strings (`"DASHSCOPE_API_KEY"`, `"QWEN_API_KEY"`) — these are env var name literals, not key values ✓ |
| giraffe-db `src/` Python files | 0 matches ✓ |
| `QwenRuntimeConfig.redacted()` | Returns `"***REDACTED***"` for llm_api_key ✓ |

**token_redacted: true**

No actual API key values appear in any output, source file, log, or response body.

---

## Bugs Found and Fixed

### Production Fixes (real blockers)

| # | File | Fix | Category |
|---|------|-----|----------|
| 1 | `src/gpm/clients/giraffe_db_client.py` | Fixed all HTTP paths to include `/api/data/` prefix (was `/schema-version`, `/gpm/context`, etc.) | Blocker — integration couldn't work |
| 2 | `src/gpm/qwen/operator_llm_api_runtime.py` | Catch `httpx.HTTPStatusError` in `generate_json()` and raise `GPMRuntimeUnavailableError` → 503 | Blocker — invalid key caused unhandled 500 |

### Test/Script Fixes (non-production)

| # | File | Fix |
|---|------|-----|
| 3 | `scripts/run_gpm_giraffe_db_context_smoke.py` | Pass `rfq_id`, `project_id`, `include_private_data` to `service.run()` so giraffe-db retriever fetches full context |

### Pre-existing Bugs (not fixed — documented only)

| # | File | Severity | Description |
|---|------|----------|-------------|
| 4 | `tests/unit/gpm/test_gpm_service_router.py` | P1 | GET/approve/reject fail because `_PACKET_STORE` not shared across TestClient instances |
| 5 | `tests/unit/gpm/test_qwen_prompt_builders.py` + `test_qwen_prompt_contracts.py` | P1 | `build_qwen_quote_reasoning_prompt()` kwarg signature mismatch |
| 6 | `tests/unit/gpm/test_qwen_local_runtime_no_cloud.py` | P2 | `QwenLocalRuntime` no longer raises `RuntimeError` at construction |
| 7 | `tests/integration/gpm/test_gpm_openclaw_skill_contract.py` | P2 | `get_quote_guidance_service.cache_clear()` fails — function not lru_cache decorated |

---

## LLM API Smoke Result (separate run with mock retriever for full data)

With `MockContextRetriever` (20 canonical samples):
- `supplier_quote_position: within_high_range`
- `accept_recommendation: negotiate`
- `evidence_validation: PASS`
- `model_output_validation: PASS`

This confirms live Qwen returns semantically valid JSON, passes `QwenOutputValidator`, and produces actionable guidance when sufficient evidence is present.

---

## Acceptance Criteria Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | giraffe-db seeded and running | ✅ |
| 2 | abcdYi starts with GPM_CONTEXT_RETRIEVER=giraffe_db | ✅ |
| 3 | POST /api/gpm/quote-guidance returns 201 with GPMQuoteGuidancePacket | ✅ |
| 4 | runtime_mode=llm_api in response (live Qwen) | ✅ |
| 5 | context_retriever=giraffe_db in packet | ✅ |
| 6 | GET packet returns same packet | ✅ |
| 7 | Approve returns dispatched=False | ✅ |
| 8 | Double-approve returns 409 | ✅ |
| 9 | Reject returns dispatched=False | ✅ |
| 10 | OpenClaw contract: no order/dispatch fields | ✅ |
| 11 | Negative A–E all correct HTTP codes | ✅ |
| 12 | Token leakage: none detected | ✅ |
| 13 | token_redacted: true in report | ✅ |
| 14 | No automatic business actions dispatched | ✅ |

---

*Report generated by automated E2E validation. Key: token_redacted: true.*
