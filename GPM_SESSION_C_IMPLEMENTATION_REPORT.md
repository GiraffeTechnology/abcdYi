# GPM Session C Implementation Report

**Branch:** `feature/gpm-session-c-qwen-context`
**Date:** 2026-06-23
**Builds on:** Session A (pricing data foundation), Session B (deterministic benchmark/guidance engines)

---

## 1. Scope

Session C adds a local Qwen semantic analysis layer and a retrieval-augmented context bundle system to the GPM pipeline. Qwen runs entirely on-device (MNN runtime) or in deterministic mock mode — no external LLM APIs are used at any point. The session B benchmark and guidance engines remain unchanged; Qwen provides semantic normalization only, not price calculations.

---

## 2. Files Added

| Path | Purpose |
|------|---------|
| `src/gpm/context/mock_context_retriever.py` | Canonical 10,000-piece men's cotton shirt scenario; 20 deterministic price samples |
| `src/gpm/llm_adapters/qwen_local_runtime.py` | `QwenLocalRuntime` — local/MNN runtime or mock mode; raises `RuntimeError` if unavailable |
| `src/gpm/prompts/qwen_gpm_normalization_prompt.py` | `build_qwen_gpm_normalization_prompt()` — evidence-grounded normalization prompt |
| `src/gpm/services/gpm_qwen_context_service.py` | `GPMQwenContextService` — full pipeline: context → Qwen → Session B engines |
| `scripts/run_gpm_qwen_local_smoke.py` | End-to-end smoke script; expected output shown in section 9 |
| `tests/unit/gpm/test_gpm_context_bundle.py` | `EvidenceReference` (Pydantic) and `GPMContextBundle` helper tests |
| `tests/unit/gpm/test_mock_context_retriever.py` | Canonical retriever: 20 evidence items, unique IDs, cotton shirt titles |
| `tests/unit/gpm/test_qwen_prompt_builders.py` | Normalization and quote-reasoning prompt contract tests |
| `tests/unit/gpm/test_qwen_local_runtime_no_cloud.py` | Mock mode, non-mock failure, and AST import guard tests |
| `tests/integration/gpm/test_gpm_qwen_context_service.py` | Full service pipeline integration test |

## 3. Files Modified

| Path | Change |
|------|--------|
| `src/gpm/context/evidence_reference.py` | Added `EvidenceReference(BaseModel)` (Pydantic v2) alongside existing `GPMEvidenceReference` dataclass |
| `src/gpm/context/context_retriever.py` | Added `ContextRetriever` Protocol with `build_gpm_context()` alongside `GPMContextRetriever` |
| `src/gpm/context/in_memory_context_retriever.py` | Store full sample attributes in `price_sample_dicts` so `BenchmarkEngine` can compute prices |
| `src/gpm/context/__init__.py` | Export `EvidenceReference`, `ContextRetriever`, `MockContextRetriever` |
| `src/gpm/validators/qwen_output_validator.py` | Added `VALID_RECOMMENDATIONS`, `VALID_POSITIONS`, `GPMServiceOutputValidator` |
| `src/gpm/validators/__init__.py` | Export `GPMServiceOutputValidator` |

---

## 4. Hard Security Boundaries (Enforced)

- **No external LLM API calls.** The AST-based test `test_no_external_llm_imports_in_gpm_src` scans all files under `src/gpm/llm_adapters/`, `src/gpm/qwen/`, `src/gpm/context/`, `src/gpm/prompts/`, `src/gpm/validators/`, and `src/gpm/services/` for imports of `openai`, `anthropic`, `dashscope`, `google.generativeai`, or `deepseek`. No violations exist.
- **No cloud fallback.** `QwenLocalRuntime` raises `RuntimeError("Local Qwen/MNN runtime is not available")` immediately when `mock_mode=False` and no valid MNN model path is found. There is no retry, no cloud fallback, no alternative provider.
- **No live marketplace API calls.** `MockContextRetriever` generates all data from hardcoded canonical lists. No HTTP requests are made anywhere in Session C code.
- **No order placement.** `human_approval_required = True` is enforced in every prompt and validated by `GPMServiceOutputValidator`. The validator raises `QwenOutputValidationError` if this field is missing or `False`.
- **No credential leakage.** `GPMContextBundle.to_prompt_payload()` strips keys matching credential patterns (`token`, `api_key`, `secret`, `password`, `key`) from evidence payload excerpts before including them in prompts.
- **No fine-tuning.** All Qwen usage is pure inference with retrieved context injected at prompt time. Customer data never touches model weights.

---

## 5. Local Qwen Runtime Behavior

`QwenLocalRuntime` has two modes:

**mock_mode=True** (default for tests and CI):
- Delegates to `MockQwenRuntime` which uses keyword matching: if prompt contains shirt+cotton+OEM keywords → `comparability_score=0.85`, `is_comparable=True`; shirt only → 0.40; other → 0.10
- `evidence_ids` extracted from prompt via regex on the `evidence_ids: [...]` line
- Deterministic: same prompt always produces the same output

**mock_mode=False** (production):
- Checks `model_path` argument, then `GPM_QWEN_MNN_MODEL_PATH` env var
- Raises `RuntimeError` immediately if the path is absent or does not exist on disk
- MNN runtime invocation stub is in place; real MNN inference requires the model binary

---

## 6. Context Bundle Schema

`GPMContextBundle` (dataclass):

