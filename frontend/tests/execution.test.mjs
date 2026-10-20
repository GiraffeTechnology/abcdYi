import test from 'node:test';
import assert from 'node:assert/strict';
import { ExecutionStore, shipmentIds, display } from '../.test-build/execution/store.js';
test('only GET with cancellation, exact references and unknown fields preserved', async () => {
  let state;
  const s = new ExecutionStore(async (path, opts) => { assert.equal(path, '/api/orders/o'); assert.equal(opts.method, 'GET'); assert.ok(opts.signal instanceof AbortSignal); return {id:'o', status:'FUTURE_STATUS'}; }, v => state=v);
  await s.read('order','/api/orders/o',v=>v.id==='o');
  assert.equal(state.resources.order.data.status,'FUTURE_STATUS');
  assert.deepEqual(shipmentIds([{payload:{shipment_id:'s'}},{payload:{shipment_id:'s'}},{payload:{other:'no'}}]),['s']);
  assert.equal(display(null),'Not supplied');
});
test('dispose prevents late response and aborts pending request', async () => {
  let resolve, signal, publications=0;
  const s=new ExecutionStore((_,o)=>{ signal=o.signal; return new Promise(r=>resolve=r); },()=>publications++);
  const p=s.read('order','/api/orders/old'); s.dispose(); assert.ok(signal.aborted); resolve({id:'old'}); await p; assert.equal(publications,1);
});
test('same resource retry ignores competing late success', async()=>{
  let old, state, calls=0;
  const s=new ExecutionStore(()=>++calls===1?new Promise(r=>old=r):Promise.resolve({id:'new'}),v=>state=v);
  const p=s.read('order','/api/orders/o'); await s.read('order','/api/orders/o'); old({id:'old'}); await p;
  assert.equal(state.resources.order.data.id,'new');
});
test('refresh cancels the superseded request while unrelated panels keep loading', async()=>{
  const pending=[], signals={}; let state;
  const s=new ExecutionStore((path,options)=>{signals[path]=options.signal;return new Promise(resolve=>pending.push({path,resolve}));},v=>state=v);
  const first=s.read('order','/old');const other=s.read('qc','/qc');const latest=s.read('order','/new');
  assert.equal(signals['/old'].aborted,true,'A repeated refresh must cancel its superseded request');
  assert.equal(signals['/qc'].aborted,false,'Independent panel requests must remain active');
  pending.find(p=>p.path==='/new').resolve({id:'new'});await latest;
  pending.find(p=>p.path==='/old').resolve({id:'old'});await first;
  pending.find(p=>p.path==='/qc').resolve([]);await other;
  assert.equal(state.resources.order.data.id,'new');s.dispose();
});
for(const status of [401,403]) test(`access ${status} clears all prior data without exposing error body`,async()=>{
  let fail=false,state;
  const s=new ExecutionStore(async()=>{if(fail)throw {status,message:'SECRET'};return {id:'o'};},v=>state=v);
  await s.read('order','/api/orders/o'); fail=true; await s.read('qc','/api/orders/o/qc-records');
  assert.deepEqual(state.resources,{}); assert.ok(state.access); assert.ok(!JSON.stringify(state).includes('SECRET'));
});
test('partial failure, timeout, retry and mismatched order are distinguishable',async()=>{
  let mode='ok',state;
  const s=new ExecutionStore(async()=>{if(mode==='timeout')return new Promise(()=>{});if(mode==='fail')throw Error('private');return {id:mode};},v=>state=v,5);
  await s.read('order','/api/orders/o'); mode='fail';await s.read('qc','/api/orders/o/qc-records');assert.ok(state.resources.order.data);assert.match(state.resources.qc.error,/Request failed/);
  mode='timeout';await s.read('qc','/api/orders/o/qc-records');assert.match(state.resources.qc.error,/timed out/);
  mode='wrong';await s.read('qc','/api/orders/o/qc-records',v=>v.id==='o');assert.match(state.resources.qc.error,/Response does not match/);
  mode='o';await s.read('qc','/api/orders/o/qc-records',v=>v.id==='o');assert.equal(state.resources.qc.data.id,'o');s.dispose();
});
test('strict-mode lifetime reset does not admit an old response',async()=>{
  let old,state,calls=0;
  const s=new ExecutionStore(()=>++calls===1?new Promise(r=>old=r):Promise.resolve({id:'current'}),v=>state=v);
  s.activate(); const p=s.read('order','/api/orders/o');s.dispose();s.activate();await s.read('order','/api/orders/o');old({id:'stale'});await p;assert.equal(state.resources.order.data.id,'current');s.dispose();
});
