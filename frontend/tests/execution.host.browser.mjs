import assert from 'node:assert/strict';
import {readFileSync, mkdirSync, writeFileSync} from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const fixtures=JSON.parse(readFileSync('../fixture-input.json','utf8'));
const browser=await chromium.launch({headless:true});
const page=await browser.newPage();
const requests=[];
await page.context().tracing.start({screenshots:true,snapshots:true});
await page.route('**/api/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname;
  assert.equal(request.method(),'GET');assert.equal(request.headers()['x-test-session'],'SYNTHETIC-HOST');
  requests.push(path);assert.ok(fixtures[path],'Only documented fixture paths are requested');
  await route.fulfill({contentType:'application/json',body:JSON.stringify(fixtures[path])});
});
try {
  await page.goto(new URL('execution-host.html',process.env.EXECUTION_PREVIEW_URL).href);
  await page.getByText('Signed out. No execution records are retained.',{exact:true}).waitFor();
  assert.equal(requests.length,0,'Unconnected host must not read business records');
  await page.evaluate(()=>window.executionHost.update({sessionKey:'synthetic-session',orderId:'00000000-0000-4000-8000-000000000001',request:(path,options)=>fetch(path,{...options,headers:{'X-Test-Session':'SYNTHETIC-HOST'}})}));
  await page.getByRole('heading',{name:'UNKNOWN_FUTURE_EVENT',exact:true}).waitFor();
  await page.evaluate(()=>{
    window.pendingSignals=[];
    window.executionHost.update({sessionKey:'pending-session',orderId:'00000000-0000-4000-8000-000000000001',request:(path,options)=>{window.pendingSignals.push(options.signal);return new Promise(resolve=>window.releasePending=()=>resolve(new Response(JSON.stringify({id:'00000000-0000-4000-8000-000000000001',order_number:'STALE-HOST'}))));}});
  });
  await page.waitForFunction(()=>window.pendingSignals.length>0);
  assert.equal(await page.evaluate(()=>{window.executionHost.logout();return document.getElementById('root').textContent;}),'Signed out. No execution records are retained.','Logout clears records synchronously');
  assert.equal(await page.evaluate(()=>window.pendingSignals.every(signal=>signal.aborted)),true);
  await page.evaluate(()=>window.releasePending());
  await page.evaluate(()=>window.executionHost.update({sessionKey:'renewed-session',orderId:'00000000-0000-4000-8000-000000000001',request:(path,options)=>fetch(path,{...options,headers:{'X-Test-Session':'SYNTHETIC-HOST'}})}));
  await page.getByRole('heading',{name:'UNKNOWN_FUTURE_EVENT',exact:true}).waitFor();
  assert.equal(await page.getByText('STALE-HOST',{exact:true}).count(),0);
  await page.evaluate(()=>window.executionHost.update({sessionKey:'renewed-session',orderId:'00000000-0000-4000-8000-000000000001',request:(_,options)=>{window.replacedSignal=options.signal;return new Promise(resolve=>window.releaseReplaced=()=>resolve(new Response(JSON.stringify({id:'00000000-0000-4000-8000-000000000001',order_number:'STALE-TRANSPORT'}))));}}));
  await page.waitForFunction(()=>!!window.replacedSignal);
  await page.evaluate(()=>window.executionHost.update({sessionKey:'renewed-session',orderId:'00000000-0000-4000-8000-000000000001',request:(path,options)=>fetch(path,{...options,headers:{'X-Test-Session':'SYNTHETIC-HOST'}})}));
  assert.equal(await page.evaluate(()=>window.replacedSignal.aborted),true,'Replacing transport with unchanged session identity cancels old reads');
  await page.evaluate(()=>window.releaseReplaced());
  await page.getByRole('heading',{name:'UNKNOWN_FUTURE_EVENT',exact:true}).waitFor();
  assert.equal(await page.getByText('STALE-TRANSPORT',{exact:true}).count(),0);
  for(const status of [401,403]) {
    await page.evaluate(status=>window.executionHost.update({sessionKey:'denied-session',orderId:'00000000-0000-4000-8000-000000000001',request:()=>Promise.resolve(new Response('PRIVATE-ERROR-BODY',{status}))}),status);
    await page.getByRole('alert').waitFor();
    assert.match(await page.getByRole('alert').textContent(),status===401?/Session expired/:/Access denied/);
    assert.equal(await page.getByRole('heading',{name:'Fulfillment history',exact:true}).count(),0);
    assert.equal(await page.getByText('PRIVATE-ERROR-BODY',{exact:true}).count(),0);
  }
  await page.evaluate(()=>window.executionHost.update({sessionKey:'same-session-new-transport',orderId:null,request:()=>{throw Error('No order selected');}}));
  await page.getByText('Select a confirmed order in the host application.',{exact:true}).waitFor();
  await page.evaluate(()=>window.executionHost.unmount());
  assert.equal(await page.locator('#root').textContent(),'');
  mkdirSync('evidence',{recursive:true});
  writeFileSync('evidence/host-verification.json',JSON.stringify({kind:'synthetic host HTTP integration; not real backend acceptance',requests,checks:['initially signed out','GET with host headers','selected order loads','synchronous logout clears records','pending request cancelled','old response ignored','renewed session loads','same-session transport replacement','401/403 without private error bodies','empty selection','unmount']},null,2));
  console.log('PASS: isolated host lifecycle, authenticated request forwarding, and GET-only fixture HTTP paths');
} finally {await page.context().tracing.stop({path:'evidence/host-trace.zip'});await browser.close();}
