import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const browser=await chromium.launch({headless:true});
const page=await browser.newPage();
await page.context().tracing.start({screenshots:true,snapshots:true});
const requests=[];let signed=false, mode='ok', pending=[];
const latestFixtures={};
const syntheticIds=new Map();
function wire(value,key='') {
  if(value===null)return null;
  if(Array.isArray(value))return value.map(v=>wire(v));
  if(typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,wire(v,k)]));
  if(typeof value==='string'&&(key==='id'||key.endsWith('_id'))&&!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) {
    if(!syntheticIds.has(value))syntheticIds.set(value,`00000000-0000-4000-8000-${String(100+syntheticIds.size).padStart(12,'0')}`);
    return syntheticIds.get(value);
  }
  return value;
}
await page.route('**/api/**',async route=>{
  const req=route.request();requests.push({url:req.url(),method:req.method()});assert.equal(req.method(),'GET');
  const path=new URL(req.url()).pathname;const id=(path.includes('00000000-0000-4000-8000-000000000002')||path.includes('00000000-0000-4000-8000-000000000012'))?'00000000-0000-4000-8000-000000000002':'00000000-0000-4000-8000-000000000001';
  assert.match(path,/^\/api\/(?:orders\/[0-9a-f-]{36}(?:\/(?:production-monitoring|qc-records))?|execution-graph\/orders\/[0-9a-f-]{36}|shipments\/[0-9a-f-]{36})$/i,'Only documented read endpoints may be requested');
  if(mode==='pending'&&path.endsWith('00000000-0000-4000-8000-000000000001')){pending.push(route);return;}
  if(mode==='401'||mode==='403'){await route.fulfill({status:Number(mode),body:'private server error'});return;}
  if(mode==='timeout'&&path.endsWith('qc-records')){pending.push(route);return;}
  if(mode==='empty'&&path!==`/api/orders/${id}`){await route.fulfill({contentType:'application/json',body:JSON.stringify(path.endsWith('production-monitoring')?{milestones:[],monitoring_packet:null}:[])});return;}
  if(mode==='qc-fail'&&path.endsWith('qc-records')){await route.fulfill({status:503,body:'private'});return;}
  let data;
  if(path.endsWith('production-monitoring'))data={milestones:[{id:'m',milestone_type:'SEWING',status:'DELAYED',planned_date:'2026-10-11T00:00:00Z',predicted_date:'2026-10-12T00:00:00Z',actual_date:null,notes:'Synthetic capacity delay'}],monitoring_packet:{id:'packet',delay_risk_level:'HIGH',recommended_action:'Human review',delayed_milestones:['m'],expedite_alert_required:true}};
  else if(path.endsWith('qc-records'))data=[{id:'qc-fail',order_id:id,result:'FAIL',rework_required:true,responsible_participant_id:null,inspected_at:null,created_at:'2026-10-11T01:00:00Z'},{id:'qc-reinspection',order_id:id,result:'PASS',rework_required:false,responsible_participant_id:null,inspected_at:'2026-10-11T02:00:00Z',created_at:'2026-10-11T02:00:00Z'}];
  else if(path.includes('execution-graph'))data=[{id:'event-1',order_id:id,tenant_id:'00000000-0000-4000-8000-000000000021',project_id:'00000000-0000-4000-8000-000000000020',participant_id:null,event_type:'LOGISTICS_HANDOVER_CREATED',occurred_at:'2026-10-11T03:00:00Z',triggered_by_user_id:'00000000-0000-4000-8000-000000000022',payload:{shipment_id:id.endsWith('2')?'00000000-0000-4000-8000-000000000012':'00000000-0000-4000-8000-000000000011',source_ref:'synthetic://receipt',version:1}},{id:'event-2',order_id:id,tenant_id:'00000000-0000-4000-8000-000000000021',project_id:'00000000-0000-4000-8000-000000000020',participant_id:null,event_type:'UNKNOWN_FUTURE_EVENT',occurred_at:'2026-10-11T04:00:00Z',triggered_by_user_id:null,payload:{corrects_event_id:'event-1',version:2,source_ref:'https://unvisited.invalid/evidence'}}];
  else if(path.includes('/shipments/'))data={id:path.split('/').pop(),order_id:id,carrier:'Synthetic carrier',tracking_number:'SYNTHETIC-TRACKING',trade_term:null,origin:null,destination:null,estimated_departure_date:null,estimated_arrival_date:null,actual_departure_date:null,actual_arrival_date:'2026-10-11T05:00:00Z',logistics_risk_flags:[],created_at:'2026-10-11T03:00:00Z',tracking_events:[{id:'tracking',event_type:'DELIVERED',location:null,description:'Synthetic delivery',occurred_at:'2026-10-11T05:00:00Z'}]};
  else data={id,project_id:'p',status:signed?'CLOSED':'CONFIRMED',order_number:id,approved_option_id:null,locked_form_version_id:null,buyer_participant_id:null,confirmed_at:'2026-10-11T00:00:00Z',buyer_signed_off_at:signed?'2026-10-11T06:00:00Z':null,created_at:'2026-10-11T00:00:00Z'};
  if(mode==='bad-signoff'&&path===`/api/orders/${id}`)data.buyer_signed_off_at=true;
  if(mode==='bad-production'&&path.endsWith('production-monitoring'))data.milestones=[null];
  if(mode==='bad-qc'&&path.endsWith('qc-records'))data[0].rework_required='false';
  if(mode==='wrong-shipment'&&path.includes('/shipments/'))data.order_id='00000000-0000-4000-8000-000000000002';
  if(mode==='invalid-reference'&&path.includes('execution-graph'))data[0].payload.shipment_id='https://unvisited.invalid/not-a-shipment-id';
  latestFixtures[path]=wire(data);
  // Preserve the deliberately malformed reference; UUID fixture normalization must not repair it.
  if(mode==='invalid-reference'&&path.includes('execution-graph'))latestFixtures[path][0].payload.shipment_id='https://unvisited.invalid/not-a-shipment-id';
  await route.fulfill({contentType:'application/json',body:JSON.stringify(latestFixtures[path])});
});
const url=process.env.EXECUTION_PREVIEW_URL ?? 'http://127.0.0.1:5179/execution-preview.html';
try{
  await page.goto(url);await page.getByRole('cell',{name:'FAIL',exact:true}).waitFor();await page.getByRole('cell',{name:'DELIVERED',exact:true}).waitFor();
  writeFileSync('evidence/synthetic-api-fixtures.json',JSON.stringify(latestFixtures,null,2)+'\n');
  assert.match(await page.locator('main').innerText(),/Buyer sign-off not recorded/);
  await page.getByRole('heading',{name:'UNKNOWN_FUTURE_EVENT',exact:true}).waitFor();
  await page.getByRole('combobox').selectOption('UNKNOWN_FUTURE_EVENT');assert.equal(await page.locator('article').count(),1);await page.getByRole('combobox').selectOption('');assert.equal(await page.locator('article').count(),2);
  await page.locator('article details summary').last().click();assert.match(await page.locator('article').last().innerText(),/corrects_event_id/);
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:'evidence/execution-narrow.png',fullPage:true});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  await page.setViewportSize({width:1280,height:900});await page.screenshot({path:'evidence/execution-wide.png',fullPage:true});
  await page.getByRole('button',{name:'Refresh from API'}).focus();await page.keyboard.press('Tab');assert.ok(await page.evaluate(()=>document.activeElement!==document.body));
  await page.evaluate(fixtures => {
    window.executionPreviewCalls=[];
    window.executionPreviewTransport=(path,options)=>{
      if(options.method!=='GET')throw Error('Unexpected write');
      window.executionPreviewCalls.push(path);
      return Promise.resolve(structuredClone(fixtures[path]));
    };
  },latestFixtures);
  await page.getByRole('button',{name:'Refresh from API'}).click();
  await page.waitForFunction(()=>['/production-monitoring','/qc-records','/execution-graph/','/shipments/'].every(part=>window.executionPreviewCalls.some(path=>path.includes(part))),{},{timeout:3000});
  await page.evaluate(()=>{delete window.executionPreviewTransport;});
  signed=true;await page.getByRole('button',{name:'Refresh from API'}).click();await page.getByText('Buyer sign-off recorded by API.',{exact:true}).waitFor();
  const before=requests.length;await page.reload();await page.getByRole('cell',{name:'FAIL',exact:true}).waitFor();assert.ok(requests.length>before);
  mode='qc-fail';await page.reload();await page.getByRole('button',{name:'Retry qc history'}).waitFor();await page.getByRole('cell',{name:'DELAYED',exact:true}).waitFor();mode='ok';await page.getByRole('button',{name:'Retry qc history'}).click();await page.getByRole('cell',{name:'FAIL',exact:true}).waitFor();
  mode='bad-signoff';await page.reload();await page.getByText('Response does not match this order or the expected API shape.',{exact:true}).waitFor();assert.equal(await page.locator('table').count(),0);assert.equal(await page.getByText('Buyer sign-off recorded by API.',{exact:true}).count(),0);
  mode='bad-production';await page.reload();await page.getByRole('button',{name:'Retry production',exact:true}).waitFor();await page.getByRole('cell',{name:'FAIL',exact:true}).waitFor();
  mode='bad-qc';await page.reload();await page.getByRole('button',{name:'Retry qc history',exact:true}).waitFor();assert.equal(await page.getByRole('cell',{name:'FAIL',exact:true}).count(),0);
  mode='wrong-shipment';await page.reload();await page.getByRole('button',{name:'Retry shipment',exact:false}).waitFor();assert.equal(await page.getByRole('cell',{name:'DELIVERED',exact:true}).count(),0);
  mode='invalid-reference';const shipmentBefore=requests.filter(r=>r.url.includes('/shipments/')).length;await page.reload();await page.getByText('Some supplied shipment references do not match the API UUID format. No request is made for those references.',{exact:true}).waitFor();assert.equal(requests.filter(r=>r.url.includes('/shipments/')).length,shipmentBefore);
  mode='empty';await page.reload();await page.getByText('No shipment reference returned. No shipment scan or unverified order-list request is performed.',{exact:true}).waitFor();assert.equal(await page.locator('table').count(),0);
  mode='timeout';await page.reload();await page.getByText('Request timed out.',{exact:true}).waitFor();mode='ok';await page.getByRole('button',{name:'Retry qc history'}).click();await page.getByRole('cell',{name:'FAIL',exact:true}).waitFor();for(const r of pending.splice(0))await r.abort().catch(()=>{});
  for(const status of ['401','403']){mode=status;await page.reload();await page.getByRole('alert').waitFor();assert.equal(await page.locator('table').count(),0);assert.ok(!(await page.locator('body').innerText()).includes('private server error'));}
  mode='pending';await page.reload();await page.getByRole('button',{name:'Select order B'}).click();await page.locator('dd').filter({hasText:'00000000-0000-4000-8000-000000000002'}).waitFor();for(const r of pending.splice(0))await r.fulfill({contentType:'application/json',body:JSON.stringify({id:'00000000-0000-4000-8000-000000000001',status:'STALE-SECRET'})}).catch(()=>{});assert.ok(!(await page.locator('body').innerText()).includes('STALE-SECRET'));
  await page.getByRole('button',{name:'Select order A'}).click();await page.getByRole('button',{name:'Sign out',exact:true}).click();for(const r of pending.splice(0))await r.fulfill({contentType:'application/json',body:JSON.stringify({id:'00000000-0000-4000-8000-000000000001',status:'STALE-SECRET'})}).catch(()=>{});await page.getByText('Signed out. No execution records are retained.',{exact:true}).waitFor();assert.equal(await page.locator('table').count(),0);
  console.log(JSON.stringify({result:'PASS',scenarios:['GET-only','QC failure/reinspection','delivery versus sign-off','unknown event and correction','filter','390/1280 layout','keyboard','refresh/remount','fast-response full refresh','malformed sign-off/production/QC','wrong-order shipment','invalid shipment reference without request','partial failure/retry','empty records','15-second timeout/retry','401/403','late order switch','logout pending'],requests:requests.length}));
}catch(error){console.error(await page.locator('body').innerText());await page.screenshot({path:'evidence/execution-error.png',fullPage:true});throw error;}finally{await page.context().tracing.stop({path:'evidence/execution-trace.zip'});await browser.close();}
