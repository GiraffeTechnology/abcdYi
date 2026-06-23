"""Unit tests for SampleComparator filtering."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest

from src.gpm.models.semantic_normalization import GPMSemanticNormalization
from src.gpm.normalization.sample_comparator import SampleComparator


@dataclass
class _Sample:
    id: str
    product_title: str
    usable_for_benchmark: bool = True


def _make_norm(sample_id: str, score: float, comparable: bool = True) -> GPMSemanticNormalization:
    return GPMSemanticNormalization(
        sample_id=sample_id,
        is_comparable=comparable,
        comparability_score=Decimal(str(score)),
        reason="test",
    )


def test_sample_below_threshold_excluded() -> None:
    comparator = SampleComparator()
    sample = _Sample(id="s1", product_title="shirt")
    norm = _make_norm("s1", 0.40)
    assert comparator.is_usable(sample, norm) is False


def test_sample_above_threshold_included() -> None:
    comparator = SampleComparator()
    sample = _Sample(id="s2", product_title="shirt")
    norm = _make_norm("s2", 0.85)
    assert comparator.is_usable(sample, norm) is True


def test_missing_normalization_excludes_sample() -> None:
    comparator = SampleComparator()
    sample = _Sample(id="s3", product_title="shirt")
    assert comparator.is_usable(sample, None) is False


def test_unusable_for_benchmark_excluded() -> None:
    comparator = SampleComparator()
    sample = _Sample(id="s4", product_title="shirt", usable_for_benchmark=False)
    norm = _make_norm("s4", 0.90)
    assert comparator.is_usable(sample, norm) is False


def test_filter_usable_returns_correct_pairs() -> None:
    comparator = SampleComparator()
    s1 = _Sample(id="s1", product_title="shirt")
    s2 = _Sample(id="s2", product_title="shirt")
    s3 = _Sample(id="s3", product_title="bucket")
    norms = [
        _make_norm("s1", 0.85),
        _make_norm("s2", 0.30),
        _make_norm("s3", 0.20),
    ]
    pairs = comparator.filter_usable([s1, s2, s3], norms)
    assert len(pairs) == 1
    assert pairs[0][0].id == "s1"
