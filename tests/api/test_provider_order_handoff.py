"""Synthetic same-provider HTTP-boundary handoff and durable local DB tests.

All records below are newly authored synthetic consumer-contract examples. No
provider repository fixture or private dataset is distributed by this test.
"""
import copy
import json
import uuid
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.deps import get_current_user, get_db
from api.main import app
from api.routes.provider_orders import get_confirmed_order_provider
from src.db.base import Base
from src.db.models import Tenant, User, UserRole, Order, Milestone, ExecutionEvent
from src.integrations.confirmed_orders import ConfirmedOrderProvider


def synthetic_order(tenant):
    requirement = {"category": "apparel", "product_type": "cotton shirt", "quantity": 120, "language": "en"}
    authorization = {"actor_id": "synthetic-buyer", "actor_role": "approver", "authorization_basis": "explicit synthetic approval"}
    option = {"option_id": "option-synthetic", "supplier_id": "supplier-synthetic", "quote": {"buyer_unit_price": 15.5, "currency": "USD"}}
    quote = {"quote_id": "quote-synthetic", "procurement_case_id": "case-synthetic", "rfq_id": "rfq-synthetic",
             "supplier_id": "supplier-synthetic", "quote_status": "confirmed", "verification_status": "operator_confirmed",
             "metadata_json": {"selected_option": option, "human_authorization": authorization}}
    return {"po_id": "po-synthetic", "tenant_id": tenant, "status": "confirmed", "selected_quote_id": "quote-synthetic",
            "procurement_case_id": "case-synthetic", "rfq_id": "rfq-synthetic", "supplier_id": "supplier-synthetic", "buyer_id": "buyer-synthetic",
            "accepted_at": "2026-10-04T00:00:00Z", "source_snapshot_hash": "a" * 64,
            "metadata_json": {"source_system": "aivan", "aivan_project_id": "aivan-synthetic", "selected_option_id": "option-synthetic",
                              "human_authorization": authorization, "confirmed_quote_snapshot": quote,
                              "confirmed_requirement_snapshot": {"case": {"requirement": requirement}, "rfq": {"requirement": requirement}}}}


class SyntheticProvider:
    def __init__(self, tenant):
        self.tenant = tenant
        self.order = synthetic_order(tenant)
        self.state = None
        self.revision = 0
        self.writes = 0
        self.lose_reply = False
        self.foreign_response = False
        self.canonical_rejection = False

    def __call__(self, request):
        if request.headers.get("X-Service-Auth") != "synthetic-secret" or request.headers.get("X-Service-Tenant-ID") != self.tenant:
            return httpx.Response(404, json={"error": "record not found"})
        if self.canonical_rejection:
            return httpx.Response(422, json={"error": "canonical_language_validation_failed"})
        if request.url.path.endswith("/execution-state"):
            if request.method == "POST":
                payload = json.loads(request.content)
                if self.revision != payload["expected_revision"]:
                    return httpx.Response(409, json={"error": "revision conflict"})
                self.state = payload["state"]
                self.revision += 1
                self.writes += 1
                if self.lose_reply:
                    raise httpx.ReadTimeout("synthetic response lost", request=request)
            return httpx.Response(200, json={"po_id": self.order["po_id"], "tenant_id": self.tenant,
                "revision": self.revision, "state": self.state, "source_snapshot_hash": self.order["source_snapshot_hash"]})
        response = copy.deepcopy(self.order)
        if self.foreign_response:
            response["tenant_id"] = "foreign-tenant"
        return httpx.Response(200, json=response)


