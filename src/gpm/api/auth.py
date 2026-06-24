from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass

from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_http_bearer = HTTPBearer(auto_error=False)

# Profiles and retrievers where keyless dev_open access is safe
_DEV_OPEN_PROFILES = frozenset({"local", "ci"})
_DEV_OPEN_RETRIEVERS = frozenset({"mock"})


@dataclass
class GPMAuthContext:
    tenant_id: str | None
    operator_id: str | None
    auth_method: str  # "api_key" | "dev_open"


def _dev_open_allowed() -> bool:
    """Return True only when both profile and retriever are safe for keyless access."""
    profile = os.getenv("GPM_RUNTIME_PROFILE", "local").strip()
    retriever = os.getenv("GPM_CONTEXT_RETRIEVER", "mock").strip()
    return profile in _DEV_OPEN_PROFILES and retriever in _DEV_OPEN_RETRIEVERS


def require_gpm_auth(
    credentials: HTTPAuthorizationCredentials | None = Security(_http_bearer),
    x_giraffe_tenant_id: str | None = Header(default=None),
    x_giraffe_operator_id: str | None = Header(default=None),
) -> GPMAuthContext:
    """Authenticate GPM API callers via API key.

    When GPM_API_KEY is set, callers must present it as
    'Authorization: Bearer <key>'.

    dev_open mode (no API key required) is only permitted when BOTH:
      - GPM_RUNTIME_PROFILE is 'local' or 'ci'
      - GPM_CONTEXT_RETRIEVER is 'mock'

    server profile or giraffe_db retriever mandates GPM_API_KEY regardless
    of whether a key is presented by the caller.

    Tenant identity comes from X-Giraffe-Tenant-ID header, not the request body.
    """
    expected_key = os.getenv("GPM_API_KEY", "").strip()

    if expected_key:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Missing API key. Provide Authorization: Bearer <key>."},
            )
        if not secrets.compare_digest(credentials.credentials, expected_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid API key."},
            )
        auth_method = "api_key"
    elif _dev_open_allowed():
        logger.debug(
            "GPM_API_KEY not set — running in dev_open mode (profile=%s, retriever=%s).",
            os.getenv("GPM_RUNTIME_PROFILE", "local"),
            os.getenv("GPM_CONTEXT_RETRIEVER", "mock"),
        )
        auth_method = "dev_open"
    else:
        # No key in an environment that requires one (server profile or giraffe_db retriever)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": (
                    "GPM_API_KEY is required when GPM_RUNTIME_PROFILE=server "
                    "or GPM_CONTEXT_RETRIEVER=giraffe_db. "
                    "Set GPM_API_KEY to enable this endpoint."
                ),
                "operator_action_required": True,
            },
        )

    return GPMAuthContext(
        tenant_id=x_giraffe_tenant_id,
        operator_id=x_giraffe_operator_id,
        auth_method=auth_method,
    )


def resolve_tenant_id(req_tenant_id: str | None, auth: GPMAuthContext) -> str | None:
    """Return the authoritative tenant_id, rejecting request/header mismatches.

    X-Giraffe-Tenant-ID (in auth.tenant_id) is always authoritative.
    If req_tenant_id is present and differs, raise 403.
    """
    if auth.tenant_id is not None and req_tenant_id is not None:
        if auth.tenant_id != req_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "tenant_id mismatch: request tenant_id does not match authenticated tenant",
                },
            )
    return auth.tenant_id if auth.tenant_id is not None else req_tenant_id
