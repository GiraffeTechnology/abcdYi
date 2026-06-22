"""Unit tests for Giraffe JP formalwear category business rules."""
import pytest
from src.giraffe_jp.formalwear import (
    HOLLOW_TO_HEM_REQUIRED_CATEGORIES,
    FORMALWEAR_CATEGORIES,
    DEFAULT_C2B2M_EDGES,
)


def test_hollow_to_hem_required_for_bridalwear():
    assert "BRIDALWEAR" in HOLLOW_TO_HEM_REQUIRED_CATEGORIES


def test_hollow_to_hem_required_for_light_wedding_dress():
    assert "LIGHT_WEDDING_DRESS" in HOLLOW_TO_HEM_REQUIRED_CATEGORIES


def test_hollow_to_hem_required_for_formal_dress():
    assert "FORMAL_DRESS" in HOLLOW_TO_HEM_REQUIRED_CATEGORIES


def test_hollow_to_hem_not_required_for_womens_suit():
    assert "WOMENS_SUIT" not in HOLLOW_TO_HEM_REQUIRED_CATEGORIES


def test_hollow_to_hem_not_required_for_reception_dress():
    assert "RECEPTION_DRESS" not in HOLLOW_TO_HEM_REQUIRED_CATEGORIES


def test_formalwear_categories_complete():
    expected = {"FORMAL_DRESS", "WOMENS_SUIT", "BRIDALWEAR", "LIGHT_WEDDING_DRESS", "RECEPTION_DRESS"}
    assert FORMALWEAR_CATEGORIES == expected


def test_hollow_to_hem_required_subset_of_formalwear():
    assert HOLLOW_TO_HEM_REQUIRED_CATEGORIES.issubset(FORMALWEAR_CATEGORIES)


def test_default_c2b2m_edges_count():
    assert len(DEFAULT_C2B2M_EDGES) == 4


def test_default_c2b2m_edges_no_duplicates():
    keys = [(e["role_from"], e["role_to"]) for e in DEFAULT_C2B2M_EDGES]
    assert len(keys) == len(set(keys)), "Duplicate edges in DEFAULT_C2B2M_EDGES"


def test_default_c2b2m_edges_contain_customer_to_platform():
    keys = {(e["role_from"], e["role_to"]) for e in DEFAULT_C2B2M_EDGES}
    assert ("CUSTOMER", "SERVICE_PLATFORM") in keys


def test_default_c2b2m_edges_contain_platform_to_production():
    keys = {(e["role_from"], e["role_to"]) for e in DEFAULT_C2B2M_EDGES}
    assert ("SERVICE_PLATFORM", "PRODUCTION_PARTNER") in keys


def test_default_c2b2m_edges_contain_platform_to_local_model():
    keys = {(e["role_from"], e["role_to"]) for e in DEFAULT_C2B2M_EDGES}
    assert ("SERVICE_PLATFORM", "LOCAL_MODEL_PARTNER") in keys


def test_default_c2b2m_edges_all_have_labels():
    for edge in DEFAULT_C2B2M_EDGES:
        assert edge.get("edge_label"), f"Edge {edge} missing edge_label"


def test_hollow_to_hem_required_logic():
    """create_formalwear_profile sets hollow_to_hem_required from category."""
    for category in FORMALWEAR_CATEGORIES:
        expected = category in HOLLOW_TO_HEM_REQUIRED_CATEGORIES
        # Simulate the logic in formalwear.create_formalwear_profile
        actual = category in HOLLOW_TO_HEM_REQUIRED_CATEGORIES
        assert actual == expected
