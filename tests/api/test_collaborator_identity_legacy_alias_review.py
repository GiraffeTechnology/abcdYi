"""Persisted collaborator attribution and legacy storage identity regressions."""
import uuid
import pytest
from sqlalchemy import select
from api.main import app
from api.deps import get_current_user
from src.db.models import Participant, Project, QCRecord, ProductionUpdate
from tests.api.test_provider_order_handoff import handoff, import_order
from tests.api.test_project_membership import collaborator

@pytest.mark.parametrize('role,field,suffix', [
    ('QC_INSPECTOR','inspector_participant_id','qc-records'),
    ('MANUFACTURER','submitted_by_participant_id','production-updates'),
])
async def test_external_submission_identity_is_bound_to_grant(handoff,role,field,suffix):
    client,provider,sessions,owner,_=handoff
    order=(await import_order(client)).json();user,pid=await collaborator(sessions,owner)
    other=uuid.uuid4()
    async with sessions() as db:
        db.add(Participant(id=other,tenant_id=owner.tenant_id,name='Other supplier'));await db.commit()
    grant=await client.post(f"/api/projects/{order['project_id']}/memberships",json={'user_id':str(user.id),'role':role,'participant_id':str(pid)})
    assert grant.status_code==200,grant.text
    if role=='QC_INSPECTOR':
        assert (await client.post(f"/api/orders/{order['id']}/request-qc")).status_code==200
    app.dependency_overrides[get_current_user]=lambda:user
    body={'label_compliance':True} if role=='QC_INSPECTOR' else {'update_text':'Production has started.'}
    before=provider.writes
    bad=await client.post(f"/api/orders/{order['id']}/{suffix}",json={**body,field:str(other)})
    assert bad.status_code==403,bad.text
    assert provider.writes==before
    good=await client.post(f"/api/orders/{order['id']}/{suffix}",json={**body,field:str(pid)})
    assert good.status_code==201,good.text
    async with sessions() as db:
        model=QCRecord if role=='QC_INSPECTOR' else ProductionUpdate
        rows=(await db.scalars(select(model).where(model.order_id==uuid.UUID(order['id'])))).all()
        assert len(rows)==1
        assert getattr(rows[0],field)==pid

@pytest.mark.parametrize('alias',['PROJ-API-QC-01','33333333-3333-4333-8333-333333333333'])
async def test_legacy_qc_resolves_alias_and_keeps_original_storage_key(handoff,monkeypatch,alias):
    client,provider,sessions,owner,_=handoff
    order=(await import_order(client)).json()
    user,_=await collaborator(sessions,owner)
    async with sessions() as db:
        project=await db.get(Project,uuid.UUID(order['project_id']));project.project_id=alias
        # For UUID-shaped aliases, an unrelated PK must not take precedence.
        if alias.startswith('333'):
            db.add(Project(id=uuid.UUID(alias),tenant_id=owner.tenant_id,title='Other',created_by=user.id))
        await db.commit()
    observed=[]
    monkeypatch.setattr('api.routes.qc.get_reference_images',lambda key,**kw: observed.append(key) or [])
    response=await client.get(f'/api/qc/{alias}/reference-images')
    assert response.status_code==200,response.text
    assert observed==[alias]
    user,_=await collaborator(sessions,owner)
    app.dependency_overrides[get_current_user]=lambda:user
    rejected=await client.get(f'/api/qc/{alias}/reference-images')
    assert rejected.status_code==404,rejected.text
    assert observed==[alias]


async def test_foreign_legacy_alias_cannot_fall_back_to_owned_primary_key(handoff,monkeypatch):
    from tests.api.test_execution_safety import other_user
    client,_,sessions,owner,_=handoff
    order=(await import_order(client)).json()
    foreign=await other_user(sessions)
    async with sessions() as db:
        db.add(Project(project_id=order['project_id'],tenant_id=foreign.tenant_id,
            title='Foreign alias',created_by=foreign.id))
        await db.commit()
    observed=[]
    monkeypatch.setattr('api.routes.qc.get_reference_images',lambda key,**kw: observed.append(key) or [])
    response=await client.get(f"/api/qc/{order['project_id']}/reference-images")
    assert response.status_code==404,response.text
    assert observed==[]
