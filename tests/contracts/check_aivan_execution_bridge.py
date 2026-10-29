"""New combination only: real JWT bridge/API/client, synthetic local ASGI DB."""
import asyncio, hashlib, importlib.util, json, os, sys
from pathlib import Path
import httpx
import pytest
from tests.api.test_provider_order_handoff import handoff
from tests.conftest import isolated_execution_language
from tests.api.test_execution_safety import started, inspection
from api.main import app
from api.deps import get_current_user
# Public source pin: GiraffeTechnology/aivan@7d3dc2f8844d276d3720f99ef66ebabcf17c93c4
AIVAN=Path(os.environ['ABCDYI_AIVAN_CONTRACT_SOURCE']).resolve()
PINNED_SOURCE_HASHES = {'installer/abcdyi_service.py': '3c45adba12dbb6dbdb2525329912f487992040eb256c618c038ef45672971272', 'src/aivan/integrations/execution_read.py': '0c75e23a16ee168aa1f2f07cd949b8d5e19ef03ac4e98a590b82d1f9afbc2047', 'src/aivan/api/request_context.py': '2598c03756fa1d29127e081b5aa13a07b10ed1603ab5562aca7d53d08f5c2fd7'}
for relative, digest in PINNED_SOURCE_HASHES.items():
    assert hashlib.sha256((AIVAN / relative).read_bytes()).hexdigest() == digest, relative
sys.path.insert(0,str(AIVAN/'src'))
import aivan
assert Path(aivan.__file__).resolve().is_relative_to(AIVAN / 'src'), 'Historical Aivan must not shadow pinned source'
from aivan.api.request_context import RequestContext
from aivan.integrations.execution_read import ExecutionReadClient, ExecutionReadError

async def test_real_installation_jwt_bridge_into_combined_execution_reads(handoff,monkeypatch):
    client,sessions,user,order,_ = await started(handoff)
    await inspection(client,order['id'],True)
    shipped=await client.post(f"/api/orders/{order['id']}/shipments",json={'carrier':'Synthetic'})
    assert shipped.status_code==201
    sid=shipped.json()['id']
    tenant=str(user.tenant_id)
    monkeypatch.setenv('MYAIVAN_FULFILLMENT_TENANTS',json.dumps({tenant:{'tenant_id':tenant,'operator_id':str(user.id)}}))
    monkeypatch.setenv('MYAIVAN_FULFILLMENT_API_KEYS',json.dumps({tenant:'synthetic-local-only-key-00000000000'}))
    monkeypatch.setenv('MYAIVAN_EXECUTION_WEB_ACTOR_ID','installation-operator')
    monkeypatch.setenv('AIVAN_UI_ACTOR_ID','installation-operator')
    monkeypatch.setenv('MYAIVAN_EXECUTION_BASE_URL','http://127.0.0.1:18081')
    spec=importlib.util.spec_from_file_location('combined_installer_bridge',AIVAN/'installer/abcdyi_service.py')
    bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
    monkeypatch.setattr(bridge,'load_source',lambda:Path.cwd())
    original_routes=list(app.router.routes)
    from api.auth import settings as auth_settings
    monkeypatch.setattr(auth_settings, 'SECRET_KEY', 'synthetic-jwt-signing-key-only-for-local-test-0000')
    bridge.application()
    app.dependency_overrides.pop(get_current_user)
    context=RequestContext(**{k:'' for k in RequestContext.__dataclass_fields__}|dict(tenant_id=tenant,actor_id='installation-operator',role_context='admin',authorization_basis='ui_session',production=False))
    association=dict(schema_version='aivan.execution-association.v1',status='associated',readback_verified=True,local_order_id=order['id'],local_project_id=order['project_id'])
    loop=asyncio.get_running_loop(); calls=[]
    async def forward(request):
        response=await client.request(request.method,request.url.path,headers=dict(request.headers),content=request.content)
        return httpx.Response(response.status_code,headers=response.headers,content=response.content)
    def transport(request):
        calls.append((request.method,request.url.path))
        return asyncio.run_coroutine_threadsafe(forward(request),loop).result(timeout=20)
    reader=ExecutionReadClient(context,transport=httpx.MockTransport(transport))
    before=handoff[1].writes
    try:
        for resource in ['order','production','qc','events','shipment']:
            response=await asyncio.to_thread(reader.read,association,resource,shipment_id=sid)
            assert response.status_code==200
        assert handoff[1].writes==before
        assert all(method=='GET' or (method=='POST' and path=='/api/installation/session') for method,path in calls)
        assert (await client.get(f"/api/orders/{order['id']}",headers={'Authorization':'Bearer invalid'})).status_code==401
        bad=dict(association,local_project_id='00000000-0000-0000-0000-000000000001')
        with pytest.raises(ExecutionReadError,match='EXECUTION_RESPONSE_IDENTITY_MISMATCH'):
            await asyncio.to_thread(reader.read,bad,'order')
    finally:
        app.router.routes[:]=original_routes
