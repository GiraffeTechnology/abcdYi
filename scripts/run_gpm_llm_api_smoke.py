"""GPM Session D LLM API smoke test.

With GPM_RUNTIME_PROFILE=lightweight or server, the resolver attempts the local MNN
model first, then the operator LLM API if explicitly allowed. Missing token, disabled
API, or no configured runtime → SKIPPED with a clear reason.
No token is ever printed or persisted.

Operator configuration (server/lightweight profile):
    GPM_RUNTIME_PROFILE=server           (or lightweight; enables local-first resolution)
    GPM_QWEN_MNN_MODEL_PATH=/path/...    (preferred: local model, no network)
    GPM_ENABLE_LLM_API=true              (optional: allow API fallback after local fails)
    GPM_LLM_API_KEY=<operator-token>     (canonical; QWEN_API_KEY / DASHSCOPE_API_KEY are aliases)
    GPM_LLM_API_MODEL=<model name>       (optional; QWEN_API_MODEL is alias)

Alternative explicit mode:
    GPM_LLM_RUNTIME_MODE=llm_api         (canonical; GPM_QWEN_RUNTIME_MODE is alias)
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

_REASON_LABELS: dict[str, str] = {
    "missing_token": "missing operator token",
    "api_disabled": "LLM API mode is disabled",
    "local_model_unavailable": "local model initialization failed",
    "no_runtime_configured": "no LLM runtime configured",
    "invalid_token": "invalid or unauthorized token",
    "timeout": "provider request timed out",
    "non_json_response": "provider returned non-JSON response",
    "schema_invalid": "provider response failed schema validation",
    "local_model_missing": "local model path not found",
    "provider_error": "provider initialization failed",
}


def main() -> None:
    from src.gpm.qwen.gpm_runtime_unavailable_error import GPMRuntimeUnavailableError
    from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
    from src.gpm.qwen.qwen_runtime_resolver import resolve_runtime

    config = QwenRuntimeConfig.from_env()

    try:
        runtime = resolve_runtime(config)
    except GPMRuntimeUnavailableError as exc:
        status = exc.to_status()
        print("GPM SESSION D LLM API SMOKE: SKIPPED")
        print(f"reason: {_REASON_LABELS.get(status['reason'], status['reason'])}")
        print(f"operator_action_required: {status['operator_action_required']}")
        return
    except RuntimeError as exc:
        print("GPM SESSION D LLM API SMOKE: FAIL")
        print(f"reason: {exc}")
        sys.exit(1)

    if runtime.runtime_mode != "llm_api":
        print("GPM SESSION D LLM API SMOKE: SKIPPED")
        print(f"reason: resolved runtime is {runtime.runtime_mode!r}, not llm_api")
        return

    # Never print the token
    redacted = config.redacted()
    provider = redacted.get("llm_provider", "qwen")
    model = redacted.get("llm_api_model") or "(default)"

    from src.gpm.context.mock_context_retriever import MockContextRetriever
    from src.gpm.prompts.qwen_gpm_normalization_prompt import build_qwen_gpm_normalization_prompt
    from src.gpm.services.gpm_semantic_quote_service import GPMSemanticQuoteService
    from src.gpm.validators.context_bundle_validator import (
        ContextBundleValidationError,
        ContextBundleValidator,
    )
    from src.gpm.validators.qwen_output_validator import QwenOutputValidator

    retriever = MockContextRetriever()
    bundle = retriever.build_gpm_context()
    try:
        ContextBundleValidator().validate(bundle)
        evidence_status = "PASS"
    except ContextBundleValidationError as e:
        print(f"GPM SESSION D LLM API SMOKE: FAIL\nreason: context bundle validation: {e}")
        sys.exit(1)

    prompt = build_qwen_gpm_normalization_prompt(bundle)
    try:
        raw = runtime.generate_json(prompt, schema_name="gpm_normalization")
        QwenOutputValidator().validate(raw, bundle)
        model_output_status = "PASS"
    except Exception as e:
        print(f"GPM SESSION D LLM API SMOKE: FAIL\nreason: model output validation: {e}")
        sys.exit(1)

    service = GPMSemanticQuoteService(retriever=retriever, runtime=runtime)
    try:
        output = service.run()
    except Exception as e:
        print(f"GPM SESSION D LLM API SMOKE: FAIL\nreason: service run: {e}")
        sys.exit(1)

    print("GPM SESSION D LLM API SMOKE: PASS")
    print(f"runtime_mode: {output['runtime_mode']}")
    print(f"provider: {provider}")
    print(f"model: {model}")
    print(f"context_bundle: built")
    print(f"evidence_validation: {evidence_status}")
    print(f"model_output_validation: {model_output_status}")
    print(f"supplier_quote_position: {output['supplier_quote_position']}")
    print(f"accept_recommendation: {output['accept_recommendation']}")
    print(f"human_approval_required: {output['human_approval_required']}")


if __name__ == "__main__":
    main()
