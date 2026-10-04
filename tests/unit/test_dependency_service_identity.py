"""Synthetic transport regressions; these are not live dependency evidence."""
import json

import httpx
import pytest

from aivan.integrations.gltg_client import GLTGClient
from src.gpm.clients.giraffe_db_client import GiraffeDBClient, GiraffeDBClientError


def test_embedded_gltg_v2_propagates_bound_identity(monkeypatch):
    monkeypatch.setenv("GLTG_SERVICE_AUTH_SECRET", "synthetic-service-key")
    captured = []
    def handle(request):
        captured.append(request)
        assert request.headers["X-Service-Tenant-ID"] == "tenant-a"
        assert request.headers["X-Service-Auth"] == "synthetic-service-key"
        assert json.loads(request.content)["tenant_id"] == "tenant-a"
        return httpx.Response(200, json={"quantiles": {"p50_days": 20}})
    result = GLTGClient(transport=httpx.MockTransport(handle)).simulate_lead_time_v2({"tenant_id": "tenant-a", "order": {"quantity": 100}})
    assert result.ok
    assert len(captured) == 1


@pytest.mark.parametrize("tenant,secret", [(None, "test"), ("tenant-a", ""), ("租户", "test"), ("tenant-a", "bad\nkey")])
def test_embedded_gltg_rejects_missing_or_invalid_identity(monkeypatch, tenant, secret):
    monkeypatch.setenv("GLTG_SERVICE_AUTH_SECRET", secret)
    transport = httpx.MockTransport(lambda request: pytest.fail("identity failure must not send"))
    result = GLTGClient(transport=transport).simulate_lead_time_v2({"tenant_id": tenant, "order": {"quantity": 100}})
    assert not result.ok
    assert result.error == "GLTG_TRUSTED_PROFILE_MISSING"


@pytest.mark.parametrize("status", [302, 401, 403, 500])
def test_embedded_gltg_does_not_expose_upstream_error_body(status):
    transport = httpx.MockTransport(lambda request: httpx.Response(status, text="sensitive-provider-body"))
    result = GLTGClient(transport=transport).health()
    assert not result.ok
    assert "sensitive-provider-body" not in result.error


def test_gpm_request_tenants_do_not_leak_through_cached_client():
    tenants = []
    def handle(request):
        tenant = json.loads(request.content)["tenant_id"]
        assert request.headers["X-Service-Tenant-ID"] == tenant
        assert request.headers["X-Service-Auth"] == "synthetic-provider-secret"
        assert "Authorization" not in request.headers
        tenants.append(tenant)
        return httpx.Response(200, json={"id": "context", "tenant_id": tenant})
    client = GiraffeDBClient("http://provider.test", service_auth_secret="synthetic-provider-secret", transport=httpx.MockTransport(handle))
    for tenant in ("tenant-a", "tenant-b", "tenant-a"):
        assert client.create_gpm_context({"tenant_id": tenant})["tenant_id"] == tenant
    assert tenants == ["tenant-a", "tenant-b", "tenant-a"]


def test_gpm_fixed_tenant_rejects_mismatch_without_request():
    client = GiraffeDBClient("http://provider.test", tenant_id="tenant-a", transport=httpx.MockTransport(lambda request: pytest.fail("must not send")))
    with pytest.raises(GiraffeDBClientError, match="request tenant mismatch"):
        client.create_gpm_context({"tenant_id": "tenant-b"})


@pytest.mark.parametrize("body", [{"tenant_id": "tenant-b"}, {"id": "missing-tenant"}, [], "invalid"])
def test_gpm_rejects_unbound_or_foreign_response(body):
    client = GiraffeDBClient("http://provider.test", transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)))
    with pytest.raises(GiraffeDBClientError, match="tenant mismatch"):
        client.create_gpm_context({"tenant_id": "tenant-a"})


def test_embedded_gltg_production_rejects_transport_substitution(monkeypatch):
    monkeypatch.setenv("AIVAN_ENV", "production")
    with pytest.raises(RuntimeError, match="forbidden in production"):
        GLTGClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))
