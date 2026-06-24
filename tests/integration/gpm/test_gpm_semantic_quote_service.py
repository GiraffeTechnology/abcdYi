"""Integration tests for GPMSemanticQuoteService — canonical 10,000 shirts scenario."""
from __future__ import annotations

import pytest

from src.gpm.context.mock_context_retriever import MockContextRetriever
from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
from src.gpm.services.gpm_semantic_quote_service import GPMSemanticQuoteService


@pytest.fixture
def service() -> GPMSemanticQuoteService:
    retriever = MockContextRetriever()
    runtime = QwenLocalRuntime(config=QwenRuntimeConfig(runtime_mode="mock"))
    return GPMSemanticQuoteService(retriever=retriever, runtime=runtime)


def test_semantic_quote_service_mock_canonical_10000_shirts(service: GPMSemanticQuoteService) -> None:
    output = service.run()
    assert output["supplier_quote_position"] == "within_high_range"
    assert output["accept_recommendation"] == "negotiate"
    assert output["runtime_mode"] == "mock"
    assert output["human_approval_required"] is True


def test_semantic_quote_service_output_is_human_approval_required(service: GPMSemanticQuoteService) -> None:
    output = service.run()
    assert output["human_approval_required"] is True


def test_semantic_quote_service_has_context_bundle_id(service: GPMSemanticQuoteService) -> None:
    output = service.run()
    assert "context_bundle_id" in output
    assert output["context_bundle_id"]


def test_semantic_quote_service_has_runtime_mode(service: GPMSemanticQuoteService) -> None:
    output = service.run()
    assert output["runtime_mode"] == "mock"


def test_semantic_quote_service_has_semantic_analysis(service: GPMSemanticQuoteService) -> None:
    output = service.run()
    sa = output["semantic_analysis"]
    assert sa["normalized_product_type"] == "men_cotton_shirt"
    assert sa["comparability_score"] == 0.85
    assert sa["is_comparable"] is True


def test_semantic_quote_service_has_benchmark_snapshot(service: GPMSemanticQuoteService) -> None:
    output = service.run()
    assert "benchmark_snapshot" in output
    assert "comparable_sample_count" in output["benchmark_snapshot"]


def test_semantic_quote_service_has_quote_guidance(service: GPMSemanticQuoteService) -> None:
    output = service.run()
    assert "quote_guidance" in output
    qg = output["quote_guidance"]
    assert "supplier_quote_position" in qg
    assert "accept_recommendation" in qg


def test_semantic_quote_service_private_data_excluded_by_default(service: GPMSemanticQuoteService) -> None:
    """Default run must not fail; private data excluded by include_private_data=False."""
    output = service.run(include_private_data=False)
    assert output["human_approval_required"] is True


def test_semantic_quote_service_private_data_included_when_allowed(service: GPMSemanticQuoteService) -> None:
    """include_private_data=True must not break the mock flow."""
    output = service.run(include_private_data=True)
    assert output["human_approval_required"] is True
    assert output["supplier_quote_position"] == "within_high_range"


def test_semantic_quote_service_runtime_mode_override() -> None:
    """runtime_mode parameter overrides env when no runtime is injected."""
    retriever = MockContextRetriever()
    service = GPMSemanticQuoteService(retriever=retriever)
    output = service.run(runtime_mode="mock")
    assert output["runtime_mode"] == "mock"
    assert output["human_approval_required"] is True
