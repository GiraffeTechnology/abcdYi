"""Tests for logistics provider registry."""
import os
import pytest
from src.logistics.providers.provider_registry import get_logistics_provider
from src.logistics.providers.base_provider import LogisticsProviderBase
from src.logistics.providers.mock_provider import MockProvider


def test_default_provider_is_mock():
    provider = get_logistics_provider()
    assert isinstance(provider, LogisticsProviderBase)


def test_explicit_mock_provider():
    provider = get_logistics_provider("mock")
    assert isinstance(provider, MockProvider)


def test_mock_provider_has_name():
    provider = get_logistics_provider("mock")
    assert provider.provider_name is not None
    assert len(provider.provider_name) > 0


def test_mock_create_or_bind_shipment():
    provider = get_logistics_provider("mock")
    result = provider.create_or_bind_shipment("SF", "SF123456789012")
    assert isinstance(result, dict)
    assert "provider_shipment_id" in result


def test_cainiao_like_provider():
    provider = get_logistics_provider("cainiao_like")
    assert provider is not None
    assert isinstance(provider, LogisticsProviderBase)


def test_cainiao_like_provider_name():
    provider = get_logistics_provider("cainiao_like")
    assert "cainiao" in provider.provider_name.lower()


def test_provider_fallback_unknown_in_dev():
    provider = get_logistics_provider("totally_unknown_provider_xyz")
    assert isinstance(provider, LogisticsProviderBase)


def test_mock_provider_fetch_tracking_events():
    provider = get_logistics_provider("mock")
    events = provider.fetch_tracking_events("SF", "SF123456789012")
    assert isinstance(events, list)


def test_providers_implement_base_interface():
    for name in ["mock", "cainiao_like"]:
        provider = get_logistics_provider(name)
        assert hasattr(provider, "create_or_bind_shipment")
        assert hasattr(provider, "fetch_tracking_events")
        assert hasattr(provider, "provider_name")
