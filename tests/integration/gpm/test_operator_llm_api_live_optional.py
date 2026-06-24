"""Optional live LLM API test — skipped unless GPM_ENABLE_LLM_API=true and token is set."""
from __future__ import annotations

import os

import pytest

from src.gpm.context.mock_context_retriever import MockContextRetriever
from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
from src.gpm.services.gpm_semantic_quote_service import GPMSemanticQuoteService
from src.gpm.validators.qwen_output_validator import QwenOutputValidator
from src.gpm.validators.context_bundle_validator import ContextBundleValidator


def _live_enabled() -> bool:
    enabled = (
        os.environ.get("GPM_ENABLE_LLM_API", "").lower() in ("1", "true", "yes")
        or os.environ.get("GPM_ENABLE_QWEN_LLM_API", "").lower() in ("1", "true", "yes")
    )
    has_token = bool(
        os.environ.get("GPM_LLM_API_KEY", "").strip()
        or os.environ.get("QWEN_API_KEY", "").strip()
        or os.environ.get("DASHSCOPE_API_KEY", "").strip()
    )
    return enabled and has_token


pytestmark = pytest.mark.skipif(
    not _live_enabled(),
    reason="GPM_ENABLE_LLM_API=true and GPM_LLM_API_KEY (or QWEN_API_KEY/DASHSCOPE_API_KEY) required for live test",
)


def test_live_llm_api_response_parses_as_json() -> None:
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "llm_api", (
        "Set GPM_LLM_RUNTIME_MODE=llm_api (or GPM_QWEN_RUNTIME_MODE=llm_api) to run live test"
    )
    runtime = QwenLocalRuntime(config=config)
    retriever = MockContextRetriever()
    bundle = retriever.build_gpm_context()

    from src.gpm.prompts.qwen_gpm_normalization_prompt import build_qwen_gpm_normalization_prompt
    prompt = build_qwen_gpm_normalization_prompt(bundle)
    result = runtime.generate_json(prompt, schema_name="gpm_normalization")

    assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result!r}"


def test_live_llm_api_validator_passes() -> None:
    config = QwenRuntimeConfig.from_env()
    runtime = QwenLocalRuntime(config=config)
    retriever = MockContextRetriever()
    bundle = retriever.build_gpm_context()

    from src.gpm.prompts.qwen_gpm_normalization_prompt import build_qwen_gpm_normalization_prompt
    prompt = build_qwen_gpm_normalization_prompt(bundle)
    result = runtime.generate_json(prompt, schema_name="gpm_normalization")

    QwenOutputValidator().validate(result, bundle)


def test_live_llm_api_evidence_ids_grounded() -> None:
    config = QwenRuntimeConfig.from_env()
    runtime = QwenLocalRuntime(config=config)
    retriever = MockContextRetriever()
    bundle = retriever.build_gpm_context()

    from src.gpm.prompts.qwen_gpm_normalization_prompt import build_qwen_gpm_normalization_prompt
    prompt = build_qwen_gpm_normalization_prompt(bundle)
    result = runtime.generate_json(prompt, schema_name="gpm_normalization")

    valid_ids = bundle.evidence_ids()
    for eid in result.get("evidence_ids", []):
        assert eid in valid_ids, f"Hallucinated evidence_id: {eid!r}"


def test_live_llm_api_human_approval_required_true() -> None:
    config = QwenRuntimeConfig.from_env()
    runtime = QwenLocalRuntime(config=config)
    retriever = MockContextRetriever()
    bundle = retriever.build_gpm_context()

    from src.gpm.prompts.qwen_gpm_normalization_prompt import build_qwen_gpm_normalization_prompt
    prompt = build_qwen_gpm_normalization_prompt(bundle)
    result = runtime.generate_json(prompt, schema_name="gpm_normalization")

    assert result.get("human_approval_required") is True, (
        f"Model must return human_approval_required=true. Got: {result.get('human_approval_required')!r}"
    )


def test_live_llm_api_canonical_guidance() -> None:
    """Canonical 10k shirts: expect within_high_range / negotiate."""
    config = QwenRuntimeConfig.from_env()
    runtime = QwenLocalRuntime(config=config)
    retriever = MockContextRetriever()
    service = GPMSemanticQuoteService(retriever=retriever, runtime=runtime)
    output = service.run()

    assert output["supplier_quote_position"] == "within_high_range"
    assert output["accept_recommendation"] == "negotiate"
    assert output["human_approval_required"] is True
