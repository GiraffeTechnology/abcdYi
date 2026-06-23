"""Tests for Qwen GPM prompt builders (normalization + quote reasoning)."""
from __future__ import annotations

import pytest

from src.gpm.context.evidence_reference import GPMEvidenceReference
from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.context.mock_context_retriever import MockContextRetriever
from src.gpm.prompts.qwen_gpm_normalization_prompt import build_qwen_gpm_normalization_prompt
from src.gpm.prompts.qwen_quote_reasoning_prompt import build_qwen_quote_reasoning_prompt


def _simple_bundle() -> GPMContextBundle:
    ev = [GPMEvidenceReference(id="ev_001", source_type="api_sample", source_id="s1")]
    return GPMContextBundle(
        bundle_id="b_test",
        data_mode="mock",
        requirement={"product": "men cotton shirt", "quantity": 10000},
        evidence=ev,
    )


@pytest.fixture
def bundle() -> GPMContextBundle:
    return _simple_bundle()


@pytest.fixture
def normalization_prompt(bundle: GPMContextBundle) -> str:
    return build_qwen_gpm_normalization_prompt(bundle)


# ── normalization prompt ──────────────────────────────────────────────────────

def test_normalization_prompt_json_only(normalization_prompt: str) -> None:
    assert "JSON only" in normalization_prompt


def test_normalization_prompt_no_invent_prices(normalization_prompt: str) -> None:
    assert "Do not invent prices" in normalization_prompt


def test_normalization_prompt_no_invent_moq(normalization_prompt: str) -> None:
    assert "Do not invent MOQ" in normalization_prompt


def test_normalization_prompt_includes_evidence_ids(normalization_prompt: str) -> None:
    assert "evidence_ids" in normalization_prompt


def test_normalization_prompt_no_cloud_instruction(normalization_prompt: str) -> None:
    prompt_lower = normalization_prompt.lower()
    for provider in ("openai", "anthropic", "dashscope", "gemini", "deepseek"):
        assert provider not in prompt_lower


def test_normalization_prompt_human_approval(normalization_prompt: str) -> None:
    prompt_lower = normalization_prompt.lower()
    assert "human approval" in prompt_lower


def test_normalization_prompt_no_order_instruction(normalization_prompt: str) -> None:
    prompt_lower = normalization_prompt.lower()
    assert "place order" not in prompt_lower or "do not place" in prompt_lower


def test_normalization_prompt_includes_bundle_id(normalization_prompt: str, bundle: GPMContextBundle) -> None:
    assert bundle.bundle_id in normalization_prompt


def test_normalization_prompt_no_credentials() -> None:
    ev = [GPMEvidenceReference(
        id="ev_001", source_type="api_sample", source_id="s1",
        payload_excerpt={"price": "30", "api_key": "TOP_SECRET"},
    )]
    bundle = GPMContextBundle(
        bundle_id="b_cred", data_mode="mock",
        requirement={"product": "shirt"}, evidence=ev,
    )
    prompt = build_qwen_gpm_normalization_prompt(bundle)
    assert "TOP_SECRET" not in prompt
    assert "api_key" not in prompt


# ── quote reasoning prompt ────────────────────────────────────────────────────

def test_quote_reasoning_prompt_json_only(bundle: GPMContextBundle) -> None:
    prompt = build_qwen_quote_reasoning_prompt(
        bundle,
        supplier_quote={"unit_price": 38.5, "currency": "CNY"},
        benchmark_summary={"benchmark_low": 28.0, "benchmark_median": 32.0},
    )
    assert "JSON only" in prompt


def test_quote_reasoning_prompt_human_approval_true(bundle: GPMContextBundle) -> None:
    prompt = build_qwen_quote_reasoning_prompt(
        bundle,
        supplier_quote={"unit_price": 38.5, "currency": "CNY"},
        benchmark_summary={},
    )
    assert "human_approval_required" in prompt


def test_canonical_normalization_prompt_has_evidence(bundle: GPMContextBundle) -> None:
    prompt = build_qwen_gpm_normalization_prompt(bundle)
    assert "ev_001" in prompt


# ── canonical scenario via MockContextRetriever ───────────────────────────────

def test_canonical_bundle_normalization_prompt() -> None:
    bundle = MockContextRetriever().build_gpm_context(
        tenant_id=None, project_id=None, rfq_id=None, supplier_response_id=None
    )
    prompt = build_qwen_gpm_normalization_prompt(bundle)
    assert "JSON only" in prompt
    assert len(prompt) > 200  # Contains real evidence data
