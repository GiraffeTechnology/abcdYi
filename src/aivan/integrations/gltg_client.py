"""Thin HTTP client for the standalone GLTG service.

GLTG (lead-time / path-enumeration / reforecasting) lives in its own service:
    https://github.com/GiraffeTechnology/GLTG

This client is the ONLY way aivan talks to GLTG. It does not calculate
lead time, enumerate paths, or reforecast locally, and it never falls back to a
local calculation when GLTG is unavailable -- failures are surfaced as
structured errors so callers can decide what to do.

Configuration (environment):
    GLTG_API_BASE_URL        default http://localhost:8090
    GLTG_API_TIMEOUT_SECONDS default 30
    GLTG_SERVICE_AUTH_SECRET required for tenant-bound v2 requests
"""


from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Optional

import httpx

DEFAULT_BASE_URL = "http://localhost:8090"
DEFAULT_TIMEOUT_SECONDS = 30.0

# Process-wide transport override. Tests install an httpx.MockTransport here so
# the whole app talks to a faithful in-memory GLTG without a live server.
_DEFAULT_TRANSPORT: Optional["httpx.BaseTransport"] = None


def set_default_transport(transport: Optional["httpx.BaseTransport"]) -> None:
    """Install (or clear) a process-wide default transport for the GLTG client."""
    if transport is not None and os.environ.get("AIVAN_ENV", "local").strip().lower() == "production":
        raise RuntimeError("GLTG test transport is forbidden in production")
    global _DEFAULT_TRANSPORT
    _DEFAULT_TRANSPORT = transport


@dataclass
class GLTGClientResult:
    """Structured result wrapper. Never raises GLTG failures at the call site."""

    ok: bool
    data: Optional[dict]
    error: Optional[str]
    status_code: Optional[int]


class GLTGClient:
    """Synchronous HTTP client for the GLTG API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("GLTG_API_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        if timeout_seconds is not None:
            self.timeout = timeout_seconds
        else:
            self.timeout = float(os.environ.get("GLTG_API_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
        # Injectable transport keeps unit tests off the network (httpx.MockTransport).
        # Falls back to the process-wide default installed via set_default_transport.
        self._transport = transport if transport is not None else _DEFAULT_TRANSPORT
        if self._transport is not None and os.environ.get("AIVAN_ENV", "local").strip().lower() == "production":
            raise RuntimeError("GLTG test transport is forbidden in production")

    # ------------------------------------------------------------------ #
    # transport
    # ------------------------------------------------------------------ #
    def _request(self, method: str, path: str, json: Optional[dict] = None, *, headers: Optional[dict[str, str]] = None) -> GLTGClientResult:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout, transport=self._transport, follow_redirects=False) as client:
                resp = client.request(method, url, json=json, headers=headers)
        except httpx.TimeoutException as exc:
            return GLTGClientResult(False, None, "GLTG request timed out", None)
        except httpx.HTTPError as exc:
            return GLTGClientResult(False, None, "GLTG connection error", None)

        if resp.status_code != 200:
            return GLTGClientResult(
                False, None, f"GLTG returned HTTP {resp.status_code}", resp.status_code
            )
        try:
            data = resp.json()
            if not isinstance(data, dict):
                raise ValueError("expected JSON object")
            return GLTGClientResult(True, data, None, resp.status_code)
        except ValueError as exc:
            return GLTGClientResult(False, None, "GLTG returned invalid JSON", resp.status_code)

    # ------------------------------------------------------------------ #
    # endpoints
    # ------------------------------------------------------------------ #
    def health(self) -> GLTGClientResult:
        return self._request("GET", "/health")

    def version(self) -> GLTGClientResult:
        return self._request("GET", "/version")

    def estimate_lead_time(
        self,
        order: dict[str, Any],
        suppliers: list[dict[str, Any]],
        constraints: Optional[dict[str, Any]] = None,
    ) -> GLTGClientResult:
        if not isinstance(order, dict) or "quantity" not in order:
            return GLTGClientResult(False, None, "invalid order payload: 'quantity' required", None)
        payload = {"order": order, "suppliers": suppliers or [], "constraints": constraints or {}}
        return self._request("POST", "/v1/lead-time/estimate", json=payload)

    def simulate_lead_time_v2(self, payload: dict[str, Any]) -> GLTGClientResult:
        order = payload.get("order") if isinstance(payload, dict) else None
        if not isinstance(order, dict) or "quantity" not in order:
            return GLTGClientResult(False, None, "invalid v2 payload: order.quantity required", None)
        tenant = payload.get("tenant_id")
        secret = os.environ.get("GLTG_SERVICE_AUTH_SECRET", "")
        if any(not isinstance(value, str) or not value.strip() or not value.isascii()
               or any(ord(char) < 32 or ord(char) == 127 for char in value)
               for value in (tenant, secret)):
            return GLTGClientResult(False, None, "GLTG_TRUSTED_PROFILE_MISSING", None)
        return self._request("POST", "/v2/lead-time/simulate", json=payload, headers={
            "X-Service-Tenant-ID": tenant, "X-Service-Auth": secret,
        })

    def enumerate_paths(
        self,
        order: dict[str, Any],
        suppliers: list[dict[str, Any]],
        constraints: Optional[dict[str, Any]] = None,
    ) -> GLTGClientResult:
        if not isinstance(order, dict) or "quantity" not in order:
            return GLTGClientResult(False, None, "invalid order payload: 'quantity' required", None)
        payload = {"order": order, "suppliers": suppliers or [], "constraints": constraints or {}}
        return self._request("POST", "/v1/paths/enumerate", json=payload)

    def reforecast(
        self,
        order: dict[str, Any],
        suppliers: list[dict[str, Any]],
        events: list[dict[str, Any]],
        constraints: Optional[dict[str, Any]] = None,
    ) -> GLTGClientResult:
        if not isinstance(order, dict) or "quantity" not in order:
            return GLTGClientResult(False, None, "invalid order payload: 'quantity' required", None)
        payload = {
            "order": order,
            "suppliers": suppliers or [],
            "events": events or [],
            "constraints": constraints or {},
        }
        return self._request("POST", "/v1/reforecast", json=payload)
