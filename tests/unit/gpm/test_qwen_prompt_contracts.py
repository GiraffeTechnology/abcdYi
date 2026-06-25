"""Tests for Qwen prompt contract requirements."""
from __future__ import annotations

import pytest

from src.gpm.context.evidence_reference import GPMEvidenceReference
from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.prompts.qwen_semantic_analysis_prompt import build_qwen_semantic_analysis_prompt
from src.gpm.prompts.qwen_quote_reasoning_prompt import build_qwen_quote_reasoning_prompt


def _make_bundle() -> GPMContextBundle:
    ev = [GPMEvidenceReference(id="ev_001", source_type="api_sample", source_id="s1")]
    return GPMContextBundle(
        bundle_id="b_test",
        data_mode="mock",
        requirement={"product": "men cotton shirt", "quantity": 10000},
        evidence=ev,
    )


@pytest.fixture
def bundle() -> GPMContextBundle:
    return _make_bundle()


@pytest.fixture
def semantic_prompt(bundle: GPMContextBundle) -> str:
    return build_qwen_semantic_analysis_prompt(bundle)


@pytest.fixture
def quote_prompt(bundle: GPMContextBundle) -> str:
    return build_qwen_quote_reasoning_prompt(bundle)


def test_semantic_prompt_requires_json_only(semantic_prompt: str) -> None:
    assert "JSON only" in semantic_prompt


def test_semantic_prompt_forbids_inventing_prices(semantic_prompt: str) -> None:
    assert "Do not invent prices" in semantic_prompt


def test_semantic_prompt_forbids_inventing_moq(semantic_prompt: str) -> None:
    assert "Do not invent MOQ" in semantic_prompt


def test_semantic_prompt_requires_citing_evidence_ids(semantic_prompt: str) -> None:
    assert "evidence_ids" in semantic_prompt


def test_semantic_prompt_forbids_placing_orders(semantic_prompt: str) -> None:
    prompt_lower = semantic_prompt.lower()
    assert "do not place orders" in prompt_lower or "place orders" in prompt_lower


def test_semantic_prompt_forbids_payment(semantic_prompt: str) -> None:
    prompt_lower = semantic_prompt.lower()
    assert "payment" in prompt_lower


def test_semantic_prompt_requires_human_approval(semantic_prompt: str) -> None:
    prompt_lower = semantic_prompt.lower()
    assert "human approval" in prompt_lower


def test_quote_prompt_requires_json_only(quote_prompt: str) -> None:
    assert "JSON only" in quote_prompt


def test_quote_prompt_human_approval_required_field(quote_prompt: str) -> None:
    assert "human_approval_required" in quote_prompt


def test_quote_prompt_forbids_setting_margin_policy(quote_prompt: str) -> None:
    prompt_lower = quote_prompt.lower()
    assert "margin policy" in prompt_lower


def test_quote_prompt_forbids_benchmark_recompute(quote_prompt: str) -> None:
    prompt_lower = quote_prompt.lower()
    assert "do not recompute" in prompt_lower or "do not compute" in prompt_lower


def test_semantic_prompt_includes_bundle_id(semantic_prompt: str, bundle: GPMContextBundle) -> None:
    assert bundle.bundle_id in semantic_prompt


def test_semantic_prompt_no_credentials() -> None:
    ev = [GPMEvidenceReference(
        id="ev_001", source_type="api_sample", source_id="s1",
        payload_excerpt={"price_min": "30", "api_key": "should_be_stripped"},
    )]
    bundle = GPMContextBundle(
        bundle_id="b_cred_test",
        data_mode="mock",
        requirement={"product": "shirt"},
        evidence=ev,
    )
    prompt = build_qwen_semantic_analysis_prompt(bundle)
    assert "should_be_stripped" not in prompt
    assert "api_key" not in prompt
