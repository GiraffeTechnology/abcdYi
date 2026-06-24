# GPM Session D Implementation Report

## 1. Scope Summary

Session D hardens the local Qwen/MNN runtime and adds a provider-agnostic, operator-selected LLM API interface. It builds on Session C (PR #13) and completes the `GPMSemanticQuoteService` as the stable Session D service entry point.

## 2. Files Changed

### Updated

| File | Change |
|---|---|
| `src/gpm/qwen/qwen_runtime_config.py` | Complete rewrite: `QwenRuntimeConfig` frozen dataclass with `from_env()` and `redacted()` |
| `src/gpm/qwen/qwen_runtime.py` | `runtime_name` → `runtime_mode`; updated `generate_json` signature |
| `src/gpm/qwen/mock_qwen_runtime.py` | `runtime_mode = "mock"`; added `missing_fields`, `risk_explanation`, `human_approval_required: True` |
| `src/gpm/qwen/qwen_mnn_runtime.py` | `runtime_mode = "mnn"`; `__init__(config: QwenRuntimeConfig)` |
| `src/gpm/llm_adapters/qwen_local_runtime.py` | 3-mode routing (mock/mnn/llm_api); backward-compatible legacy kwargs |
| `src/gpm/validators/qwen_output_validator.py` | Added `human_approval_required` to `REQUIRED_KEYS`; added forbidden key check |
| `src/gpm/models/qwen_semantic_analysis.py` | Added `missing_fields`, `risk_explanation`, `human_approval_required` fields |
| `tests/unit/gpm/test_mock_qwen_runtime.py` | `test_runtime_name` → `test_runtime_mode`; added `human_approval_required` assertions |
| `tests/unit/gpm/test_qwen_output_validator.py` | Added `human_approval_required: True` to `_valid_output()`; new guard tests |
| `scripts/run_gpm_qwen_local_smoke.py` | Session D naming; uses `GPMSemanticQuoteService` |
| `scripts/run_gpm_qwen_mnn_smoke.py` | Uses `runtime_mode`; accepts `true/yes` env values |

### New

| File | Purpose |
|---|---|
| `src/gpm/qwen/operator_llm_api_runtime.py` | Provider-agnostic LLM API runtime (qwen/openai_compatible/custom_http) via httpx |
| `src/gpm/services/gpm_semantic_quote_service.py` | Session D main service: context + Qwen + benchmark + guidance |
| `src/gpm/prompts/qwen_quote_reasoning_prompt.py` | Quote reasoning prompt builder |
| `scripts/run_gpm_llm_api_smoke.py` | Operator LLM API smoke test |
| `tests/unit/gpm/test_qwen_runtime_config.py` | Config loading, token redaction, frozen guard, canonical env priority |
| `tests/unit/gpm/test_qwen_runtime_mode_selection.py` | Mode routing and guard tests |
| `tests/unit/gpm/test_operator_llm_api_runtime_guard.py` | Disabled-by-default, token gate, no leakage |
| `tests/unit/gpm/test_qwen_output_validator_strict_schema.py` | Strict schema: forbidden keys, human approval, evidence grounding |
| `tests/integration/gpm/test_gpm_semantic_quote_service.py` | Canonical 10k shirts integration test |
| `tests/integration/gpm/test_gpm_operator_llm_api_smoke_contract.py` | Guard and provider contract tests |
| `tests/integration/gpm/test_operator_llm_api_live_optional.py` | Optional live API test (skipped without token) |
| `docs/GPM_PUBLIC_PRIVATE_DATA_MODE.md` | Public/private data mode documentation |

## 3. Runtime Modes

```text
mock    — deterministic offline runtime, default for CI and unit tests
mnn     — local Qwen/MNN model, no network, gated by model path
llm_api — operator-selected LLM API, disabled by default, requires explicit token
```

| Mode | Default? | Network? | CI? | Guard |
|---|---:|---:|---:|---|
| `mock` | yes | no | yes | none |
| `mnn` | no | no | gated | `GPM_QWEN_MNN_MODEL_PATH` must exist |
| `llm_api` | no | yes | never | `GPM_ENABLE_LLM_API=true` + token required |

## 4. Mock Runtime Behavior

`MockQwenRuntime` returns deterministic JSON based on regex matching over prompt text:
- `men_cotton_shirt` + cotton → score 0.85, high confidence
- shirt without cotton → score 0.40, medium confidence
- non-shirt → score 0.10, low confidence, not comparable

Always includes `human_approval_required: True`, `missing_fields: []`, `risk_explanation: ""`.

## 5. MNN Runtime Behavior

`QwenMNNRuntime` validates model path at construction. `generate_json()` raises `NotImplementedError` — the stub is complete; the MNN inference integration step is documented as Session D known limitation.

Required for live MNN:
```bash
GPM_ENABLE_LIVE_QWEN_MNN_TESTS=true \
GPM_LLM_RUNTIME_MODE=mnn \
GPM_QWEN_MNN_MODEL_PATH=/path/to/model.mnn \
uv run python scripts/run_gpm_qwen_mnn_smoke.py
```

## 6. LLM API Runtime Behavior

`OperatorLLMApiRuntime` is disabled by default. Raises `RuntimeError` unless operator explicitly enables it:

```bash
GPM_ENABLE_LLM_API=true              # canonical (GPM_ENABLE_QWEN_LLM_API is alias)
GPM_LLM_RUNTIME_MODE=llm_api        # canonical (GPM_QWEN_RUNTIME_MODE is alias)
GPM_LLM_API_KEY=<operator-token>    # canonical (QWEN_API_KEY / DASHSCOPE_API_KEY are aliases)
```

Three providers supported via httpx (no vendor SDK):
- `qwen` (default): DashScope-compatible endpoint
- `openai_compatible`: OpenAI chat/completions JSON mode, configurable base URL
- `custom_http`: generic JSON POST, operator supplies full URL

Provider selected by `GPM_LLM_PROVIDER`. Default provider is `qwen`; default runtime is `mock`.

## 7. Token Handling and Redaction

- Token is read from `GPM_LLM_API_KEY` (canonical), then `QWEN_API_KEY`, then `DASHSCOPE_API_KEY` (Qwen aliases)
- `QwenRuntimeConfig.redacted()` returns `{"llm_api_key": "***REDACTED***"}` when set
- Token is never printed, logged, or persisted
- `.env` files with token values must never be committed

## 8. Prompt / Schema Contract

Prompts instruct the model:
1. Return JSON only
2. Use only provided evidence
3. Never invent prices, MOQ, supplier identity, lead time, or payment terms
4. Cite only evidence IDs present in context
5. Set `human_approval_required=true`
6. Do not make pricing decisions
7. Do not send, approve, or dispatch any quote

Required output schema:
```json
{
  "normalized_product_type": "men_cotton_shirt",
  "normalized_material": "cotton",
  "normalized_process_tags": ["oem_odm"],
  "is_comparable": true,
  "comparability_score": 0.85,
  "detected_mismatch_flags": [],
  "missing_fields": [],
  "risk_explanation": "",
  "evidence_ids": ["ev_001"],
  "reason": "...",
  "confidence": "high",
  "human_approval_required": true
}
```

## 9. Validator Contract

`QwenOutputValidator.validate(output, context)` enforces:
1. Output is dict
2. Required keys present (including `human_approval_required`)
3. `human_approval_required` is exactly `True`
4. `comparability_score` numeric, [0.0, 1.0]
5. `evidence_ids` is list; every ID must exist in context bundle
6. No price fields: `price`, `unit_price`, `quote_price`
7. No MOQ fields: `moq`, `min_order_qty`, `minimum_order_quantity`
8. No forbidden action keys: `send_quote`, `dispatch_quote`, `place_order`, `make_payment`, `auto_approve`
9. No forbidden text instructions (dispatch quote, place order, make payment, etc.)

## 10. Test Commands

```bash
uv run pytest tests/unit/gpm/ tests/integration/gpm/ -v
```

Expected: all tests pass. Live LLM API tests are skipped unless `GPM_ENABLE_LLM_API=true` and token set.

## 11. Local Smoke Output

```text
GPM SESSION D LOCAL QWEN MOCK SMOKE: PASS
runtime_mode: mock
context_bundle: built
evidence_validation: PASS
supplier_quote_position: within_high_range
accept_recommendation: negotiate
human_approval_required: True
```

Run with:
```bash
uv run python scripts/run_gpm_qwen_local_smoke.py
```

## 12. LLM API Smoke Output

The LLM API smoke requires an operator-provided token. The token is not available in this environment.

```text
Blocked: operator LLM API token is missing.
```

To run the LLM API smoke when a token is available:
```bash
GPM_ENABLE_LLM_API=true \
GPM_LLM_RUNTIME_MODE=llm_api \
GPM_LLM_PROVIDER=qwen \
GPM_LLM_API_KEY=<operator-provided-token> \
GPM_LLM_API_MODEL=qwen-turbo \
uv run python scripts/run_gpm_llm_api_smoke.py
```

Expected output:
```text
GPM SESSION D LLM API SMOKE: PASS
runtime_mode: llm_api
provider: qwen
model: qwen-turbo
context_bundle: built
evidence_validation: PASS
model_output_validation: PASS
supplier_quote_position: within_high_range
accept_recommendation: negotiate
human_approval_required: True
```

## 13. Confirmation: No QC Changes

No QC routes, QC DB, QC model code, QC image/video evidence, QC process cards, QC comparison reports, or QC runtime data were touched in Session D.

## 14. Confirmation: No DB Migration

No Alembic migrations, no new SQLAlchemy business tables, no giraffe-db direct SQL access, no order/quote DB migration.

## 15. Confirmation: No Automatic Business Action

- `human_approval_required` is always `True` in all outputs
- Validator rejects any output where `human_approval_required` is not `True`
- Validator rejects forbidden action keys (`send_quote`, `dispatch_quote`, `place_order`, `make_payment`, `auto_approve`)
- No automatic buyer quote dispatch, order placement, payment, supplier commitment, or human approval bypass
- LLM API mode is disabled by default; requires explicit `GPM_ENABLE_LLM_API=true` + operator token
- No automatic fallback from local MNN to LLM API

## 16. Known Limitations

1. **MNN inference not yet implemented**: `QwenMNNRuntime.generate_json()` raises `NotImplementedError`. The model loading stub and guard are in place. Session E or a dedicated MNN integration PR should implement the actual inference call.

2. **LLM API smoke not run**: No operator token was available in this environment. The smoke script, guard tests, and live optional tests are all implemented and ready. Run with a token to complete acceptance criterion #5.

3. **Provider schema response parsing**: Some LLM providers may not support `response_format: {"type": "json_object"}`. If a provider returns markdown-wrapped JSON, the caller will need to strip the fenced code block before parsing. A text-fallback parser can be added to `_QwenProvider` if needed.

## 17. Session E Handoff

Session E theme: **GPM Session E — giraffe-db Context Retriever Integration**

- Replace `MockContextRetriever` with a real `giraffe-db`-backed retriever in `GPMSemanticQuoteService`
- The provider-agnostic LLM API interface remains independent from the database layer
- Database/data-source selection and LLM-provider selection are separate config concerns
- `QwenRuntimeConfig`, `OperatorLLMApiRuntime`, `GPMSemanticQuoteService`, and `QwenOutputValidator` should not require changes unless Session D exposes a bug
