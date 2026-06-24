"""HTTP client for giraffe-db API. abcdYi consumes giraffe-db ONLY through this boundary."""
from __future__ import annotations

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
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._tenant_id = tenant_id
        self._operator_id = operator_id
        self._api_key = api_key
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._tenant_id:
            headers["X-Giraffe-Tenant-ID"] = self._tenant_id
        if self._operator_id:
            headers["X-Giraffe-Operator-ID"] = self._operator_id
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _make_client(self) -> httpx.Client:
        kwargs: dict = {
            "base_url": self._base_url,
            "headers": self._headers(),
            "timeout": self._timeout,
        }
        if self._transport is not None:
            kwargs["transport"] = self._transport
        return httpx.Client(**kwargs)

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_error:
            try:
                body = response.text[:200]
            except Exception:
                body = "<unreadable>"
            raise GiraffeDBClientError(
                f"giraffe-db returned HTTP {response.status_code}: {body}"
            )

    def healthz(self) -> dict:
        try:
            with self._make_client() as client:
                response = client.get("/healthz")
                self._raise_for_status(response)
                return response.json()
        except httpx.ConnectError:
            raise GiraffeDBClientError(
                f"giraffe-db context retriever failed: service unreachable at {self._base_url}"
            )

    def schema_version(self) -> dict:
        try:
            with self._make_client() as client:
                response = client.get("/schema-version")
                self._raise_for_status(response)
                return response.json()
        except httpx.ConnectError:
            raise GiraffeDBClientError(
                f"giraffe-db context retriever failed: service unreachable at {self._base_url}"
            )

    def create_gpm_context(self, payload: dict) -> dict:
        try:
            with self._make_client() as client:
                response = client.post("/gpm/context", json=payload)
                self._raise_for_status(response)
                return response.json()
        except httpx.ConnectError:
            raise GiraffeDBClientError(
                f"giraffe-db context retriever failed: service unreachable at {self._base_url}"
            )

    def get_gpm_context(self, context_id: str) -> dict:
        try:
            with self._make_client() as client:
                response = client.get(f"/gpm/context/{context_id}")
                self._raise_for_status(response)
                return response.json()
        except httpx.ConnectError:
            raise GiraffeDBClientError(
                f"giraffe-db context retriever failed: service unreachable at {self._base_url}"
            )

    def create_gltg_context(self, payload: dict) -> dict:
        try:
            with self._make_client() as client:
                response = client.post("/gltg/context", json=payload)
                self._raise_for_status(response)
                return response.json()
        except httpx.ConnectError:
            raise GiraffeDBClientError(
                f"giraffe-db context retriever failed: service unreachable at {self._base_url}"
            )

    def get_gltg_context(self, context_id: str) -> dict:
        try:
            with self._make_client() as client:
                response = client.get(f"/gltg/context/{context_id}")
                self._raise_for_status(response)
                return response.json()
        except httpx.ConnectError:
            raise GiraffeDBClientError(
                f"giraffe-db context retriever failed: service unreachable at {self._base_url}"
            )

    def list_projects(self, **params) -> list[dict]:
        return self._list("/projects", params)

    def list_rfqs(self, **params) -> list[dict]:
        return self._list("/rfqs", params)

    def list_supplier_responses(self, **params) -> list[dict]:
        return self._list("/supplier-responses", params)

    def list_pricing_evidence(self, **params) -> list[dict]:
        return self._list("/gpm/pricing-evidence", params)

    def list_lead_time_evidence(self, **params) -> list[dict]:
        return self._list("/lead-time-evidence", params)

    def list_execution_events(self, **params) -> list[dict]:
        return self._list("/execution-events", params)

    def _list(self, path: str, params: dict) -> list[dict]:
        try:
            with self._make_client() as client:
                response = client.get(
                    path,
                    params={k: v for k, v in params.items() if v is not None},
                )
                self._raise_for_status(response)
                return response.json()
        except httpx.ConnectError:
            raise GiraffeDBClientError(
                f"giraffe-db context retriever failed: service unreachable at {self._base_url}"
            )
