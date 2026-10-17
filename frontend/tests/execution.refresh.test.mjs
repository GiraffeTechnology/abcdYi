import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { create, act } from 'react-test-renderer';
import { ExecutionWorkspace } from '../.test-build/component/ExecutionWorkspace.mjs';
globalThis.IS_REACT_ACT_ENVIRONMENT=true;
const id='00000000-0000-4000-8000-000000000001', project='00000000-0000-4000-8000-000000000002', ship='00000000-0000-4000-8000-000000000003', time='2026-10-15T00:00:00Z';
const order=()=>({id,project_id:project,status:'CONFIRMED',created_at:time});
const production=(status)=>({milestones:[{id:project,milestone_type:'SEWING',status,actual_date:status==='COMPLETED'?time:null}],monitoring_packet:null});
const event=(type)=>({id:project,order_id:id,tenant_id:project,event_type:type,payload:{source:'SYNTHETIC'},occurred_at:time});
const mount=(get,extra={})=>create(React.createElement(ExecutionWorkspace,{orderId:id,sessionKey:'SYNTHETIC-session',authenticated:true,get,...extra}),{unstable_isConcurrent:true});
const rendered=(view)=>JSON.stringify(view.toJSON());
const refresh=(view)=>view.root.findAllByType('button').find(b=>b.children.join('')==='Refresh from API').props.onClick();
test('global refresh rereads every visible resource with a fast cached host order',async()=>{
  let phase=0;const counts=new Map();
  const get=async(path,options)=>{
    assert.equal(options.method,'GET');counts.set(path,(counts.get(path)||0)+1);
    if(path==='/api/orders/'+id)return order();
    if(path.endsWith('/production-monitoring'))return production(phase?'COMPLETED':'PENDING');
    if(path.endsWith('/qc-records'))return phase?[{id:project,order_id:id,result:'FAIL',rework_required:true,created_at:time}]:[];
    if(path==='/api/execution-graph/orders/'+id)return phase?[event('QC_FAILED')]:[];
    if(path==='/api/shipments/'+ship)return {id:ship,order_id:id,created_at:time,tracking_events:phase?[{id:project,event_type:'DELIVERED',occurred_at:time,description:'SYNTHETIC shipment refreshed'}]:[]};
    throw new Error('Unexpected path '+path);
  };
  let view;try{
    await act(async()=>{view=mount(get,{shipmentId:ship});});assert.match(rendered(view),/PENDING/);
    phase=1;await act(async()=>refresh(view));
    for(const path of ['/api/orders/'+id,'/api/orders/'+id+'/production-monitoring','/api/orders/'+id+'/qc-records','/api/execution-graph/orders/'+id,'/api/shipments/'+ship])assert.equal(counts.get(path),2,'reread '+path);
    assert.match(rendered(view),/COMPLETED/);assert.match(rendered(view),/QC_FAILED/);assert.match(rendered(view),/SYNTHETIC shipment refreshed/);
    assert.match(rendered(view),/Carrier delivery does not constitute buyer acceptance/);
  }finally{if(view)await act(async()=>view.unmount());}
});
test('global refresh cancels old pending evidence and ignores its later completion',async()=>{
  let productionCalls=0,oldSignal,resolveOld;
  const get=async(path,options)=>{
    assert.equal(options.method,'GET');
    if(path==='/api/orders/'+id)return order();
    if(path.endsWith('/production-monitoring')){
      productionCalls++;if(productionCalls===1){oldSignal=options.signal;return new Promise(resolve=>{resolveOld=resolve;});}
      return production('COMPLETED');
    }
    if(path.endsWith('/qc-records')||path==='/api/execution-graph/orders/'+id)return [];
    throw new Error('Unexpected path '+path);
  };
  let view;try{
    await act(async()=>{view=mount(get);});assert.ok(oldSignal);
    await act(async()=>refresh(view));assert.equal(oldSignal.aborted,true,'old HTTP lifetime must be cancelled');assert.equal(productionCalls,2);
    await act(async()=>resolveOld({milestones:[{id:project,milestone_type:'SYNTHETIC_STALE',status:'PENDING'}],monitoring_packet:null}));
    assert.match(rendered(view),/COMPLETED/);assert.doesNotMatch(rendered(view),/SYNTHETIC_STALE/);
  }finally{if(view)await act(async()=>view.unmount());}
});
test('global refresh retains an available event filter and clears it when that type disappears',async()=>{
  let phase=0;
  const get=async(path,options)=>{
    assert.equal(options.method,'GET');
    if(path==='/api/orders/'+id)return order();
    if(path.endsWith('/production-monitoring'))return {milestones:[],monitoring_packet:null};
    if(path.endsWith('/qc-records'))return [];
    if(path==='/api/execution-graph/orders/'+id)return [event(phase===2?'SHIPMENT_UPDATED':'QC_FAILED')];
    throw new Error('Unexpected path '+path);
  };
  let view;try{
    await act(async()=>{view=mount(get);});
    await act(async()=>view.root.findByType('select').props.onChange({target:{value:'QC_FAILED'}}));
    phase=1;await act(async()=>refresh(view));assert.equal(view.root.findByType('select').props.value,'QC_FAILED');
    phase=2;await act(async()=>refresh(view));assert.equal(view.root.findByType('select').props.value,'');assert.match(rendered(view),/SHIPMENT_UPDATED/);
  }finally{if(view)await act(async()=>view.unmount());}
});