| Field | Type | Notes |
|-------|------|-------|
| `bundle_id` | `str` | UUID; auto-generated via `create()` classmethod |
| `data_mode` | `Literal["public","private","mixed","mock"]` | Controls data sourcing policy |
| `requirement` | `dict` | RFQ details: product, quantity, material, etc. |
| `evidence` | `list[GPMEvidenceReference]` | Linked evidence items |
| `tenant_id` | `str \| None` | Passed through from caller |
| `project_id` | `str \| None` | Passed through from caller |
| `supplier_quote` | `dict \| None` | Supplier's quoted price/terms |
| `price_samples` | `list[dict]` | Full sample data for BenchmarkEngine |
| `supplier_history` | `list` | Historical order data (empty in mock mode) |
| `private_order_history` | `list` | Tenant-private orders (empty when `include_private_data=False`) |

Key methods:
- `evidence_ids()` → `set[str]` — all evidence IDs in the bundle
- `to_prompt_payload(max_items=20)` → `dict` — credential-stripped payload safe for prompt injection
- `create(...)` → classmethod that auto-assigns a `uuid4` bundle_id

`EvidenceReference(BaseModel)` (Pydantic v2, NEW):
- 12 allowed `source_type` values (no QC types)
- 4 `visibility` levels: `public_benchmark`, `tenant_private`, `internal_system`, `restricted`
- `payload: dict[str, Any]` defaults to `{}`; never contains credentials

---

## 7. Evidence Validation

`ContextBundleValidator.validate(bundle)` checks:
- `bundle_id` is non-empty
- `data_mode` is one of the four allowed literals
- All evidence IDs are unique (no duplicates)
- `requirement` dict is non-empty
- No credential-looking keys in requirement

`QwenOutputValidator.validate(output, bundle)` checks:
- Output is a `dict`
- Required keys present: `normalized_product_type`, `is_comparable`, `comparability_score`, `evidence_ids`
- `comparability_score` is in `[0.0, 1.0]`
- All cited `evidence_ids` exist in the bundle (no hallucinated IDs)
- No invented price or MOQ fields beyond what evidence supports

`GPMServiceOutputValidator.validate(combined, bundle)` additionally checks:
- `human_approval_required` is present and `True`
- `accept_recommendation` is one of: `accept`, `negotiate`, `reject`, `request_more_info`, `human_review_required`
- `supplier_quote_position` is one of: `below_market`, `within_low_range`, `within_mid_range`, `within_high_range`, `above_market`, `insufficient_data`

---

## 8. Test Commands and Results

```
uv run pytest tests/unit/gpm/ tests/integration/gpm/ -v
```

Result: **221 passed, 0 failed, 2 warnings** (Pydantic v1-style config in unrelated db module; passlib crypt deprecation — both pre-existing, not introduced by Session C)

New tests added in Session C:
- `tests/unit/gpm/test_gpm_context_bundle.py` — 9 tests
- `tests/unit/gpm/test_mock_context_retriever.py` — 9 tests
- `tests/unit/gpm/test_qwen_prompt_builders.py` — 12 tests
- `tests/unit/gpm/test_qwen_local_runtime_no_cloud.py` — 8 tests (includes AST import guard)
- `tests/integration/gpm/test_gpm_qwen_context_service.py` — 9 tests

---

## 9. Smoke Script Output

```
$ uv run python scripts/run_gpm_qwen_local_smoke.py
GPM SESSION C LOCAL QWEN CONTEXT SMOKE: PASS
context_bundle: built
evidence_validation: PASS
qwen_runtime_mode: mock
supplier_quote_position: within_high_range
accept_recommendation: negotiate
human_approval_required: True
```

The canonical scenario: 10,000 men's cotton shirts, supplier quote 38.5 CNY/piece, benchmark prices 24.0→46.04 CNY (step 1.16, 20 samples). P50≈35.02, P75≈40.53, threshold=(P50+P75)/2≈37.78. Since 38.5 > 37.78, position = `within_high_range` → recommendation = `negotiate`.

---

## 10. No External LLM Confirmation

The AST guard test `test_no_external_llm_imports_in_gpm_src` in `test_qwen_local_runtime_no_cloud.py` scans all `.py` files in the six GPM source directories and fails if any file imports `openai`, `anthropic`, `dashscope`, `google.generativeai`, or `deepseek`. This test passes green.

All Qwen inference in Session C routes through `QwenLocalRuntime` → `MockQwenRuntime` (tests/CI) or the local MNN binary (production). No HTTP calls to any LLM API are made.

---

## 11. No QC Confirmation

Session C touches no QC routes, QC database tables, QC model code, QC image/video processing, or QC process cards. The `EvidenceReference.source_type` Literal explicitly excludes `qc_image`, `qc_video`, `qc_report`, `qc_reference` (verified by `test_evidence_reference_no_qc_types`). No GPM service calls any QC service or imports from any QC module.

---

## 12. No DB Migration Confirmation

Session C introduces no database migrations, no new tables, no schema changes to `giraffe-db`, and no changes to GLTG. All context data is passed in-memory through `GPMContextBundle`. The `MockContextRetriever` generates data from Python lists at runtime. Persistent storage for production use will be designed in a future session when a real context store is introduced.

---

## Next PR Handoff

Session D should focus on:
1. Real `InMemoryGPMContextRetriever` backed by DB query (replacing the mock-only retriever)
2. `QwenMNNRuntime` with actual MNN inference call (replacing the mock stub)
3. Production `ContextRetriever` reading from `giraffe-db` price sample store
4. Latency measurement and MNN model quantization decisions
5. Multi-tenant evidence isolation (tenant-scoped evidence filtering in bundle construction)

The Session B `BenchmarkEngine` and `QuoteGuidanceEngine` are stable and require no changes for Session D.
