import pytest


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
