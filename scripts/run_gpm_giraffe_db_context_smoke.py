"""GPM Session E giraffe-db context retriever smoke test.

Requires:
    GPM_CONTEXT_RETRIEVER=giraffe_db
    GPM_GIRAFFE_DB_BASE_URL=http://localhost:8001

When GPM_CONTEXT_RETRIEVER != giraffe_db the script prints SKIPPED and exits 0,
so CI without a live giraffe-db service is unaffected.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, ".")


def main() -> None:
    mode = os.environ.get("GPM_CONTEXT_RETRIEVER", "mock")
    if mode != "giraffe_db":
        print(f"GPM SESSION E GIRAFFE-DB SMOKE: SKIPPED (GPM_CONTEXT_RETRIEVER={mode!r})")
        sys.exit(0)

    base_url = os.environ.get("GPM_GIRAFFE_DB_BASE_URL", "").strip()
    if not base_url:
        print("GPM SESSION E GIRAFFE-DB SMOKE: FAIL — GPM_GIRAFFE_DB_BASE_URL is not set")
        sys.exit(1)

    from src.gpm.clients.giraffe_db_client import GiraffeDBClient, GiraffeDBClientError
    from src.gpm.context.retrievers.giraffe_db_context_retriever import GiraffeDBContextRetriever
    from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime
    from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
    from src.gpm.services.gpm_semantic_quote_service import GPMSemanticQuoteService
    from src.gpm.validators.context_bundle_validator import ContextBundleValidator, ContextBundleValidationError

    client = GiraffeDBClient(
        base_url=base_url,
        tenant_id=os.environ.get("GPM_GIRAFFE_DB_TENANT_ID") or None,
        operator_id=os.environ.get("GPM_GIRAFFE_DB_OPERATOR_ID") or None,
        api_key=os.environ.get("GPM_GIRAFFE_DB_API_KEY") or None,
    )

    # Health check
    try:
        health = client.healthz()
        print(f"health: {health}")
    except GiraffeDBClientError as e:
        print(f"GPM SESSION E GIRAFFE-DB SMOKE: FAIL — health check failed: {e}")
        sys.exit(1)

    # Schema version
    try:
        version = client.schema_version()
        print(f"schema_version: {version}")
    except GiraffeDBClientError as e:
        print(f"GPM SESSION E GIRAFFE-DB SMOKE: FAIL — schema_version failed: {e}")
        sys.exit(1)

    # Build context bundle
    retriever = GiraffeDBContextRetriever(
        client=client,
        default_tenant_id=os.environ.get("GPM_GIRAFFE_DB_TENANT_ID") or None,
    )
    try:
        bundle = retriever.retrieve(
            tenant_id=os.environ.get("GPM_GIRAFFE_DB_TENANT_ID") or None,
            project_id=os.environ.get("GPM_GIRAFFE_DB_PROJECT_ID") or None,
            rfq_id=os.environ.get("GPM_GIRAFFE_DB_RFQ_ID") or None,
        )
    except GiraffeDBClientError as e:
        print(f"GPM SESSION E GIRAFFE-DB SMOKE: FAIL — context retrieval failed: {e}")
        sys.exit(1)

    # Validate bundle
    try:
        ContextBundleValidator().validate(bundle)
    except ContextBundleValidationError as e:
        print(f"GPM SESSION E GIRAFFE-DB SMOKE: FAIL — bundle validation failed: {e}")
        sys.exit(1)

    # Run full service — pass the same IDs used for retrieval so rfq/project are included
    runtime = QwenLocalRuntime(config=QwenRuntimeConfig(runtime_mode="mock"))
    service = GPMSemanticQuoteService(context_retriever=retriever, qwen_runtime=runtime)
    try:
        output = service.run(
            tenant_id=os.environ.get("GPM_GIRAFFE_DB_TENANT_ID") or None,
            project_id=os.environ.get("GPM_GIRAFFE_DB_PROJECT_ID") or None,
            rfq_id=os.environ.get("GPM_GIRAFFE_DB_RFQ_ID") or None,
            include_private_data=os.environ.get(
                "GPM_GIRAFFE_DB_INCLUDE_PRIVATE_DATA", "false"
            ).lower() in ("1", "true", "yes"),
        )
    except Exception as e:
        print(f"GPM SESSION E GIRAFFE-DB SMOKE: FAIL — service run failed: {e}")
        sys.exit(1)

    print("GPM SESSION E GIRAFFE-DB SMOKE: PASS")
    print(f"base_url: {base_url}")
    print(f"bundle_id: {bundle.bundle_id}")
    print(f"data_mode: {bundle.data_mode}")
    print(f"evidence_count: {len(bundle.evidence)}")
    print(f"price_sample_count: {len(bundle.price_samples)}")
    print(f"supplier_quote_position: {output['supplier_quote_position']}")
    print(f"accept_recommendation: {output['accept_recommendation']}")
    print(f"human_approval_required: {output['human_approval_required']}")


if __name__ == "__main__":
    main()