@pytest.fixture
async def handoff(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/consumer.sqlite")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()
    async with sessions() as db:
        db.add(Tenant(id=tenant_id, name="Synthetic test tenant", slug=str(tenant_id)))
        await db.flush()
        db.add(User(id=user_id, tenant_id=tenant_id, email="synthetic@example.invalid", hashed_password="not-a-login-credential"))
        await db.flush()
        db.add(UserRole(user_id=user_id, role_name="PROCUREMENT"))
        await db.commit()
    user = SimpleNamespace(id=user_id, tenant_id=tenant_id)
    fixture = SyntheticProvider(str(tenant_id))
    monkeypatch.setenv("ABCDYI_PRIVATE_DATA_PROVIDER_ID", "synthetic-provider")
    monkeypatch.setenv("GIRAFFE_DB_BASE_URL", "http://provider.invalid")
    monkeypatch.setenv("GIRAFFE_DB_SERVICE_AUTH_SECRET", "synthetic-secret")
    monkeypatch.delenv("ABCDYI_PRIVATE_DATA_TENANT_MAP", raising=False)
    provider = ConfirmedOrderProvider(local_tenant_id=str(tenant_id), transport=httpx.MockTransport(fixture))
    async def db_override():
        async with sessions() as db:
            db.info["confirmed_order_provider"] = provider
            yield db
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_confirmed_order_provider] = lambda: provider
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://consumer.invalid") as client:
        yield client, fixture, sessions, user, engine
    app.dependency_overrides.clear()
    await engine.dispose()


async def import_order(client):
    return await client.post("/api/orders/from-provider-confirmed", json={"purchase_order_id": "po-synthetic"})


async def test_import_is_durable_idempotent_and_preserves_progress(handoff):
    client, provider, sessions, user, engine = handoff
    first = await import_order(client)
    assert first.status_code == 200, first.text
    order = first.json()
    assert order["status"] == "IN_PRODUCTION"
    assert provider.writes == 1
    assert provider.state["local_order_id"] == order["id"]
    assert provider.state["local_project_id"] == order["project_id"]
    qc = await client.post(f"/api/orders/{order['id']}/request-qc")
    assert qc.status_code == 200, qc.text
    assert qc.json()["status"] == "QC_PENDING"
    await engine.dispose()  # A new connection/session cannot depend on prior context.
    replay = await import_order(client)
    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == order["id"]
    assert replay.json()["status"] == "QC_PENDING"
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Order)) == 1
        assert await db.scalar(select(func.count()).select_from(Milestone)) == 12
        assert await db.scalar(select(func.count()).select_from(ExecutionEvent).where(ExecutionEvent.event_type == "PROVIDER_CONFIRMED_ORDER_IMPORTED")) == 1
    assert provider.writes == 2


async def test_import_reconciles_lost_provider_commit_reply(handoff):
    client, provider, *_ = handoff
    provider.lose_reply = True
    response = await import_order(client)
    assert response.status_code == 200, response.text
    assert provider.writes == 1


@pytest.mark.parametrize("mutation", ["draft", "approval", "scope", "requirement", "price", "snapshot"])
async def test_unconfirmed_or_changed_source_cannot_launch_execution(handoff, mutation):
    client, provider, sessions, *_ = handoff
    if mutation == "draft": provider.order["status"] = "draft"
    elif mutation == "approval": provider.order["metadata_json"].pop("human_authorization")
    elif mutation == "scope": provider.order["metadata_json"]["confirmed_quote_snapshot"]["rfq_id"] = "different-rfq"
    elif mutation == "requirement": provider.order["metadata_json"]["confirmed_requirement_snapshot"]["case"]["requirement"] = {}
    elif mutation == "price": provider.order["metadata_json"]["confirmed_quote_snapshot"]["metadata_json"]["selected_option"]["quote"]["buyer_unit_price"] = None
    else: provider.order["source_snapshot_hash"] = None
    response = await import_order(client)
    assert response.status_code == 409, response.text
    assert provider.writes == 0
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Order)) == 0


async def test_provider_response_tenant_is_verified(handoff):
    client, provider, sessions, *_ = handoff
    provider.foreign_response = True
    response = await import_order(client)
    assert response.status_code == 502
    assert provider.writes == 0


async def test_source_change_never_resets_existing_execution(handoff):
    client, provider, *_ = handoff
    first = await import_order(client)
    assert first.status_code == 200
    provider.order["source_snapshot_hash"] = "b" * 64
    changed = await import_order(client)
    assert changed.status_code == 409
    assert changed.json()["detail"]["error"] == "CONFIRMED_SOURCE_CHANGED"
    assert provider.writes == 1


