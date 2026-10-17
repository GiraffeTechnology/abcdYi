import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const browser=await chromium.launch({headless:true});
const page=await browser.newPage();
await page.context().tracing.start({screenshots:true,snapshots:true});
const fixtures=JSON.parse(readFileSync('evidence/synthetic-api-fixtures.json','utf8'));
let replaceHistory=false;
const requests=[];
await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  assert.equal(route.request().method(),'GET');requests.push(path);
  let response=structuredClone(fixtures[path]);
  assert.notEqual(response,undefined,'Only known synthetic records are requested');
  if(replaceHistory&&path.includes('/execution-graph/'))response=[{...response[1],event_type:'REPLACEMENT_EVENT'}];
  await route.fulfill({contentType:'application/json',body:JSON.stringify(response)});
});
try {
  await page.goto(new URL('execution-preview.html',process.env.EXECUTION_PREVIEW_URL ?? 'http://127.0.0.1:5187/').href);
  await page.getByRole('heading',{name:'UNKNOWN_FUTURE_EVENT',exact:true}).waitFor();
  await page.getByRole('combobox').selectOption('UNKNOWN_FUTURE_EVENT');
  assert.equal(await page.locator('article').count(),1);
  replaceHistory=true;
  await page.getByRole('button',{name:'Refresh from API',exact:true}).click();
  await page.waitForFunction(()=>Array.from(document.querySelectorAll('select option')).some(o=>o.value==='REPLACEMENT_EVENT'));
  assert.equal(await page.getByRole('heading',{name:'REPLACEMENT_EVENT',exact:true}).count(),1,'A refreshed history must not be hidden by an obsolete filter');
  assert.equal(await page.getByRole('combobox').inputValue(),'','An unavailable filter resets to All events');
  assert.equal(await page.getByRole('heading',{name:'UNKNOWN_FUTURE_EVENT',exact:true}).count(),0);
  await page.evaluate(fixtures=>{
    const orderPath='/api/orders/00000000-0000-4000-8000-000000000001';
    window.executionPreviewTransport=(path,options)=>{
      if(options.method!=='GET')throw Error('Unexpected write');
      if(path===orderPath)return new Promise(resolve=>{window.resolvePreviousSession=()=>resolve({...fixtures[path],order_number:'STALE-SESSION'});});
      return Promise.resolve(structuredClone(fixtures[path]));
    };
  },fixtures);
  await page.getByRole('button',{name:'Refresh from API',exact:true}).click();
  await page.waitForFunction(()=>typeof window.resolvePreviousSession==='function');
  await page.evaluate(fixtures=>{
    window.executionPreviewTransport=(path,options)=>{
      if(options.method!=='GET')throw Error('Unexpected write');
      const data=structuredClone(fixtures[path]);
      if(path==='/api/orders/00000000-0000-4000-8000-000000000001')data.order_number='CURRENT-SESSION';
      if(path.includes('/execution-graph/'))data.reverse();
      return Promise.resolve(data);
    };
  },fixtures);
  await page.getByRole('button',{name:'Renew synthetic session',exact:true}).click();
  await page.getByText('CURRENT-SESSION',{exact:true}).waitFor();
  await page.evaluate(async()=>{window.resolvePreviousSession();await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));});
  assert.equal(await page.getByText('STALE-SESSION',{exact:true}).count(),0,'An old session response cannot replace the same order in a new session');
  assert.equal(await page.getByText('CURRENT-SESSION',{exact:true}).count(),1);
  await page.getByRole('heading',{name:'UNKNOWN_FUTURE_EVENT',exact:true}).waitFor();
  assert.deepEqual(await page.locator('article h3').allTextContents(),['LOGISTICS_HANDOVER_CREATED','UNKNOWN_FUTURE_EVENT'],'Unsorted API events render chronologically after session reset');
  assert.equal(await page.getByRole('combobox').inputValue(),'');
  await page.screenshot({path:'evidence/execution-lifecycle.png',fullPage:true});
  console.log(JSON.stringify({result:'PASS',scenarios:['obsolete event filter after API refresh','same-order session reset with controlled late response','chronological reversed event response'],requests:requests.length}));
} finally { await page.context().tracing.stop({path:'evidence/execution-lifecycle-trace.zip'});await browser.close(); }
