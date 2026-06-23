"""GPM Session D Qwen LLM API simulation smoke test.

Requires operator configuration:
    GPM_ENABLE_QWEN_LLM_API=true
    GPM_QWEN_RUNTIME_MODE=llm_api
    QWEN_API_KEY=<operator-provided-token>  (or DASHSCOPE_API_KEY)
    QWEN_API_MODEL=<model name>

The token is never printed or persisted.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, ".")


def main() -> None:
    enabled = os.environ.get("GPM_ENABLE_QWEN_LLM_API", "").lower() in ("1", "true", "yes")
    has_token = bool(
        os.environ.get("QWEN_API_KEY", "").strip()
        or os.environ.get("DASHSCOPE_API_KEY", "").strip()
    )

    if not enabled or not has_token:
        print("GPM SESSION D QWEN API SIMULATION SMOKE: SKIPPED")
        print("reason: GPM_ENABLE_QWEN_LLM_API=true and QWEN_API_KEY or DASHSCOPE_API_KEY required")
        return

    from src.gpm.context.mock_context_retriever import MockContextRetriever
    from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime
    from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
    from src.gpm.services.gpm_semantic_quote_service import GPMSemanticQuoteService
    from src.gpm.validators.context_bundle_validator import ContextBundleValidator, ContextBundleValidationError
    from src.gpm.validators.qwen_output_validator import QwenOutputValidator

    config = QwenRuntimeConfig.from_env()
    if config.runtime_mode != "llm_api":
        print("GPM SESSION D QWEN API SIMULATION SMOKE: SKIPPED")
        print("reason: GPM_QWEN_RUNTIME_MODE must be llm_api")
        return

    # Never print the token
    redacted = config.redacted()
    provider = redacted.get("llm_provider", "qwen")
    model = redacted.get("qwen_api_model") or "(default)"

    retriever = MockContextRetriever()

    # Validate context bundle
    bundle = retriever.build_gpm_context()
    try:
        ContextBundleValidator().validate(bundle)
        evidence_status = "PASS"
    except ContextBundleValidationError as e:
        print(f"GPM SESSION D QWEN API SIMULATION SMOKE: FAIL\nreason: context bundle validation: {e}")
        sys.exit(1)

    runtime = QwenLocalRuntime(config=config)

    # Validate raw Qwen output
    from src.gpm.prompts.qwen_gpm_normalization_prompt import build_qwen_gpm_normalization_prompt
    prompt = build_qwen_gpm_normalization_prompt(bundle)
    try:
        raw = runtime.generate_json(prompt, schema_name="gpm_normalization")
        QwenOutputValidator().validate(raw, bundle)
        model_output_status = "PASS"
    except Exception as e:
        print(f"GPM SESSION D QWEN API SIMULATION SMOKE: FAIL\nreason: model output validation: {e}")
        sys.exit(1)

    # Run full service
    service = GPMSemanticQuoteService(retriever=retriever, runtime=runtime)
    try:
        output = service.run()
    except Exception as e:
        print(f"GPM SESSION D QWEN API SIMULATION SMOKE: FAIL\nreason: service run: {e}")
        sys.exit(1)

    print("GPM SESSION D QWEN API SIMULATION SMOKE: PASS")
    print(f"runtime_mode: {output['runtime_mode']}")
    print(f"llm_api_simulation: enabled")
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