async def test_conflicting_remote_association_is_not_overwritten(handoff):
    client, provider, *_ = handoff
    provider.state = {"local_order_id": str(uuid.uuid4())}
    provider.revision = 1
    response = await import_order(client)
    assert response.status_code == 409
    assert provider.writes == 0


async def test_client_cannot_choose_provider_or_tenant(handoff):
    client, provider, *_ = handoff
    response = await client.post("/api/orders/from-provider-confirmed", json={
        "purchase_order_id": "po-synthetic", "tenant_id": "foreign", "provider_url": "http://foreign.invalid"})
    assert response.status_code == 422
    assert provider.writes == 0


async def test_handoff_requires_authentication(handoff):
    client, provider, *_ = handoff
    app.dependency_overrides.pop(get_current_user)
    response = await import_order(client)
    assert response.status_code == 401
    assert provider.writes == 0


async def test_local_failure_retries_same_provider_association(handoff, monkeypatch):
    client, provider, sessions, *_ = handoff
    import src.order_confirmation.provider_handoff as service
    original = service.emit_event
    async def fail_audit(*args, **kwargs):
        raise RuntimeError("synthetic local transaction failure")
    monkeypatch.setattr(service, "emit_event", fail_audit)
    with pytest.raises(RuntimeError, match="synthetic local transaction failure"):
        await import_order(client)
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Order)) == 0
    assert provider.writes == 1
    monkeypatch.setattr(service, "emit_event", original)
    recovered = await import_order(client)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["id"] == provider.state["local_order_id"]
    assert provider.writes == 1


async def test_repeated_concurrent_import_is_not_duplicate(handoff):
    import asyncio
    client, provider, sessions, *_ = handoff
    responses = await asyncio.gather(import_order(client), import_order(client))
    assert all(response.status_code in {200, 409} for response in responses)
    replay = await import_order(client)
    assert replay.status_code == 200
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Order)) == 1
    assert provider.writes == 1


async def test_signed_invalid_user_id_is_unauthorized(handoff):
    client, provider, *_ = handoff
    from api.auth import create_access_token
    app.dependency_overrides.pop(get_current_user)
    token = create_access_token("not-a-user-uuid")
    response = await client.post("/api/orders/from-provider-confirmed", headers={"Authorization": "Bearer " + token},
                                 json={"purchase_order_id": "po-synthetic"})
    assert response.status_code == 401
    assert provider.writes == 0


async def test_confirmed_quantity_must_match_frozen_requirement(handoff):
    client, provider, *_ = handoff
    provider.order["metadata_json"]["confirmed_quote_snapshot"]["metadata_json"]["selected_option"]["quote"]["quantity"] = 999
    response = await import_order(client)
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "CONFIRMED_QUANTITY_MISMATCH"
    assert provider.writes == 0


async def test_canonical_english_preserves_non_english_source_language(handoff):
    client, provider, sessions, *_ = handoff
    from src.db.models import DynamicOrderFormVersion
    requirement = provider.order["metadata_json"]["confirmed_requirement_snapshot"]["case"]["requirement"]
    requirement["language"] = "zh"
    requirement["extra"] = {"canonical_english_text": "Please supply one hundred and twenty cotton shirts."}
    response = await import_order(client)
    assert response.status_code == 200, response.text
    async with sessions() as db:
        version = await db.get(DynamicOrderFormVersion, uuid.UUID(response.json()["locked_form_version_id"]))
        assert version.fields["language"] == "zh"
        assert version.fields["product_type"] == "cotton shirt"
        assert version.fields["extra"]["canonical_english_text"] == requirement["extra"]["canonical_english_text"]
    assert provider.writes == 1


async def test_provider_canonical_language_rejection_cannot_import(handoff):
    client, provider, sessions, *_ = handoff
    # The actual provider owns content validation. A source-language tag or
    # local fallback must not override its rejection. Real HTTP validation of
    # non-English content is separate from this mocked error-propagation test.
    provider.canonical_rejection = True
    response = await import_order(client)
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "PROVIDER_HTTP_422"
    assert provider.writes == 0
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Order)) == 0
