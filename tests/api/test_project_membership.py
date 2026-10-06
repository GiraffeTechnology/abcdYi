"""Same-tenant competitors do not inherit project or quote access."""
import uuid
from types import SimpleNamespace
from sqlalchemy import select
from api.main import app
from api.deps import get_current_user
from src.db.models import User, UserRole, Participant, ProjectMembership, Milestone
from tests.api.test_provider_order_handoff import handoff, import_order


async def collaborator(sessions, owner):
    uid=uuid.uuid4();pid=uuid.uuid4()
    async with sessions() as db:
        db.add(User(id=uid,tenant_id=owner.tenant_id,email=f'{uid}@example.invalid',hashed_password='not-a-credential'))
        db.add(Participant(id=pid,tenant_id=owner.tenant_id,name='Synthetic production supplier'))
        await db.flush();db.add(UserRole(user_id=uid,role_name='MANUFACTURER'));await db.commit()
    return SimpleNamespace(id=uid,tenant_id=owner.tenant_id,is_platform_admin=False),pid


async def test_unassigned_same_tenant_user_cannot_read_or_mutate_order(handoff):
    client,provider,sessions,owner,_=handoff
    order=(await import_order(client)).json();user,_=await collaborator(sessions,owner)
    app.dependency_overrides[get_current_user]=lambda:user
    for method,path in [('GET',f"/api/orders/{order['id']}"),('GET',f"/api/projects/{order['project_id']}"),('GET',f"/api/orders/{order['id']}/production-monitoring"),('POST',f"/api/orders/{order['id']}/request-qc"),('GET',f"/api/execution-graph/orders/{order['id']}")]:
        r=await client.request(method,path);assert r.status_code==404,r.text
    assert (await client.get('/api/projects')).json()==[]
    r=await import_order(client);assert r.status_code==403,r.text
    assert provider.revision==1


async def test_project_owner_can_scope_and_revoke_production_access(handoff):
    client,provider,sessions,owner,_=handoff
    order=(await import_order(client)).json();user,pid=await collaborator(sessions,owner)
    path=f"/api/projects/{order['project_id']}/memberships"
    r=await client.post(path,json={'user_id':str(user.id),'role':'MANUFACTURER','participant_id':str(pid)})
    assert r.status_code==200,r.text
    app.dependency_overrides[get_current_user]=lambda:user
    assert (await client.get(f"/api/orders/{order['id']}/production-monitoring")).status_code==200
    # Whole-project commercial data and immutable approval evidence are not a
    # manufacturer capability, even when it participates in this same project.
    for route in [f"/api/projects/{order['project_id']}/dynamic-forms/current",f"/api/execution-graph/orders/{order['id']}",f"/api/projects/{order['project_id']}"]:
        r=await client.get(route);assert r.status_code==404,r.text
    r=await client.post(path,json={'user_id':str(user.id),'role':'BUYER'});assert r.status_code in {403,404},r.text
    app.dependency_overrides[get_current_user]=lambda:owner
    r=await client.delete(path+'/'+str(user.id));assert r.status_code==200,r.text
    app.dependency_overrides[get_current_user]=lambda:user
    assert (await client.get(f"/api/orders/{order['id']}/production-monitoring")).status_code==404


async def test_header_role_cannot_replace_persisted_project_grant(handoff):
    client,_,sessions,owner,_=handoff
    order=(await import_order(client)).json();user,_=await collaborator(sessions,owner)
    app.dependency_overrides[get_current_user]=lambda:user
    response=await client.get(f"/api/orders/{order['id']}",headers={'X-Role':'BUYER','X-Project-Role':'admin','X-User-ID':str(owner.id)})
    assert response.status_code==404


async def test_same_actor_has_distinct_buyer_and_supplier_project_roles(handoff):
    client,_,sessions,owner,_=handoff
    order=(await import_order(client)).json();user,pid=await collaborator(sessions,owner)
    project=(await client.post('/api/projects',json={'title':'Synthetic upstream procurement project'})).json()
    async with sessions() as db:
        db.add(UserRole(user_id=user.id,role_name='BUYER'));await db.commit()
    for project_id,role,participant in [(order['project_id'],'MANUFACTURER',str(pid)),(project['id'],'BUYER',None)]:
        r=await client.post(f'/api/projects/{project_id}/memberships',json={'user_id':str(user.id),'role':role,'participant_id':participant})
        assert r.status_code==200,r.text
    app.dependency_overrides[get_current_user]=lambda:user
    assert (await client.get(f"/api/projects/{project['id']}")).status_code==200
    assert (await client.get(f"/api/orders/{order['id']}/production-monitoring")).status_code==200
    # A global buyer role cannot escalate this actor's manufacturer role on the
    # original buyer's project or reveal its competing commercial responses.
    assert (await client.get(f"/api/projects/{order['project_id']}/dynamic-forms/current")).status_code==404
    assert (await client.get(f"/api/projects/{order['project_id']}/timeline")).status_code==404
