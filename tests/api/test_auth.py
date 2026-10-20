import pytest

from datetime import timedelta

import jwt
from sqlalchemy import select

from api import auth
from src.db.models.user import User


@pytest.mark.asyncio
async def test_login_success(client, seed_user):
    resp = await client.post(
        "/api/auth/login",
        data={
            "username": seed_user["email"],
            "password": seed_user["password"],
        },
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client, seed_user):
    resp = await client.post(
        "/api/auth/login",
        data={
            "username": seed_user["email"],
            "password": "wrong",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_non_ascii_password_login_and_authenticated_identity(client, seed_user, db):
    password = "p\u00e4ssw\u00f6rd-\u5bc6\u7801-\U0001f512"
    user = (await db.execute(select(User).where(User.email == seed_user["email"]))).scalar_one()
    user.hashed_password = auth.hash_password(password)
    await db.commit()
    response = await client.post(
        "/api/auth/login", data={"username": seed_user["email"], "password": password},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    assert auth.decode_token(token) == seed_user["user_id"]
    identity = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert identity.status_code == 200, identity.text
    assert identity.json()["id"] == seed_user["user_id"]
    assert identity.json()["roles"] == ["BUYER"]


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_kind", ["expired", "forged", "wrong-algorithm", "unsigned"])
async def test_invalid_token_cannot_authenticate_existing_user(client, seed_user, invalid_kind):
    payload = {"sub": seed_user["user_id"]}
    if invalid_kind == "expired":
        token = auth.create_access_token(seed_user["user_id"], timedelta(seconds=-1))
    elif invalid_kind == "forged":
        token = jwt.encode(payload, "synthetic-untrusted-signing-key-000001", algorithm="HS256")
    elif invalid_kind == "wrong-algorithm":
        token = jwt.encode(payload, auth.settings.SECRET_KEY, algorithm="HS512")
    else:
        token = jwt.encode(payload, "", algorithm="none")
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401, response.text
