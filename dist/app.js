import {searchCorpus} from './retrieval.mjs';
import {prepareFilings} from './filings.mjs';
let data;
const $ = s => document.querySelector(s);
const escape = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dateLabel = d => d ? new Date(d + 'T12:00:00Z').toLocaleDateString('en-IN', {day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}) : 'Publication date not established';
const percent = n => `${n}%`;
let selectedTicker = 'INFY';
let replay = false;
let endDate = '2025-04-17';
let days = 1;
let filingCategory = 'all';
let comparisonFilter = 'latest';
let search = '';
let sourceQuery = '';
let researchQuery = 'growth guidance';
const corpusCache = new Map();
let retrievalResults = [];
let retrievalVersion = 0;
let canCollect = false;
let settings = {price:3,volume:2};
try { settings = {...settings,...JSON.parse(localStorage.getItem('finn-thresholds') || '{}')}; } catch {}
if (!(settings.price >= 1 && settings.price <= 10)) settings.price = 3;
if (!(settings.volume >= 1 && settings.volume <= 5)) settings.volume = 2;
const source = id => data.companies.INFY.sources.find(s => s.id === id);
const sourceButton = (id, label='View evidence ↗') => `<button class="text-button" data-source="${escape(id)}">${label}</button>`;
const head = (eyebrow,title,intro,button='') => `<div class="page-head"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="intro">${intro}</p></div>${button}</div>`;
const note = `<div class="notice"><span><strong>Verified case study.</strong> Figures were manually checked against company documents. Comparison verdicts are calculated in code. AI extraction is not connected.</span><a href="#sources">Inspect sources ↗</a></div>`;

function documentSearchMarkup(){
 const coverage=data.research_coverage?.[selectedTicker];
 const choices=Object.values(data.research_coverage||{}).filter(c=>c.document_count>0);
 return `<div class="controls" style="margin-bottom:18px">${choices.map(c=>`<button class="button secondary" data-ticker="${escape(c.ticker)}" ${c.ticker===selectedTicker?'aria-current="true"':''}>${escape(c.ticker)}</button>`).join('')}</div>`+(coverage?.document_count?`<section class="card" id="document-research"><div class="section-head" style="margin-top:0"><div><div class="eyebrow">PRIMARY-DOCUMENT SEARCH / ${escape(selectedTicker)}</div><h2 style="margin-top:10px">${escape(coverage.name)}</h2><p class="small-copy">${coverage.document_count} PDFs · ${coverage.transcripts} transcripts · ${coverage.annual_reports} annual reports · ${coverage.page_count} PDF pages</p></div><span class="badge">NO API KEY NEEDED</span></div><form class="search-form" id="research-query-form"><input type="search" id="research-query" placeholder="Ask the documents: growth guidance, margins, cash flow…" aria-label="Search primary documents" value="${escape(researchQuery)}" maxlength="250" required><button class="button">Find evidence →</button></form><div class="controls">${['growth guidance','operating margin','cash flow','debt working capital','risk'].map(q=>`<button class="text-button" data-topic="${q}">${q}</button>`).join('')}</div><p class="small-copy">Keyword-ranked source passages, not an AI-written answer. A mention of guidance may be an analyst’s question or refer to a different period. Check the source before drawing a conclusion.</p><div id="retrieval-results" aria-live="polite"><p class="small-copy">Loading document index…</p></div>${coverage.rejected.length?`<details class="small-copy"><summary>${coverage.rejected.length} source candidates excluded</summary>${coverage.rejected.map(r=>`<p>${escape(r.kind.replaceAll('_',' '))} · ${escape(r.period)}: ${escape(r.reason)}</p>`).join('')}</details>`:''}</section>`:'');
}

async function loadCorpus(ticker){
 if(corpusCache.has(ticker))return corpusCache.get(ticker);
 const coverage=data.research_coverage?.[ticker];
 if(!coverage)throw Error('No corpus indexed');
 const response=await fetch(coverage.corpus_url);
 if(!response.ok)throw Error('Document index could not be loaded');
 const raw=await response.arrayBuffer();
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),b=>b.toString(16).padStart(2,'0')).join('');
 if(digest!==coverage.corpus_sha256)throw Error('Document index integrity check failed. Reload the latest snapshot.');
 const corpus=JSON.parse(new TextDecoder().decode(raw));
 corpusCache.set(ticker,corpus);return corpus;
}

