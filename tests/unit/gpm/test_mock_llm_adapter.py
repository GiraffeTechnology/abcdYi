"""Unit tests for MockLLMAdapter deterministic normalization."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest

from src.gpm.llm_adapters.mock_llm_adapter import MockLLMAdapter


@dataclass
class _Sample:
    id: str
    product_title: str


@pytest.fixture
def adapter() -> MockLLMAdapter:
    return MockLLMAdapter()


def _req() -> dict:
    return {"product": "men's cotton shirt", "process_tags": ["sewing"]}


def test_shirt_sample_high_comparability_score(adapter: MockLLMAdapter) -> None:
    sample = _Sample(id="s1", product_title="men cotton shirt OEM")
    result = adapter.normalize_price_sample(_req(), sample)
    assert result["comparability_score"] >= 0.80
    assert result["is_comparable"] is True


def test_non_shirt_sample_low_comparability_score(adapter: MockLLMAdapter) -> None:
    sample = _Sample(id="s2", product_title="plastic bucket wholesale")
    result = adapter.normalize_price_sample(_req(), sample)
    assert result["comparability_score"] < 0.50
    assert result["is_comparable"] is False


def test_cotton_sample_normalizes_material(adapter: MockLLMAdapter) -> None:
    sample = _Sample(id="s3", product_title="100% cotton shirt")
    result = adapter.normalize_price_sample(_req(), sample)
    assert result["normalized_material"] == "cotton"


def test_oem_sample_marks_customization_supported(adapter: MockLLMAdapter) -> None:
    sample = _Sample(id="s4", product_title="OEM men shirt")
    result = adapter.normalize_price_sample(_req(), sample)
    assert result["customization_supported"] is True


def test_chinese_oem_keyword(adapter: MockLLMAdapter) -> None:
    sample = _Sample(id="s5", product_title="纯棉衬衫定制")
    result = adapter.normalize_price_sample(_req(), sample)
    assert result["customization_supported"] is True
    assert result["normalized_material"] == "cotton"
