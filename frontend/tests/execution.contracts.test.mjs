import test from 'node:test';
import assert from 'node:assert/strict';
import { orderResponse, productionResponse, qcResponse, eventsResponse, shipmentResponse, suppliedShipmentReferences } from '../.test-build/execution/contracts.js';
import { createExecutionReadTransport } from '../.test-build/execution/transport.js';
import { ExecutionStore } from '../.test-build/execution/store.js';
const id='00000000-0000-4000-8000-000000000001', other='00000000-0000-4000-8000-000000000002', time='2026-10-11T00:00:00Z';
const order={id,project_id:other,status:'CONFIRMED',created_at:time,confirmed_at:time,buyer_signed_off_at:null};
test('malformed sign-off and incorrect identity cannot become a valid order',()=>{
  assert.ok(orderResponse(order,id));
  for(const value of [{},true,12,'not-a-date']) assert.equal(orderResponse({...order,buyer_signed_off_at:value},id),false);
  assert.equal(orderResponse({...order,id:other},id),false);
  assert.ok(orderResponse({...order,status:'FUTURE_STATE',buyer_signed_off_at:time},id));
});
test('production preserves missing dates and returned predictions but rejects malformed rows',()=>{
  const milestone={id,milestone_type:'SEWING',status:'DELAYED',planned_date:null,predicted_date:time,actual_date:null};
  assert.ok(productionResponse({milestones:[milestone],monitoring_packet:null}));
  for(const item of [null,12,[],{...milestone,actual_date:{}},{...milestone,status:12}]) assert.equal(productionResponse({milestones:[item]}),false);
  assert.equal(productionResponse({milestones:[],monitoring_packet:'invented'}),false);
});
test('QC booleans and order associations are checked without discarding failures',()=>{
  const qc={id,order_id:id,result:'FAIL',rework_required:true,created_at:time};
  assert.ok(qcResponse([qc],id));assert.ok(qcResponse([],id));
  assert.equal(qcResponse([{...qc,rework_required:'false'}],id),false);
  assert.equal(qcResponse([{...qc,order_id:other}],id),false);
});
test('unknown execution events and original correction lineage are retained',()=>{
  const e={id,order_id:id,tenant_id:other,event_type:'FUTURE_EVENT',payload:{corrects_event_id:other},occurred_at:time};
  assert.ok(eventsResponse([e],id));assert.equal(eventsResponse([{...e,payload:[]}],id),false);
  assert.equal(eventsResponse([{...e,order_id:other}],id),false);
});
test('shipment reference extraction never requests an arbitrary URL or guessed identity',()=>{
  assert.deepEqual(suppliedShipmentReferences([{payload:{shipment_id:id}},{payload:{shipment_id:id}},{payload:{shipment_id:'https://example.invalid'}}],other),{ids:[other,id],invalidCount:1});
  const s={id,order_id:other,created_at:time,tracking_events:[{id:other,event_type:'DELIVERED',occurred_at:time}]};
  assert.ok(shipmentResponse(s,other,id));assert.equal(shipmentResponse(s,id,id),false);
  assert.equal(shipmentResponse({...s,actual_arrival_date:true},other,id),false);
});
test('response adapter forces GET, forwards cancellation and does not consume private error body',async()=>{
  const signal=new AbortController().signal;let reads=0;
  const get=createExecutionReadTransport(async(path,options)=>{assert.equal(path,'/api/orders/o');assert.equal(options.method,'GET');assert.equal(options.signal,signal);return {ok:false,status:403,json:()=>{reads++;},text:()=>{reads++;}};});
  await assert.rejects(get('/api/orders/o',{method:'GET',signal}),e=>e.status===403);assert.equal(reads,0);
  const success=createExecutionReadTransport(async()=>new Response(JSON.stringify(order),{status:200}));assert.deepEqual(await success('/api/orders/o',{method:'GET',signal}),order);
});
for(const status of [404,409,422,429,503]) test(`HTTP ${status} remains a distinguishable read failure`,async()=>{
  let state;const s=new ExecutionStore(createExecutionReadTransport(async()=>new Response('private body',{status})),v=>state=v);
  await s.read('order','/api/orders/o');assert.equal(state.resources.order.httpStatus,status);assert.ok(state.resources.order.error);assert.ok(!JSON.stringify(state).includes('private body'));s.dispose();
});
