import test from 'node:test';
import assert from 'node:assert/strict';
import { orderResponse, productionResponse, qcResponse, eventsResponse, shipmentResponse } from '../.test-build/execution/contracts.js';
const id='00000000-0000-4000-8000-000000000001', other='00000000-0000-4000-8000-000000000002', valid='2026-10-11T00:00:00Z';
const order={id,project_id:other,status:'CONFIRMED',created_at:valid};
for (const invalid of ['2026-02-30T10:00:00Z','2026-04-31T10:00:00+08:00','2025-02-29T10:00:00Z','2026-10-11T24:00:00Z']) {
  test('impossible evidence timestamp is rejected across API records: '+invalid,()=>{
    assert.equal(orderResponse({...order,buyer_signed_off_at:invalid},id),false,'invalid sign-off cannot be accepted');
    assert.equal(productionResponse({milestones:[{id,milestone_type:'SEWING',status:'DELAYED',actual_date:invalid}]}),false);
    assert.equal(qcResponse([{id,order_id:id,result:'FAIL',rework_required:true,created_at:valid,inspected_at:invalid}],id),false);
    assert.equal(eventsResponse([{id,order_id:id,tenant_id:other,event_type:'QC_FAILED',payload:{},occurred_at:invalid}],id),false);
    assert.equal(shipmentResponse({id,order_id:id,created_at:valid,tracking_events:[{id:other,event_type:'DELIVERED',occurred_at:invalid}]},id,id),false);
  });
}
test('valid leap days and explicit timezone offsets remain accepted without altering evidence',()=>{
  for(const time of ['2024-02-29T23:59:59.123456Z','2026-10-11T00:30:00+08:00','2026-10-10T16:30:00Z','2026-10-11T00:30:00-07:00','2026-10-11T00:30:00']) {
    const value={...order,buyer_signed_off_at:time};
    assert.equal(orderResponse(value,id),true,time);
    assert.equal(value.buyer_signed_off_at,time,'validator must preserve the returned timestamp');
  }
});