async function runRetrieval(){
 const target=$('#retrieval-results');if(!target)return;
 const version=++retrievalVersion;
 const ticker=selectedTicker;
 target.innerHTML='<p class="small-copy">Searching primary-document passages…</p>';
 try{
  const corpus=await loadCorpus(ticker);
  if(version!==retrievalVersion||selectedTicker!==ticker||!target.isConnected)return;
  retrievalResults=searchCorpus(corpus,researchQuery);
  target.innerHTML=retrievalResults.length?`<div class="section-head"><h3>${retrievalResults.length} matching documents</h3><button class="text-button" id="export-search">Export evidence pack ↓</button></div>`+retrievalResults.map((r,i)=>`<article class="source-row"><div class="eyebrow">${escape(r.document.title)} · PDF PAGE ${r.page}</div><p class="source-excerpt">“${escape(r.snippet)}…”</p><div class="controls"><button class="text-button" data-result="${i}">Inspect evidence ↗</button><span class="small-copy">Matched: ${escape(r.matched.join(', '))}</span></div></article>`).join(''):'<div class="empty"><strong>No matching source passage found.</strong>This does not prove the company never discussed the topic. Try specific terms or inspect the original documents.</div>';
  target.querySelectorAll('[data-result]').forEach(button=>button.onclick=()=>retrievedEvidence(retrievalResults[Number(button.dataset.result)]));
  if($('#export-search'))$('#export-search').onclick=()=>{
   const pack={ticker,question:researchQuery,method:'Keyword retrieval; no generated financial conclusion',instruction:'Use only this evidence. Distinguish questions from management statements. Check reporting periods and accounting scope. If these short excerpts do not support an answer, say what is missing and inspect the linked primary PDFs.',sources:retrievalResults.map(r=>({title:r.document.title,url:r.document.url+'#page='+r.page,pdf_page:r.page,sha256:r.document.sha256,excerpt:r.snippet}))};
   const url=URL.createObjectURL(new Blob([JSON.stringify(pack,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='FINN-'+ticker+'-research-pack.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
 }catch(error){if(target.isConnected)target.innerHTML=`<div class="empty"><strong>Document search is unavailable.</strong>${escape(error.message)}</div>`}
}

function retrievedEvidence(result){
 const d=result.document;
 const url=new URL(d.url);if(url.protocol!=='https:')return;
 $('#evidence-content').innerHTML=`<div class="eyebrow">PRIMARY PDF / ${escape(selectedTicker)}</div><h2>${escape(d.title)}</h2><div class="eyebrow">PDF PAGE ${result.page} OF ${d.page_count}</div><p class="source-excerpt">“${escape(result.snippet)}…”</p><div class="evidence-note">Exact extracted text, shortened to 25 words. This retrieval result is not a verified financial claim. Table layout, speaker identity, reporting period, and accounting scope need checking in the original PDF.</div><a class="button" href="${escape(d.url)}#page=${result.page}" target="_blank" rel="noopener noreferrer">Open original · page ${result.page} ↗</a><p class="small-copy">Document SHA-256: <span style="overflow-wrap:anywhere">${escape(d.sha256)}</span></p><p class="small-copy">${escape(d.identity_check)}</p>`;
 $('#evidence').showModal();
}

async function collectCompany(){
 const ticker=selectedTicker;
 const button=$('#collect-company');
 const status=$('#collection-status');
 if(button)button.disabled=true;
 if(status)status.textContent='Finding company-issued reports and transcripts…';
 try{
  const response=await fetch('/api/collect',{method:'POST',headers:{'Content-Type':'application/json','X-FINN-Request':'local'},body:JSON.stringify({ticker})});
  const job=await response.json();
  if(!response.ok)throw Error(job.error||'Could not start source collection');
  for(let attempt=0;attempt<180;attempt++){
   await new Promise(resolve=>setTimeout(resolve,1000));
   const poll=await fetch('/api/jobs/'+job.job_id,{cache:'no-store'});
   if(!poll.ok)throw Error('Source-collection status unavailable');
   const state=await poll.json();
   if(state.status==='failed')throw Error(state.error||'No usable primary documents could be imported.');
   if(state.status==='complete'){
    const snapshot=await fetch('snapshot.json',{cache:'no-store'});
    if(!snapshot.ok)throw Error('Updated snapshot unavailable');
    data=await snapshot.json();corpusCache.delete(ticker);
    if(selectedTicker===ticker)render();
    toast(ticker+' primary documents indexed.');return;
   }
  }
  throw Error('Collection is still running. Reopen the company shortly to check its coverage.');
 }catch(error){if(status?.isConnected)status.textContent=error.message;if(button?.isConnected)button.disabled=false}
}

function exchangeFeed(start,end){
 const feed=data.announcements||{};
 const {inWindow,categories,routine,important}=prepareFilings(feed.records||[],start,end,filingCategory);
 const timestamp=value=>new Date(value).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZone:'Asia/Kolkata'})+' IST';
 const card=r=>`<article class="card event filing-event"><div class="meta"><div><span class="ticker">${escape(r.ticker)}</span><span class="tag">${escape(r.category.replaceAll('_',' '))}</span></div><span class="filing-time">${escape(timestamp(r.published_at))}</span></div><h3>${escape(r.subject)}</h3><p>${escape(r.details)}</p><div class="filing-details">Priority ${r.priority}/100 · ${escape(r.classification_method)}${r.related_count>1?' · '+r.related_count+' entries grouped by attachment':''}</div><a class="text-button" href="${escape(r.source_url)}" target="_blank" rel="noopener noreferrer">Open exchange disclosure ↗</a><button class="text-button" style="margin-left:15px" data-ticker="${escape(r.ticker)}">Research company →</button></article>`;
 return `<section id="exchange-feed"><div class="section-head"><div><h2>Portfolio filings</h2><div class="eyebrow">${inWindow.length} OBSERVED DISCLOSURES IN YOUR WINDOW</div></div><select id="filing-category" aria-label="Announcement category"><option value="all">All categories</option>${categories.map(c=>`<option value="${escape(c)}" ${filingCategory===c?'selected':''}>${escape(c.replaceAll('_',' '))}</option>`).join('')}</select></div><div class="notice ${feed.status==='ok'?'':'warn'}"><span><strong>${feed.status==='ok'?'Exchange feed reachable · '+escape(feed.provider||'NSE'):'Exchange refresh unavailable'}</strong><br>${feed.status==='ok'?'Rolling-feed span: '+escape(timestamp(feed.coverage_start))+' to '+escape(timestamp(feed.coverage_end))+'. Gaps between refreshes may be missing.':escape(feed.rss_error||feed.error||'No successful refresh recorded.')}</span></div>${important.length?important.map(card).join(''):'<div class="empty"><strong>No higher-priority portfolio filings observed in this window.</strong>This is a rolling source snapshot, not proof that no disclosures occurred.</div>'}${routine.length?`<details class="card" id="routine-filings"><summary>${routine.length} routine or investor-meeting entries · expand to inspect</summary><div style="margin-top:18px">${routine.map(card).join('')}</div></details>`:''}<p class="small-copy">Subjects and descriptions come from the exchange feed. Priority is assigned by inspectable keyword rules; it is not an AI assessment of financial impact. Unknown categories remain visible for review.</p></section>`;
}

function briefing(){
 const company = data.companies.INFY;
 const end = new Date(replay?endDate+'T23:59:59+05:30':data.built_at);
 const start = new Date(end.getTime()-days*86400000);
 const events = company.sources.filter(s=>s.kind==='transcript' && s.date && new Date(s.date+'T12:00:00Z')>=start && new Date(s.date+'T12:00:00Z')<=end);
 events.sort((a,b)=>b.date.localeCompare(a.date));
 const alerts=(data.market.records||[]).filter(r=>r.status==='ok').map(r=>({record:r,calc:marketRule(r)})).filter(r=>r.calc?.trigger);
 const marketSignals=`<div class="section-head"><div><h2>Market signals</h2><div class="eyebrow">EOD SNAPSHOT · SEPARATE FROM THE EVENT REPLAY</div></div><a class="text-button" href="#portfolio">Configure thresholds →</a></div><div class="library">${alerts.length?alerts.map(({record:r,calc:c})=>`<article class="card"><div class="eyebrow">${escape(r.ticker)} · ${dateLabel(r.session_date)}</div><h3>${Math.abs(c.change)>=settings.price?'Price threshold crossed':'Unusual volume'}</h3><div class="mini-metrics" style="width:100%"><div><b class="${c.change<0?'down':'up'}">${c.change>0?'+':''}${c.change.toFixed(2)}%</b><span>Close-to-close change</span></div><div><b>${c.volume.toFixed(2)}×</b><span>Prior 20-session volume</span></div></div><p>Triggered by your rules: ±${settings.price}% price or ${settings.volume}× volume. A threshold crossing does not explain its cause.</p><a href="#portfolio" class="text-button">Inspect portfolio →</a></article>`).join(''):'<div class="empty">No configured thresholds crossed in the available price snapshot.</div>'}</div>`;
 return head('A LITTLE LESS NOISE','Your attention, directed.','A focused view of what changed, what matters, and the evidence behind it.')+
 `<div class="notice ${replay?'warn':''}"><span><strong>${replay?'Historical replay · '+dateLabel(endDate):'Current snapshot · '+dateLabel(data.as_of)}</strong> · ${replay?'Real historical company disclosures; this is not a live exchange feed.':'Saved source snapshot. Exchange coverage and freshness are stated below.'}</span><button class="text-button" id="toggle-replay">${replay?'Use current date':'Open historical replay'} ↗</button></div>`+
 `<section class="hero" aria-label="Featured research"><div class="hero-copy"><div class="eyebrow">THE SIGNAL / INFOSYS / FY25</div><h2>Growth delivered.<br>The latest promise didn’t.</h2><p>FY25 revenue growth beat the earlier Q1 range, met the Q2 range, and fell below the final Q3 range. The reference point changes the conclusion.</p><a class="text-button" href="#research">Follow the promise →</a></div><div class="hero-figure"><div class="big-number">−0.3<small> pp</small></div><div class="figure-label">Below latest guidance’s lower bound<br>4.2% actual vs. 4.5–5% guided<br>Full-year constant-currency growth</div></div></section>`+
 `<div class="section-head"><div><h2>In your window</h2><div class="eyebrow">${replay?events.length+' CASE-STUDY EVENTS · INFY':(data.announcements.records||[]).length+' ARCHIVED PORTFOLIO DISCLOSURES'}</div></div><div class="controls"><select id="window" aria-label="Digest time window"><option value="1" ${days===1?'selected':''}>Last 24 hours</option><option value="7" ${days===7?'selected':''}>Last 7 days</option><option value="90" ${days===90?'selected':''}>Last 90 days</option><option value="365" ${days===365?'selected':''}>Last year</option></select>${replay?`<input type="date" id="end-date" aria-label="Replay end date" value="${endDate}" max="${data.as_of}">`:''}</div></div>`+
 (replay?`<div class="grid"><section>${events.length?events.map(s=>`<article class="card event"><div class="meta"><div><span class="ticker">INFY</span><span class="tag">${s.id==='q4'?'RESULTS':'GUIDANCE'}</span></div><span class="eyebrow">${dateLabel(s.date)}</span></div><h3>${s.id==='q4'?'FY25 growth below latest guidance; margin within range':s.id==='q2fy27'?'FY27 growth guidance: full-year outcome pending':'FY25 guidance revised · '+s.title.split(' ')[0]}</h3><p>${escape(s.summary)}</p>${s.id==='q4'?'<div class="mini-metrics"><div><b>4.2%</b><span>FY25 CC revenue growth</span></div><div><b>21.1%</b><span>FY25 operating margin</span></div></div>':''}${sourceButton(s.id)} · <a class="text-button" href="#research">Research →</a></article>`).join(''):'<div class="empty"><strong>No case-study disclosures in this window.</strong>Expand the window to inspect earlier guidance.</div>'}</section><aside><section class="card"><div class="eyebrow">THE NEXT QUESTION</div><h3 style="margin-top:12px">Did the forecast move, or did the business?</h3><p class="small-copy">Read each revision against the same final outcome. Earlier guidance stays visible; a later revision does not rewrite history.</p><a class="text-button" href="#research">Open guidance history →</a><hr class="divider"><div class="eyebrow">COVERAGE, HONESTLY</div><p class="small-copy">18 portfolio companies configured.<br>${Object.values(data.research_coverage||{}).filter(c=>c.document_count>0).length} companies with searchable primary PDFs.<br>5 curated guidance comparisons.</p></section></aside></div>`:exchangeFeed(start,end))+marketSignals;
}

function comparison(p){
 const status = p.assessment.status;
 const actual = status==='pending'||status==='insufficient_evidence' ? 'Pending' : percent(p.actual);
 const delta = status==='missed'?`${Math.abs(p.assessment.delta_pp).toFixed(2).replace(/0$/,'')} percentage points below the lower bound.`:p.assessment.reason;
 return `<article class="card comparison"><div class="comparison-top"><div><h3>${escape(p.label)}</h3><div class="eyebrow">${p.period} · ${p.basis.replaceAll('_',' ')} · ${p.scope}</div></div><span class="status ${status}">${status.replaceAll('_',' ')}</span></div><div class="compare-values"><div><small>MANAGEMENT GUIDED</small><span class="value">${p.low}–${p.high}%</span><small>${dateLabel(source(p.source).date)}</small></div><div class="arrow">→</div><div><small>FULL-YEAR OUTCOME</small><span class="value">${actual}</span><small>${p.outcome_date?dateLabel(p.outcome_date):'Year ends '+dateLabel(p.period_end)}</small></div></div><div class="comparison-bottom"><span>${escape(delta)}<br><span class="muted">${escape(p.revision)}</span></span><div>${sourceButton(p.source,'Guidance ↗')} ${p.outcome_source?sourceButton(p.outcome_source,'Outcome ↗'):''}</div></div></article>`;
}

function research(){
 const company = data.companies[selectedTicker];
 let markup = head('RESEARCH / PRIMARY SOURCES','Promises, meet results.','A company’s story is more useful when you can check what happened next.');
 markup += `<form class="search-form" id="ticker-form"><input id="ticker" type="text" aria-label="NSE ticker" placeholder="Enter an NSE ticker, e.g. INFY" value="${escape(selectedTicker)}" maxlength="40" required><button class="button">Open company →</button></form>`;
 if(!company) return markup+documentSearchMarkup()+(data.research_coverage?.[selectedTicker]?.document_count?'':`<div class="empty"><strong>No verified research indexed for ${escape(selectedTicker)} yet.</strong>${canCollect?'Find and index the company’s primary reports and transcripts. This can take a few minutes.':'Choose an indexed company above. New primary documents can be added through the reusable ticker pipeline; this hosted snapshot does not fetch a new company on demand.'}<br>${canCollect?'<button class="button" id="collect-company">Find company documents →</button><p id="collection-status" role="status"></p>':''}<button class="text-button" id="reset-ticker">Explore Infosys instead →</button></div>`);
 const promises = company.promises.filter(p=>comparisonFilter==='all'||p.id==='growth_q3'||p.id==='margin_q3'||p.id==='growth_fy27');
 return markup+documentSearchMarkup()+note+`<div class="section-head"><div><h2><span class="ticker">INFY</span> Infosys</h2><p class="small-copy">${escape(company.description)}</p></div><button class="button secondary" id="export">Export evidence ↓</button></div><div class="stats"><div class="stat"><div class="eyebrow">REVENUE GUIDANCE</div><b class="down">Missed</b><small>Latest FY25 range · 4.5–5%</small></div><div class="stat"><div class="eyebrow">MARGIN GUIDANCE</div><b class="up">Met</b><small>FY25 range · 20–22%</small></div><div class="stat"><div class="eyebrow">FY27 GROWTH</div><b>Pending</b><small>Full year ends March 2027</small></div></div><div class="grid"><section><div class="section-head"><h2>The delivery record</h2><select id="comparison-filter" aria-label="Guidance comparison filter"><option value="latest" ${comparisonFilter==='latest'?'selected':''}>Latest guidance</option><option value="all" ${comparisonFilter==='all'?'selected':''}>Include earlier revisions</option></select></div>${promises.map(comparison).join('')}<p class="small-copy">FY25 is a completed historical case, not the latest four-quarter research view. No investment recommendation or explanation of causality is inferred from these comparisons.</p></section><aside><section class="card"><div class="eyebrow">SAME YEAR / DIFFERENT EXPECTATIONS</div><h3 style="margin-top:12px">How the goalposts moved</h3><div class="timeline">${company.promises.filter(p=>p.metric==='revenue_growth'&&p.period==='FY2025').map(p=>`<div class="timeline-item"><small>${dateLabel(source(p.source).date)} · ${source(p.source).title.split(' ')[0]}</small><b>${p.low}–${p.high}%</b><p>${p.assessment.status==='exceeded'?'Final outcome above this range':p.assessment.status==='met'?'Final outcome within this range':'Final outcome below this range'}</p>${sourceButton(p.source,'Source ↗')}</div>`).join('')}<div class="timeline-item"><small>17 Apr 2025 · Full-year outcome</small><b>4.2%</b><p>Constant-currency revenue growth</p>${sourceButton('q4','Source ↗')}</div></div></section><section class="card" style="margin-top:18px"><div class="eyebrow">EVIDENCE DISCIPLINE</div><p class="small-copy">Same financial year. Same metric. Same currency basis. Consolidated scope. Annual guidance is compared with annual delivery.</p><p class="small-copy">The later annual report corroborates growth; it is not used to backdate the April event.</p>${sourceButton('ar25','Annual-report corroboration ↗')}</section></aside></div>`;
}

function marketRule(record){
 const rows = record.history;
 if(!rows||rows.length<21) return null;
 const average=rows.slice(-21,-1).reduce((a,r)=>a+r.volume,0)/20;
 const prior=rows.at(-2).close;
 if(!(average>0&&prior>0))return null;
 const change=(rows.at(-1).close/prior-1)*100;
 const volume=rows.at(-1).volume/average;
 return {change,volume,trigger:Math.abs(change)>=settings.price||volume>=settings.volume};
}

function portfolio(){
 const records=data.market.records||[];
 const ok=records.filter(r=>r.status==='ok');
 const sessionDates=[...new Set(ok.map(r=>r.session_date))].sort();
 const filtered=data.portfolio.filter(c=>(c.ticker+' '+c.sector).toLowerCase().includes(search.toLowerCase()));
 return head('PORTFOLIO / END OF DAY','Watch what matters.','Your mock portfolio and configurable unusual-move rules. Daily prices are snapshots, with their trading date shown.')+
 `<div class="notice ${ok.length?'':'warn'}"><span><strong>${ok.length}/18 price sources available.</strong> Latest returned session: ${sessionDates.length?dateLabel(sessionDates.at(-1)):'unavailable'}. ${data.market.refreshed_at?'Last refresh attempt: '+escape(new Date(data.market.refreshed_at).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'}))+' IST.':''} Availability does not guarantee freshness. This deployed view does not refresh automatically.</span><button class="text-button" id="reload">Reload saved snapshot ↻</button></div>`+
 `<section class="card"><div class="section-head" style="margin-top:0"><h2>What counts as unusual?</h2><span class="tag">SAVED ON THIS DEVICE</span></div><div class="settings"><label>Daily price move: <output id="price-output">±${settings.price}%</output><input type="range" id="price-threshold" min="1" max="10" step="0.5" value="${settings.price}" aria-label="Daily price move threshold"></label><label>Volume vs. prior 20-session average: <output id="volume-output">${settings.volume}×</output><input type="range" id="volume-threshold" min="1" max="5" step="0.25" value="${settings.volume}" aria-label="Volume multiple threshold"></label></div><p class="small-copy">The current session is excluded from the average. Alerts use completed sessions. Splits and other corporate actions can cause mechanical price moves.</p></section><div class="section-head"><h2>The watchlist <span class="muted">/ 18</span></h2><input id="portfolio-search" type="search" placeholder="Filter companies or sectors" aria-label="Filter portfolio" value="${escape(search)}" style="width:240px;padding:10px;font-size:12px"></div><div class="card table-wrap" style="padding:0"><table class="portfolio-table"><thead><tr><th>COMPANY / SECTOR</th><th>CLOSE</th><th>DAILY MOVE</th><th>VOLUME</th><th>SESSION / STATUS</th></tr></thead><tbody>${filtered.map(c=>{const r=records.find(r=>r.ticker===c.ticker);const calc=r?.status==='ok'?marketRule(r):null;return `<tr><td><button data-ticker="${escape(c.ticker)}">${escape(c.ticker)} ↗</button><div class="small-copy" style="font-size:10px;margin:2px 0">${escape(c.sector)}</div></td><td>${r?.status==='ok'?escape(r.currency)+' '+r.close.toLocaleString('en-IN'):'—'}</td><td class="${calc?.change<0?'down':'up'}">${calc?(calc.change>0?'+':'')+calc.change.toFixed(2)+'%':'—'}</td><td>${calc?calc.volume.toFixed(2)+'×':'—'}</td><td>${r?.status==='ok'?dateLabel(r.session_date)+`<div class="small-copy">${calc?.trigger?'Threshold crossed':'No configured trigger'}</div>`:`<span class="muted">Data unavailable</span>`}</td></tr>`}).join('')}</tbody></table>${!filtered.length?'<p class="empty">No matching companies.</p>':''}</div>`;
}

function sources(){
 const docs=data.companies.INFY.sources.filter(s=>(s.title+' '+s.summary).toLowerCase().includes(sourceQuery.toLowerCase()));
 return head('SOURCE LIBRARY / INFY','Follow the evidence.','Original company disclosures, with a page reference for every comparison. Source summaries below are paraphrases.')+
 `<div class="notice"><span><strong>Primary PDFs are now indexed through exchange-hosted copies.</strong> The six original FY25 case-study references below were separately checked through a web reader. Original external links may still be blocked in some environments.</span></div><div class="library">${Object.values(data.research_coverage||{}).filter(c=>c.document_count>0).map(c=>`<article class="card"><div class="eyebrow">${escape(c.ticker)} / IMPORTED PRIMARY PDFS</div><h3>${escape(c.name)}</h3><p>${c.document_count} usable documents · ${c.page_count} pages<br>${c.rejected.length} candidates excluded by source checks.</p><button class="text-button" data-ticker="${escape(c.ticker)}">Search original documents →</button></article>`).join('')}</div><div class="section-head"><h2>Curated Infosys case references</h2></div><form class="search-form" id="source-search-form"><input type="search" id="source-search" aria-label="Search verified source summaries" placeholder="Search curated summaries: growth, margin, FY27…" value="${escape(sourceQuery)}"><button class="button">Search →</button></form><div class="section-head"><h2>${docs.length} curated references</h2><span class="eyebrow">PRIMARY DOCUMENTS ONLY</span></div><div class="library curated-library">${docs.map(s=>`<article class="card"><span class="source-kind">${s.kind.replaceAll('_',' ')} / PDF PAGE ${s.page}</span><h3>${escape(s.title)}</h3><span class="eyebrow">${dateLabel(s.date)}</span><p>${escape(s.summary)}</p>${sourceButton(s.id,'Inspect source ↗')}</article>`).join('')}</div>${!docs.length?'<div class="empty">No curated summary matches this search. Use Research to search the imported document passages.</div>':''}`;
}

function render(){
 const view=location.hash.slice(1)||'briefing';
 for(const link of document.querySelectorAll('[data-view]')){link.classList.toggle('active',link.dataset.view===view);if(link.dataset.view===view)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current')}
 $('#content').innerHTML=({briefing,research,portfolio,sources}[view]||briefing)();
 bind();
}
function toast(message){$('#toast').textContent=message;$('#toast').style.display='block';setTimeout(()=>$('#toast').style.display='none',4000)}
function evidence(id){
 const s=source(id);if(!s)return;
 const url=new URL(s.url);if(url.protocol!=='https:')return;
 $('#evidence-content').innerHTML=`<div class="eyebrow">PRIMARY SOURCE / INFOSYS</div><h2>${escape(s.title)}</h2><div class="eyebrow">PDF page ${s.page} · ${dateLabel(s.date)}</div><p>${escape(s.summary)}</p><div class="evidence-note"><strong>Paraphrased source finding.</strong> ${escape(s.verification)} PDF page numbers are counted from the first PDF page and may differ from printed numbering.</div><a class="button" href="${escape(s.url)}#page=${s.page}" target="_blank" rel="noopener noreferrer">Open original PDF · page ${s.page} ↗</a><p class="small-copy">Source domain: ${escape(url.hostname)}. This view does not display an original document excerpt.</p>`;
 $('#evidence').showModal();
}
function bind(){
 document.querySelectorAll('[data-source]').forEach(b=>b.onclick=()=>evidence(b.dataset.source));
 document.querySelectorAll('[data-ticker]').forEach(b=>b.onclick=()=>{selectedTicker=b.dataset.ticker;location.hash='research';if(location.hash==='#research')render()});
 if($('#toggle-replay'))$('#toggle-replay').onclick=()=>{replay=!replay;render()};
 if($('#window'))$('#window').onchange=e=>{days=Number(e.target.value);render()};
 if($('#filing-category'))$('#filing-category').onchange=e=>{filingCategory=e.target.value;render()};
 if($('#end-date'))$('#end-date').onchange=e=>{if(e.target.value){endDate=e.target.value;render()}};
 if($('#ticker-form'))$('#ticker-form').onsubmit=e=>{e.preventDefault();selectedTicker=$('#ticker').value.trim().toUpperCase();render()};
 if($('#collect-company'))$('#collect-company').onclick=collectCompany;
 if($('#research-query-form'))$('#research-query-form').onsubmit=e=>{e.preventDefault();researchQuery=$('#research-query').value.trim();runRetrieval()};
 document.querySelectorAll('[data-topic]').forEach(b=>b.onclick=()=>{researchQuery=b.dataset.topic;$('#research-query').value=researchQuery;runRetrieval()});
 if($('#retrieval-results'))runRetrieval();
 if($('#reset-ticker'))$('#reset-ticker').onclick=()=>{selectedTicker='INFY';render()};
 if($('#comparison-filter'))$('#comparison-filter').onchange=e=>{comparisonFilter=e.target.value;render()};
 if($('#export'))$('#export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(data.companies.INFY,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='FINN-INFY-evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
 if($('#source-search-form'))$('#source-search-form').onsubmit=e=>{e.preventDefault();sourceQuery=$('#source-search').value;render()};
 if($('#portfolio-search'))$('#portfolio-search').oninput=e=>{const pos=e.target.selectionStart;search=e.target.value;render();$('#portfolio-search').focus();$('#portfolio-search').setSelectionRange(pos,pos)};
 for(const [id,key]of[['price-threshold','price'],['volume-threshold','volume']])if($('#'+id))$('#'+id).onchange=e=>{settings[key]=Number(e.target.value);try{localStorage.setItem('finn-thresholds',JSON.stringify(settings))}catch{}render();toast('Alert thresholds saved for this device.')};
 if($('#reload'))$('#reload').onclick=async()=>{try{const r=await fetch('snapshot.json',{cache:'no-store'});if(!r.ok)throw Error();data=await r.json();render();toast('Saved snapshot reloaded. This does not fetch new market data.')}catch{toast('Snapshot could not be reloaded. Try again.')}};
}
$('#close-evidence').onclick=()=>$('#evidence').close();
$('#evidence').addEventListener('click',e=>{if(e.target===$('#evidence')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close()}});
window.addEventListener('hashchange',()=>{render();window.scrollTo(0,0)});
try{const response=await fetch('snapshot.json');if(!response.ok)throw Error('Research snapshot unavailable');data=await response.json();if(['127.0.0.1','localhost'].includes(location.hostname)){try{const capabilities=await fetch('/api/capabilities');if(capabilities.ok)canCollect=!!(await capabilities.json()).on_demand_ingestion}catch{}}render()}catch(e){$('#content').innerHTML='<div class="empty"><strong>Research could not load.</strong>Please reload this page. Serve the app over HTTP rather than opening the HTML file directly.</div>';console.error(e)}
