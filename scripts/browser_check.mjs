// Browser integration checks using an installed Chrome and its DevTools protocol.
import {spawn} from 'node:child_process';
import {mkdtemp, mkdir, writeFile, access} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const profile=await mkdtemp(path.join(tmpdir(),'finn-browser-'));
const artifacts=path.join(root,'artifacts');
await mkdir(artifacts,{recursive:true});
let staticDir=path.join(root,'dist');
try{await access(staticDir)}catch{staticDir=path.join(root,'finn-site/dist')}
const port=18765;
const debugPort=19225;
const server=spawn('python3',[path.join(root,'scripts/serve.py'),'--port',String(port)],{stdio:'ignore'});
const chrome=spawn('/opt/google/chrome/chrome',['--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--no-default-browser-check',`--user-data-dir=${profile}`,`--remote-debugging-port=${debugPort}`,'about:blank'],{stdio:'ignore'});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let socket;
const results=[];
try{
 let page;
 for(let i=0;i<60;i++){
  try{const pages=await(await fetch(`http://127.0.0.1:${debugPort}/json`)).json();page=pages.find(p=>p.type==='page');if(page)break}catch{}
  await sleep(200);
 }
 assert(page,'Chrome did not start');
 socket=new WebSocket(page.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject});
 let sequence=0;
 const pending=new Map();
 const exceptions=[];
 socket.onmessage=event=>{const m=JSON.parse(event.data);if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params);if(m.id){const p=pending.get(m.id);pending.delete(m.id);if(m.error)p.reject(Error(JSON.stringify(m.error)));else p.resolve(m.result)}};
 const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}))});
 const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value};
 const until=async expression=>{for(let i=0;i<60;i++){if(await evaluate(expression))return;await sleep(100)}throw Error('Timed out: '+expression)};
 const check=(condition,message)=>{assert(condition,message);results.push(message)};
 await call('Runtime.enable');await call('Page.enable');
 await call('Page.navigate',{url:`http://127.0.0.1:${port}/`});
 await until(`document.querySelector('h1')?.textContent==='Your attention, directed.'`);
 check(await evaluate(`document.querySelector('.notice').textContent.includes('Current snapshot') && document.querySelector('#window').value==='1'`),'Briefing defaults to the current 24-hour window');
 check(await evaluate(`document.querySelector('#exchange-feed').textContent.includes('Exchange feed reachable')`),'Reachable exchange feed displays its actual coverage');
 await evaluate(`document.querySelector('#toggle-replay').click()`);
 check(await evaluate(`document.querySelector('.notice').textContent.includes('Historical replay')`),'Historical replay is explicitly labelled');
 check(await evaluate(`document.querySelectorAll('.event').length===1`),'Historical replay shows the dated FY25 results event');
 await evaluate(`location.hash='research'`);await until(`document.querySelectorAll('.comparison').length===3`);
 check(await evaluate(`document.querySelector('.status.missed')?.textContent==='missed'`),'Latest guidance miss is visible');
 await evaluate(`document.querySelector('#comparison-filter').value='all';document.querySelector('#comparison-filter').dispatchEvent(new Event('change'))`);
 check(await evaluate(`document.querySelectorAll('.comparison').length===5`),'Earlier guidance revisions and pending FY27 outcome are accessible');
 await evaluate(`document.querySelector('[data-source="q3"]').click()`);
 check(await evaluate(`document.querySelector('dialog').open && document.querySelector('dialog a').href.endsWith('#page=7')`),'Evidence inspector links to the correct original PDF page');
 await evaluate(`document.querySelector('#close-evidence').click();document.querySelector('#ticker').value='UNSEEN';document.querySelector('#ticker-form').requestSubmit()`);
 check(await evaluate(`document.querySelector('.empty').textContent.includes('No verified research indexed for UNSEEN')`),'Unsupported ticker produces a coverage gap instead of invented research');
 check(await evaluate(`!!document.querySelector('#collect-company')`),'Local research mode offers on-demand source collection for an unindexed ticker');
 await evaluate(`document.querySelector('[data-ticker="HCLTECH"]').click()`);
 await until(`document.querySelectorAll('#retrieval-results .source-row').length>0`);
 check(await evaluate(`document.querySelector('#document-research').textContent.includes('HCL Technologies')`),'Non-Infosys company loads its independently collected primary documents');
 await evaluate(`document.querySelector('[data-result="0"]').click()`);
 check(await evaluate(`document.querySelector('dialog').open && document.querySelector('dialog a').href.includes('#page=') && document.querySelector('dialog').textContent.includes('Document SHA-256')`),'Retrieved evidence preserves the source page and document hash');
 await evaluate(`document.querySelector('#close-evidence').click();document.querySelector('#research-query').value='zzzzzzzz';document.querySelector('#research-query-form').requestSubmit()`);
 await until(`document.querySelector('#retrieval-results .empty')`);
 check(await evaluate(`document.querySelector('#retrieval-results').textContent.includes('No matching source passage')`),'A question with no matching evidence produces an explicit gap');
 await evaluate(`document.querySelector('#ticker').value='COFORGE';document.querySelector('#ticker-form').requestSubmit()`);
 await evaluate(`document.querySelector('[data-topic="growth guidance"]').click()`);
 await until(`document.querySelectorAll('#retrieval-results .source-row').length>0`);
 check(await evaluate(`document.querySelector('#document-research').textContent.includes('Coforge')`),'An extra ticker outside the original demo set uses the same retrieval flow');
 await evaluate(`location.hash='portfolio'`);await until(`document.querySelectorAll('tbody tr').length===18`);
 check(await evaluate(`document.querySelector('main').textContent.includes('18/18 price sources available')`),'All 18 fetched portfolio prices are displayed');
 await evaluate(`document.querySelector('#price-threshold').value='5';document.querySelector('#price-threshold').dispatchEvent(new Event('change'))`);
 check(await evaluate(`JSON.parse(localStorage.getItem('finn-thresholds')).price===5`),'Configurable price threshold persists on the device');
 await evaluate(`document.querySelector('#portfolio-search').value='INFY';document.querySelector('#portfolio-search').dispatchEvent(new Event('input'))`);
 check(await evaluate(`document.querySelectorAll('tbody tr').length===1`),'Portfolio filter narrows to the requested company');
 await evaluate(`location.hash='sources'`);await until(`document.querySelectorAll('.curated-library .card').length===6`);
 await evaluate(`document.querySelector('#source-search').value='FY27';document.querySelector('#source-search-form').requestSubmit()`);
 check(await evaluate(`document.querySelectorAll('.curated-library .card').length===1`),'Verified source-summary search returns the matching FY27 reference');
 await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await evaluate(`document.querySelector('#toast').style.display='none'`);
 await evaluate(`location.hash='research'`);await until(`document.querySelector('#ticker')`);
 await evaluate(`document.querySelector('#ticker').value='INFY';document.querySelector('#ticker-form').requestSubmit()`);
 await sleep(500);
 let screenshot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
 await writeFile(path.join(artifacts,'research-desktop.png'),Buffer.from(screenshot.data,'base64'));
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 for(const view of ['briefing','research','portfolio','sources']){
  await evaluate(`location.hash='${view}'`);await sleep(150);
  check(await evaluate(`document.documentElement.scrollWidth<=window.innerWidth`),`No page overflow at 390px: ${view}`);
 }
 await evaluate(`location.hash='research'`);await sleep(250);
 screenshot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
 await writeFile(path.join(artifacts,'research-mobile.png'),Buffer.from(screenshot.data,'base64'));
 check(exceptions.length===0,'No uncaught JavaScript exceptions during the user flows');
 await writeFile(path.join(artifacts,'browser-check.json'),JSON.stringify({passed:results.length,checks:results,exceptions},null,2)+'\n');
 console.log(JSON.stringify({passed:results.length,checks:results},null,2));
}finally{
 socket?.close();chrome.kill('SIGTERM');server.kill('SIGTERM');
}
