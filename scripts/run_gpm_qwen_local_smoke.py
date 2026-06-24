"""GPM Session D local Qwen mock smoke test — canonical 10,000 men's cotton shirt scenario."""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from src.gpm.context.mock_context_retriever import MockContextRetriever
from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
from src.gpm.services.gpm_semantic_quote_service import GPMSemanticQuoteService
from src.gpm.validators.context_bundle_validator import ContextBundleValidator, ContextBundleValidationError


def main() -> None:
    retriever = MockContextRetriever()
    config = QwenRuntimeConfig(runtime_mode="mock")
    runtime = QwenLocalRuntime(config=config)

    # Validate the context bundle
    bundle = retriever.build_gpm_context(tenant_id=None, project_id=None, rfq_id=None,
                                          supplier_response_id=None)
    try:
        ContextBundleValidator().validate(bundle)
        evidence_status = "PASS"
    except ContextBundleValidationError as e:
        print(f"GPM SESSION D LOCAL QWEN MOCK SMOKE: FAIL\nreason: {e}")
        sys.exit(1)

    # Run the full Session D service
    service = GPMSemanticQuoteService(retriever=retriever, runtime=runtime)
    try:
        output = service.run()
    except Exception as e:
        print(f"GPM SESSION D LOCAL QWEN MOCK SMOKE: FAIL\nreason: {e}")
        sys.exit(1)

    print("GPM SESSION D LOCAL QWEN MOCK SMOKE: PASS")
    print(f"runtime_mode: {output['runtime_mode']}")
    print(f"context_bundle: built")
    print(f"evidence_validation: {evidence_status}")
    print(f"supplier_quote_position: {output['supplier_quote_position']}")
    print(f"accept_recommendation: {output['accept_recommendation']}")
    print(f"human_approval_required: {output['human_approval_required']}")


if __name__ == "__main__":
    main()
