from __future__ import annotations

from src.gpm.qwen.mock_qwen_runtime import MockQwenRuntime


CANONICAL_PROMPT = """
Requirement:
  product_type: men_cotton_shirt
  material: 100% cotton
  quantity: 10000 pieces
  process_tags: [OEM, ODM]
  target_market: Japan

Supplier quote: 38.5 CNY / piece

Evidence (cite only these IDs):
  [{"id": "ev_sample_001", "title": "Men's 100% Cotton Shirt衬衫", "usable_for_analysis": true}]

Available evidence_ids: ["ev_sample_001"]
"""


def test_canonical_scenario_product_type():
    runtime = MockQwenRuntime()
    out = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    assert out["normalized_product_type"] == "men_cotton_shirt"


def test_canonical_scenario_material():
    runtime = MockQwenRuntime()
    out = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    assert out["normalized_material"] == "cotton"


def test_canonical_scenario_comparability_score():
    runtime = MockQwenRuntime()
    out = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    assert out["comparability_score"] == 0.85


def test_canonical_scenario_is_comparable():
    runtime = MockQwenRuntime()
    out = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    assert out["is_comparable"] is True


def test_canonical_scenario_confidence():
    runtime = MockQwenRuntime()
    out = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    assert out["confidence"] == "high"


def test_canonical_scenario_evidence_ids():
    runtime = MockQwenRuntime()
    out = runtime.generate_json(CANONICAL_PROMPT, schema_name="qwen_semantic_analysis")
    assert "ev_sample_001" in out["evidence_ids"]


def test_shirt_without_cotton_weak_match():
    prompt = "shirt 衬衫\nAvailable evidence_ids: []"
    runtime = MockQwenRuntime()
    out = runtime.generate_json(prompt, schema_name="qwen_semantic_analysis")
    assert out["comparability_score"] == 0.40
    assert out["is_comparable"] is True


def test_non_matching_product_low_score():
    prompt = "trousers pants men\nAvailable evidence_ids: []"
    runtime = MockQwenRuntime()
    out = runtime.generate_json(prompt, schema_name="qwen_semantic_analysis")
    assert out["comparability_score"] == 0.10
    assert out["is_comparable"] is False


def test_oem_process_tag_detected():
    prompt = "shirt cotton OEM custom\nAvailable evidence_ids: []"
    runtime = MockQwenRuntime()
    out = runtime.generate_json(prompt, schema_name="qwen_semantic_analysis")
    assert "oem" in out["normalized_process_tags"]


def test_output_has_required_keys():
    runtime = MockQwenRuntime()
    out = runtime.generate_json("shirt cotton\nAvailable evidence_ids: []", "test")
    for key in (
        "normalized_product_type",
        "normalized_material",
        "normalized_process_tags",
        "is_comparable",
        "comparability_score",
        "detected_mismatch_flags",
        "evidence_ids",
        "reason",
        "confidence",
    ):
        assert key in out, f"Missing key: {key}"


def test_runtime_name():
    runtime = MockQwenRuntime()
    assert runtime.runtime_name == "mock_qwen"


def test_deterministic_output():
    runtime = MockQwenRuntime()
    out1 = runtime.generate_json(CANONICAL_PROMPT, "qwen_semantic_analysis")
    out2 = runtime.generate_json(CANONICAL_PROMPT, "qwen_semantic_analysis")
    assert out1 == out2
