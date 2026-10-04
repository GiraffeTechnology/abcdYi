"""Tenant-bound HTTP contract for a selected private provider's confirmed POs.

The provider is selected by operator configuration. No request can choose a URL,
credential, provider identity, or service tenant. This adapter performs no buyer
confirmation and sends no supplier communication.
"""
from __future__ import annotations

import json
import os
import re
from urllib.parse import urlsplit

import httpx

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,254}$")


class ConfirmedOrderError(RuntimeError):
    def __init__(self, code: str, status_code: int = 502):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


def require_id(value: object) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ConfirmedOrderError("PROVIDER_ID_INVALID", 422)
    return value


class ConfirmedOrderProvider:
    def __init__(self, *, local_tenant_id: str, transport: httpx.BaseTransport | None = None):
        self.provider_id = require_id(os.environ.get("ABCDYI_PRIVATE_DATA_PROVIDER_ID", ""))
        self.tenant_id = require_id(local_tenant_id)
        raw_mapping = os.environ.get("ABCDYI_PRIVATE_DATA_TENANT_MAP")
        if raw_mapping:
            try:
                mapping = json.loads(raw_mapping)
                if not isinstance(mapping, dict) or any(not isinstance(value, str) for value in mapping.values()):
                    raise ValueError("invalid mapping")
                if len(set(mapping.values())) != len(mapping):
                    raise ValueError("ambiguous tenant mapping")
                self.tenant_id = require_id(mapping[local_tenant_id])
            except (ValueError, KeyError, TypeError) as exc:
                raise ConfirmedOrderError("PROVIDER_TENANT_MAPPING_REQUIRED", 503) from exc
        self.base_url = os.environ.get("GIRAFFE_DB_BASE_URL", "").strip().rstrip("/")
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ConfirmedOrderError("PROVIDER_ENDPOINT_REQUIRED", 503)
        self._secret = os.environ.get("GIRAFFE_DB_SERVICE_AUTH_SECRET", "")
        if not self._secret or not self._secret.isascii() or any(ord(char) < 32 or ord(char) == 127 for char in self._secret):
            raise ConfirmedOrderError("PROVIDER_SERVICE_IDENTITY_REQUIRED", 503)
        if transport is not None and os.environ.get("AIVAN_ENV", "local").lower() == "production":
            raise ConfirmedOrderError("PROVIDER_TEST_TRANSPORT_FORBIDDEN", 503)
        self._transport = transport

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        try:
            with httpx.Client(timeout=10, transport=self._transport, follow_redirects=False) as client:
                response = client.request(method, self.base_url + path, json=payload, headers={
                    "X-Service-Tenant-ID": self.tenant_id,
                    "X-Service-Auth": self._secret,
                })
        except httpx.HTTPError as exc:
            raise ConfirmedOrderError("PROVIDER_UNAVAILABLE", 503) from exc
        if response.status_code != 200:
            code = response.status_code
            raise ConfirmedOrderError(f"PROVIDER_HTTP_{code}", code if code in {404, 409, 422} else 502)
        try:
            data = response.json()
        except ValueError as exc:
            raise ConfirmedOrderError("PROVIDER_RESPONSE_INVALID") from exc
        if not isinstance(data, dict) or data.get("tenant_id") != self.tenant_id:
            raise ConfirmedOrderError("PROVIDER_RESPONSE_TENANT_MISMATCH")
        return data

    def get_order(self, po_id: str) -> dict:
        po_id = require_id(po_id)
        data = self._request("GET", f"/api/data/purchase-orders/{po_id}")
        if data.get("po_id") != po_id or data.get("status") != "confirmed":
            raise ConfirmedOrderError("PROVIDER_ORDER_NOT_CONFIRMED", 409)
        if not isinstance(data.get("source_snapshot_hash"), str) or not re.fullmatch(r"[0-9a-f]{64}", data["source_snapshot_hash"]):
            raise ConfirmedOrderError("PROVIDER_CONFIRMED_SNAPSHOT_REQUIRED", 409)
        return data

    def get_execution(self, po_id: str) -> dict:
        po_id = require_id(po_id)
        result = self._request("GET", f"/api/data/purchase-orders/{po_id}/execution-state")
        if result.get("po_id") != po_id or type(result.get("revision")) is not int or result["revision"] < 0:
            raise ConfirmedOrderError("PROVIDER_EXECUTION_RESPONSE_INVALID")
        return result

    def associate(self, po_id: str, state: dict) -> dict:
        """CAS once, then require authoritative readback, including lost replies."""
        current = self.get_execution(po_id)
        if current.get("state") is not None:
            return current
        try:
            self._request("POST", f"/api/data/purchase-orders/{require_id(po_id)}/execution-state", {
                "expected_revision": current["revision"], "state": state,
            })
        except ConfirmedOrderError as exc:
            if exc.code != "PROVIDER_HTTP_409" and exc.status_code not in {502, 503}:
                raise
            # A timeout or malformed reply cannot prove that the write failed.
            # Reconcile the same PO; never create another order on uncertainty.
        return self.get_execution(po_id)
