"""HTTP client for giraffe-db API. abcdYi consumes giraffe-db ONLY through this boundary."""
from __future__ import annotations

from urllib.parse import quote

import httpx


class GiraffeDBClientError(Exception):
    """Raised when giraffe-db HTTP calls fail."""


class GiraffeDBClient:
    """Thin httpx wrapper for the giraffe-db HTTP API."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        tenant_id: str | None = None,
        operator_id: str | None = None,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        service_auth_secret: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._tenant_id = tenant_id
        self._operator_id = operator_id
        self._api_key = api_key
        self._service_auth_secret = service_auth_secret
        self._transport = transport

    def _headers(self, tenant_id: str | None = None) -> dict[str, str]:
        if self._tenant_id and tenant_id and self._tenant_id != tenant_id:
            raise GiraffeDBClientError("giraffe-db request tenant mismatch")
        effective_tenant = tenant_id or self._tenant_id
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if effective_tenant:
            headers["X-Service-Tenant-ID"] = effective_tenant
        if self._operator_id:
            headers["X-Giraffe-Operator-ID"] = self._operator_id
        if self._service_auth_secret:
            headers["X-Service-Auth"] = self._service_auth_secret
        for value in headers.values():
            if not isinstance(value, str) or not value.isascii() or any(ord(char) < 32 or ord(char) == 127 for char in value):
                raise GiraffeDBClientError("giraffe-db invalid service identity")
        return headers

    def _make_client(self, tenant_id: str | None = None) -> httpx.Client:
        kwargs: dict = {
            "base_url": self._base_url,
            "headers": self._headers(tenant_id),
            "follow_redirects": False,
            "timeout": self._timeout,
        }
        if self._transport is not None:
            kwargs["transport"] = self._transport
        return httpx.Client(**kwargs)

    def _raise_for_status(self, response: httpx.Response) -> None:
        if not 200 <= response.status_code < 300:
            raise GiraffeDBClientError(f"giraffe-db returned HTTP {response.status_code}")

    def _context_response(self, response: httpx.Response, tenant_id: str | None) -> dict:
        self._raise_for_status(response)
        try:
            data = response.json()
        except ValueError as exc:
            raise GiraffeDBClientError("giraffe-db invalid JSON response") from exc
        if not isinstance(data, dict) or (tenant_id and data.get("tenant_id") != tenant_id):
            raise GiraffeDBClientError("giraffe-db context response tenant mismatch")
        return data

    def healthz(self) -> dict:
        try:
            with self._make_client() as client:
                response = client.get("/healthz")
                self._raise_for_status(response)
                return response.json()
        except httpx.HTTPError:
            raise GiraffeDBClientError(
                "giraffe-db context retriever failed: service unreachable"
            )

    def schema_version(self) -> dict:
        try:
            with self._make_client() as client:
                response = client.get("/api/data/schema-version")
                self._raise_for_status(response)
                return response.json()
        except httpx.HTTPError:
            raise GiraffeDBClientError(
                "giraffe-db context retriever failed: service unreachable"
            )

    def create_gpm_context(self, payload: dict) -> dict:
        tenant_id = payload.get("tenant_id") or self._tenant_id
        try:
            with self._make_client(tenant_id) as client:
                response = client.post("/api/data/gpm/context", json=payload)
                return self._context_response(response, tenant_id)
        except httpx.HTTPError as exc:
            raise GiraffeDBClientError("giraffe-db context service unavailable") from exc

    def get_gpm_context(self, context_id: str) -> dict:
        try:
            with self._make_client() as client:
                response = client.get(f"/api/data/gpm/context/{quote(context_id, safe='')}")
                return self._context_response(response, self._tenant_id)
        except httpx.HTTPError as exc:
            raise GiraffeDBClientError("giraffe-db context service unavailable") from exc

    def create_gltg_context(self, payload: dict) -> dict:
        tenant_id = payload.get("tenant_id") or self._tenant_id
        try:
            with self._make_client(tenant_id) as client:
                response = client.post("/api/data/gltg/context", json=payload)
                return self._context_response(response, tenant_id)
        except httpx.HTTPError as exc:
            raise GiraffeDBClientError("giraffe-db context service unavailable") from exc

    def get_gltg_context(self, context_id: str) -> dict:
        try:
            with self._make_client() as client:
                response = client.get(f"/api/data/gltg/context/{quote(context_id, safe='')}")
                return self._context_response(response, self._tenant_id)
        except httpx.HTTPError as exc:
            raise GiraffeDBClientError("giraffe-db context service unavailable") from exc

    def list_projects(self, **params) -> list[dict]:
        return self._list("/api/data/projects", params)

    def list_rfqs(self, **params) -> list[dict]:
        return self._list("/api/data/rfqs", params)

    def list_supplier_responses(self, **params) -> list[dict]:
        return self._list("/api/data/supplier-responses", params)

    def list_pricing_evidence(self, **params) -> list[dict]:
        return self._list("/api/data/gpm/pricing-evidence", params)

    def list_lead_time_evidence(self, **params) -> list[dict]:
        return self._list("/api/data/lead-time-evidence", params)

    def list_execution_events(self, **params) -> list[dict]:
        return self._list("/api/data/execution-events", params)

    def _list(self, path: str, params: dict) -> list[dict]:
        try:
            with self._make_client(params.get("tenant_id")) as client:
                response = client.get(
                    path,
                    params={k: v for k, v in params.items() if v is not None},
                )
                self._raise_for_status(response)
                return response.json()
        except httpx.HTTPError:
            raise GiraffeDBClientError(
                "giraffe-db context retriever failed: service unreachable"
            )
