import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from api.main import app
from src.db.base import AsyncSessionLocal
from api.auth import hash_password


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def seed_user(db):
    from src.db.models.user import User
    from src.db.models.tenant import Tenant

    tenant = Tenant(name="Test Tenant", slug=f"test-{uuid.uuid4().hex[:8]}")
    db.add(tenant)
    await db.flush()

    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        tenant_id=tenant.id,
        email=email,
        hashed_password=hash_password("testpassword"),
    )
    db.add(user)
    await db.commit()
    return {
        "email": user.email,
        "password": "testpassword",
        "user_id": str(user.id),
        "tenant_id": str(tenant.id),
    }


@pytest.fixture
async def auth_client(client, seed_user):
    resp = await client.post(
        "/api/auth/login",
        data={
            "username": seed_user["email"],
            "password": seed_user["password"],
        },
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
async def seed_participant(auth_client):
    resp = await auth_client.post(
        "/api/participants",
        json={"name": "Seed Participant Co.", "country": "CN"},
    )
    assert resp.status_code == 201, f"Create participant failed: {resp.text}"
    return resp.json()


@pytest.fixture
async def seed_project(auth_client):
    resp = await auth_client.post(
        "/api/projects",
        json={"title": "Test Project"},
    )
    assert resp.status_code == 201, f"Create project failed: {resp.text}"
    return resp.json()


@pytest.fixture
async def seed_inquiry(auth_client, seed_project):
    resp = await auth_client.post(
        f"/api/projects/{seed_project['id']}/buyer-inquiries",
        json={"raw_text": "We need 10,000 white cotton shirts, FOB Shenzhen, delivery in 45 days."},
    )
    assert resp.status_code == 201, f"Create inquiry failed: {resp.text}"
    data = resp.json()
    data["project_id"] = seed_project["id"]
    return data


@pytest.fixture
async def seed_form(auth_client, seed_inquiry):
    resp = await auth_client.post(
        f"/api/projects/{seed_inquiry['project_id']}/dynamic-forms",
        json={"inquiry_id": seed_inquiry["id"]},
    )
    assert resp.status_code == 201, f"Create form failed: {resp.text}"
    data = resp.json()
    return {"form_id": str(data["form_id"]), "version_id": str(data["id"]), **data}


@pytest.fixture
async def seed_locked_form(auth_client, seed_form):
    resp = await auth_client.post(f"/api/dynamic-forms/{seed_form['form_id']}/lock")
    assert resp.status_code == 200, f"Lock form failed: {resp.text}"
    return seed_form
