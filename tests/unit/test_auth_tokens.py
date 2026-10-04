"""Authentication compatibility checks for the PyJWT dependency migration."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from api import auth


@pytest.fixture(autouse=True)
def signing_settings(monkeypatch):
    monkeypatch.setattr(auth.settings, "SECRET_KEY", "synthetic-auth-test-signing-key-0000001" * 2)
    monkeypatch.setattr(auth.settings, "ALGORITHM", "HS256")


def test_access_token_preserves_subject_and_expiry():
    before = datetime.now(timezone.utc)
    token = auth.create_access_token("synthetic-user", timedelta(minutes=5))
    payload = jwt.decode(token, auth.settings.SECRET_KEY, algorithms=["HS256"])
    assert jwt.get_unverified_header(token)["alg"] == "HS256"
    assert payload["sub"] == "synthetic-user"
    assert int((before + timedelta(minutes=5)).timestamp()) <= payload["exp"]
    assert payload["exp"] <= int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
    assert auth.decode_token(token) == "synthetic-user"


def test_expired_token_is_rejected():
    token = auth.create_access_token("synthetic-user", timedelta(seconds=-1))
    assert auth.decode_token(token) is None


def test_forged_signature_is_rejected():
    token = jwt.encode({"sub": "synthetic-user"}, "synthetic-wrong-signing-key-00000000001", algorithm="HS256")
    assert auth.decode_token(token) is None


@pytest.mark.parametrize("algorithm", ["HS384", "HS512", "none"])
def test_unapproved_algorithm_is_rejected(algorithm):
    key = "" if algorithm == "none" else auth.settings.SECRET_KEY
    token = jwt.encode({"sub": "synthetic-user"}, key, algorithm=algorithm)
    assert auth.decode_token(token) is None


@pytest.mark.parametrize("token", ["", "not-a-token", "a.b.c"])
def test_malformed_token_is_rejected(token):
    assert auth.decode_token(token) is None


@pytest.mark.parametrize("issuer", [None, "synthetic-issuer"])
def test_issuer_remains_optional_without_a_new_issuer_constraint(issuer):
    payload = {"sub": "synthetic-user"}
    if issuer is not None:
        payload["iss"] = issuer
    token = jwt.encode(payload, auth.settings.SECRET_KEY, algorithm="HS256")
    assert auth.decode_token(token) == "synthetic-user"


def test_missing_subject_does_not_authenticate():
    token = jwt.encode({"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, auth.settings.SECRET_KEY, algorithm="HS256")
    assert auth.decode_token(token) is None


def test_non_ascii_credentials_round_trip_without_normalization():
    password = "p\u00e4ssw\u00f6rd-\u5bc6\u7801-\U0001f512"
    hashed = auth.hash_password(password)
    assert auth.verify_password(password, hashed)
    assert not auth.verify_password("passw\u00f6rd-\u5bc6\u7801-\U0001f512", hashed)
    subject = "user-\u00e9-\u7528\u6237"
    assert auth.decode_token(auth.create_access_token(subject)) == subject
