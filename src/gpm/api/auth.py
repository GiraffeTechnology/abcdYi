from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass

from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_http_bearer = HTTPBearer(auto_error=False)


@dataclass
class GPMAuthContext:
    tenant_id: str | None
    operator_id: str | None
    auth_method: str  # "api_key" | "dev_open"


def require_gpm_auth(
    credentials: HTTPAuthorizationCredentials | None = Security(_http_bearer),
    x_giraffe_tenant_id: str | None = Header(default=None),
    x_giraffe_operator_id: str | None = Header(default=None),
) -> GPMAuthContext:
    """Authenticate GPM API callers via API key.

    When GPM_API_KEY is set, callers must present it as
    'Authorization: Bearer <key>'. When not set, runs in dev_open mode
    (suitable for local dev only — always set GPM_API_KEY in production).

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
    else:
        logger.debug("GPM_API_KEY not set — running in dev_open mode.")
        auth_method = "dev_open"

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
