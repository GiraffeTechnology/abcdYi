"""Integration test: GPMQwenContextService with MockContextRetriever + QwenLocalRuntime (mock mode)."""
from __future__ import annotations

import pytest

from src.gpm.context.mock_context_retriever import MockContextRetriever
from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime
from src.gpm.services.gpm_qwen_context_service import GPMQwenContextService


@pytest.fixture
def service() -> GPMQwenContextService:
    retriever = MockContextRetriever()
    runtime = QwenLocalRuntime(mock_mode=True)
    return GPMQwenContextService(retriever=retriever, runtime=runtime)


def test_canonical_flow_returns_dict(service: GPMQwenContextService) -> None:
    result = service.run()
    assert isinstance(result, dict)


def test_canonical_flow_within_high_range(service: GPMQwenContextService) -> None:
    result = service.run()
    assert result["supplier_quote_position"] == "within_high_range", (
        f"Expected within_high_range, got {result['supplier_quote_position']}"
    )


def test_canonical_flow_negotiate(service: GPMQwenContextService) -> None:
    result = service.run()
    assert result["accept_recommendation"] == "negotiate", (
        f"Expected negotiate, got {result['accept_recommendation']}"
    )


def test_canonical_flow_human_approval_required(service: GPMQwenContextService) -> None:
    result = service.run()
    assert result["human_approval_required"] is True


def test_canonical_flow_has_qwen_fields(service: GPMQwenContextService) -> None:
    result = service.run()
    for key in ("normalized_product_type", "is_comparable", "comparability_score", "evidence_ids"):
        assert key in result, f"Missing Qwen field: {key}"


def test_canonical_flow_has_benchmark_fields(service: GPMQwenContextService) -> None:
    result = service.run()
    assert "benchmark_confidence" in result
    assert "benchmark_comparable_samples" in result
    assert result["benchmark_comparable_samples"] > 0


def test_canonical_flow_is_comparable(service: GPMQwenContextService) -> None:
    result = service.run()
    assert result["is_comparable"] is True


def test_canonical_flow_with_tenant_id(service: GPMQwenContextService) -> None:
    result = service.run(tenant_id="tenant_test_001")
    assert result["human_approval_required"] is True
    assert result["accept_recommendation"] == "negotiate"


def test_canonical_flow_deterministic(service: GPMQwenContextService) -> None:
    r1 = service.run()
    r2 = service.run()
    assert r1["supplier_quote_position"] == r2["supplier_quote_position"]
    assert r1["accept_recommendation"] == r2["accept_recommendation"]
    assert r1["comparability_score"] == r2["comparability_score"]
