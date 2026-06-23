"""Tests for MockQwenRuntime deterministic output."""
from __future__ import annotations

import pytest

from src.gpm.qwen.mock_qwen_runtime import MockQwenRuntime


@pytest.fixture
def runtime() -> MockQwenRuntime:
    return MockQwenRuntime()


CANONICAL_PROMPT = """
requirement: 10,000 pieces men's cotton shirt, 100% cotton, OEM / ODM, Japan market
supplier quote: 38.5 CNY / piece
evidence:
  - "id": "ev_ms-001"
    title: "men cotton shirt OEM custom"
  - "id": "ev_ms-002"
    title: "100% cotton shirt men"
evidence_ids: ["ev_ms-001", "ev_ms-002"]
"""


def test_canonical_scenario_product_type(runtime: MockQwenRuntime) -> None:
    out = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    assert out["normalized_product_type"] == "men_cotton_shirt"


def test_canonical_scenario_material(runtime: MockQwenRuntime) -> None:
    out = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    assert out["normalized_material"] == "cotton"


def test_canonical_scenario_comparability_score(runtime: MockQwenRuntime) -> None:
    out = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    assert out["comparability_score"] == 0.85


def test_canonical_scenario_is_comparable(runtime: MockQwenRuntime) -> None:
    out = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    assert out["is_comparable"] is True


def test_canonical_scenario_evidence_ids_copied(runtime: MockQwenRuntime) -> None:
    out = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    assert "ev_ms-001" in out["evidence_ids"] or "ev_ms-002" in out["evidence_ids"]


def test_shirt_without_cotton_gives_weak_match(runtime: MockQwenRuntime) -> None:
    prompt = "shirt product, polyester blend, supplier quote 20 CNY\nevidence_ids: []"
    out = runtime.generate_json(prompt, schema_name="qwen_semantic_analysis")
    assert out["comparability_score"] == 0.40


def test_non_shirt_gives_non_match(runtime: MockQwenRuntime) -> None:
    prompt = "trousers product, cotton, supplier quote 50 CNY\nevidence_ids: []"
    out = runtime.generate_json(prompt, schema_name="qwen_semantic_analysis")
    assert out["comparability_score"] == 0.10
    assert out["is_comparable"] is False


def test_oem_detected_in_process_tags(runtime: MockQwenRuntime) -> None:
    prompt = "men cotton shirt OEM ODM custom\nevidence_ids: []"
    out = runtime.generate_json(prompt, schema_name="qwen_semantic_analysis")
    assert "oem_odm" in out["normalized_process_tags"]


def test_output_has_all_required_keys(runtime: MockQwenRuntime) -> None:
    out = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    for key in (
        "normalized_product_type", "normalized_material", "normalized_process_tags",
        "is_comparable", "comparability_score", "detected_mismatch_flags",
        "evidence_ids", "reason", "confidence",
    ):
        assert key in out, f"Missing key: {key}"


def test_runtime_name() -> None:
    assert MockQwenRuntime.runtime_name == "mock_qwen"


def test_deterministic_same_input(runtime: MockQwenRuntime) -> None:
    out1 = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    out2 = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    assert out1 == out2
