"""Combined #36 backend / #39-40 R6 boundary: synthetic SQLite/ASGI only."""
import json
import subprocess
from pathlib import Path
from tests.api.test_provider_order_handoff import handoff
from tests.api.test_execution_safety import started, inspection

async def test_current_backend_reads_match_pinned_r6_contract_without_provider_writes(handoff):
    client, sessions, user, order, milestone = await started(handoff)
    await inspection(client, order['id'], True)
    shipment = await client.post(f"/api/orders/{order['id']}/shipments", json={'carrier': 'Synthetic carrier'})
    assert shipment.status_code == 201, shipment.text
    sid = shipment.json()['id']
    paths = {'order': f"/api/orders/{order['id']}", 'production': f"/api/orders/{order['id']}/production-monitoring", 'qc': f"/api/orders/{order['id']}/qc-records", 'events': f"/api/execution-graph/orders/{order['id']}", 'shipment': f"/api/shipments/{sid}"}
    before = handoff[1].writes
    payload = {'orderId': order['id'], 'shipmentId': sid}
    for key, path in paths.items():
        response = await client.get(path)
        assert response.status_code == 200, (key, response.text)
        payload[key] = response.json()
    assert handoff[1].writes == before, 'Reads must not mutate provider state'
    script = '''import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as c from './frontend/.test-build/execution/contracts.js';
const p=JSON.parse(fs.readFileSync(0,'utf8'));
assert.equal(c.orderResponse(p.order,p.orderId),true,'order');
assert.equal(c.productionResponse(p.production),true,'production');
assert.equal(c.qcResponse(p.qc,p.orderId),true,'qc');
assert.equal(c.eventsResponse(p.events,p.orderId),true,'events');
assert.equal(c.shipmentResponse(p.shipment,p.orderId,p.shipmentId),true,'shipment');
const wrong='00000000-0000-0000-0000-000000000001';
assert.equal(c.orderResponse(p.order,wrong),false,'wrong order');
assert.equal(c.qcResponse(p.qc,wrong),false,'wrong qc order');
assert.equal(c.eventsResponse(p.events,wrong),false,'wrong event order');
assert.equal(c.shipmentResponse(p.shipment,wrong,p.shipmentId),false,'wrong shipment order');
'''
    result = subprocess.run(['node', '--input-type=module', '-e', script], input=json.dumps(payload), text=True, capture_output=True, cwd=Path(__file__).resolve().parents[2])
    assert result.returncode == 0, result.stderr
