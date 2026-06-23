"""GPM Session C local Qwen context smoke test — canonical 10,000 men's cotton shirt scenario."""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from src.gpm.context.mock_context_retriever import MockContextRetriever
from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime
from src.gpm.services.gpm_qwen_context_service import GPMQwenContextService
from src.gpm.validators.context_bundle_validator import ContextBundleValidator, ContextBundleValidationError


def main() -> None:
    retriever = MockContextRetriever()
    runtime = QwenLocalRuntime(mock_mode=True)

    # Validate the context bundle
    bundle = retriever.build_gpm_context(tenant_id=None, project_id=None, rfq_id=None,
                                          supplier_response_id=None)
    try:
        ContextBundleValidator().validate(bundle)
        evidence_status = "PASS"
    except ContextBundleValidationError as e:
        print(f"GPM SESSION C LOCAL QWEN CONTEXT SMOKE: FAIL\nreason: {e}")
        sys.exit(1)

    # Run the full service
    service = GPMQwenContextService(retriever=retriever, runtime=runtime)
    try:
        output = service.run()
    except Exception as e:
        print(f"GPM SESSION C LOCAL QWEN CONTEXT SMOKE: FAIL\nreason: {e}")
        sys.exit(1)

    print("GPM SESSION C LOCAL QWEN CONTEXT SMOKE: PASS")
    print("context_bundle: built")
    print(f"evidence_validation: {evidence_status}")
    print(f"qwen_runtime_mode: {runtime.runtime_mode}")
    print(f"supplier_quote_position: {output['supplier_quote_position']}")
    print(f"accept_recommendation: {output['accept_recommendation']}")
    print(f"human_approval_required: {output['human_approval_required']}")


if __name__ == "__main__":
    main()
