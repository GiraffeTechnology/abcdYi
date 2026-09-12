"""A non-ASCII credential must be rejected, not crash the server.

ASGI decodes request headers as latin-1, so a client that sends a single raw
header byte in 0x80-0xFF hands the auth path a ``str`` containing a code point
above U+007F. ``hmac.compare_digest`` raises ``TypeError`` on exactly that
input. Before the fix an unauthenticated caller could turn a protected route
into an unhandled 500 with one byte, on three independent surfaces: the GPM
service bearer key, the embedded AIVAN API key, and the logistics webhook
signature check.

The request-level tests build the ASGI scope by hand. That is deliberate:
``TestClient`` (and the httpx stack under it) encodes header values before the
request is ever sent, so a ``TestClient``-based test raises
``UnicodeEncodeError`` in the client and passes whether or not the server is
fixed. ``test_testclient_cannot_reach_this`` pins that trap.
"""

from __future__ import annotations

import hmac

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from aivan.api.main import _require_api_key
from aivan.api.secure_compare import secure_compare_str
from src.gpm.api.auth import require_gpm_auth
from src.logistics.providers.cainiao_like_provider import CainiaoLikeProvider

RAW_NON_ASCII = b"\xff"
DECODED_NON_ASCII = RAW_NON_ASCII.decode("latin-1")
SECRET = "expected-secret"


def _request(headers: list[tuple[bytes, bytes]], method: str = "POST") -> Request:
    """A Starlette Request carrying raw header bytes, with no client in between."""
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.1"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": "/api/projects",
            "raw_path": b"/api/projects",
            "query_string": b"",
            "root_path": "",
            "headers": headers,
            "client": ("127.0.0.1", 54321),
            "server": ("testserver", 80),
        }
    )


def test_raw_byte_really_decodes_to_non_ascii():
    """Guard the premise: the wire byte must survive as a non-ASCII str."""
    request = _request([(b"x-aivan-api-key", RAW_NON_ASCII)])
    assert request.headers.get("X-AIVAN-API-Key") == DECODED_NON_ASCII
    assert any(ord(ch) > 0x7F for ch in DECODED_NON_ASCII)


def test_compare_digest_would_raise_on_this_input():
    """Pin why the guard exists: the stdlib call this replaced raises here."""
    with pytest.raises(TypeError):
        hmac.compare_digest(DECODED_NON_ASCII, SECRET)


def test_secure_compare_str_rejects_non_ascii_without_raising():
    assert secure_compare_str(DECODED_NON_ASCII, SECRET) is False


def test_secure_compare_str_still_matches_equal_secrets():
    assert secure_compare_str(SECRET, SECRET) is True
    assert secure_compare_str(SECRET, SECRET[:-1] + "x") is False


def test_secure_compare_str_handles_lone_surrogates():
    """Strict encoding would raise UnicodeEncodeError; surrogateescape must not."""
    assert secure_compare_str("\udcff", SECRET) is False


def test_aivan_non_ascii_api_key_is_403_not_500(monkeypatch):
    monkeypatch.setenv("AIVAN_API_KEY", SECRET)
    monkeypatch.delenv("AIVAN_AUTH_SECRET", raising=False)

    with pytest.raises(HTTPException) as excinfo:
        _require_api_key(_request([(b"x-aivan-api-key", RAW_NON_ASCII)]))
    assert excinfo.value.status_code == 403


def test_aivan_non_ascii_bearer_token_is_403_not_500(monkeypatch):
    monkeypatch.delenv("AIVAN_API_KEY", raising=False)
    monkeypatch.setenv("AIVAN_AUTH_SECRET", SECRET)

    with pytest.raises(HTTPException) as excinfo:
        _require_api_key(_request([(b"authorization", b"Bearer " + RAW_NON_ASCII)]))
    assert excinfo.value.status_code == 403


def test_aivan_correct_key_still_authenticates(monkeypatch):
    monkeypatch.setenv("AIVAN_API_KEY", SECRET)
    monkeypatch.delenv("AIVAN_AUTH_SECRET", raising=False)

    assert _require_api_key(_request([(b"x-aivan-api-key", SECRET.encode())])) is None


def test_gpm_non_ascii_bearer_key_is_401_not_500(monkeypatch):
    monkeypatch.setenv("GPM_API_KEY", SECRET)

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=DECODED_NON_ASCII
    )
    with pytest.raises(HTTPException) as excinfo:
        require_gpm_auth(credentials=credentials)
    assert excinfo.value.status_code == 401


def test_gpm_correct_bearer_key_still_authenticates(monkeypatch):
    monkeypatch.setenv("GPM_API_KEY", SECRET)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=SECRET)
    context = require_gpm_auth(
        credentials=credentials, x_giraffe_tenant_id="tenant-1"
    )
    assert context.auth_method == "api_key"


def test_logistics_non_ascii_webhook_signature_is_false_not_500(monkeypatch):
    """An unauthenticated webhook caller must not be able to raise TypeError."""
    monkeypatch.setenv("GIRAFFE_ENV", "production")
    monkeypatch.setenv("CAINIAO_LIKE_WEBHOOK_SECRET", SECRET)
    provider = CainiaoLikeProvider()

    assert (
        provider.verify_webhook_signature(
            b"{}", {"X-Cainiao-Signature": DECODED_NON_ASCII}
        )
        is False
    )


def test_testclient_cannot_reach_this():
    """Documents why these tests do not use TestClient.

    httpx encodes header values before sending, so a TestClient-based version
    fails in the client and never exercises the server. A test written that
    way passes against unfixed code.
    """
    import httpx

    with pytest.raises(UnicodeEncodeError):
        httpx.Headers({"X-AIVAN-API-Key": DECODED_NON_ASCII}).raw
