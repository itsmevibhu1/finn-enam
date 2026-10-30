let data;
const $ = s => document.querySelector(s);
const escape = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dateLabel = d => d ? new Date(d + 'T12:00:00Z').toLocaleDateString('en-IN', {day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}) : 'Publication date not established';
const percent = n => `${n}%`;
let selectedTicker = 'INFY';
let replay = true;
let endDate = '2025-04-17';
let days = 90;
let comparisonFilter = 'latest';
let search = '';
let sourceQuery = '';
let settings = {price:3,volume:2};
try { settings = {...settings,...JSON.parse(localStorage.getItem('finn-thresholds') || '{}')}; } catch {}
if (!(settings.price >= 1 && settings.price <= 10)) settings.price = 3;
if (!(settings.volume >= 1 && settings.volume <= 5)) settings.volume = 2;
const source = id => data.companies.INFY.sources.find(s => s.id === id);
const sourceButton = (id, label='View evidence ↗') => `<button class="text-button" data-source="${escape(id)}">${label}</button>`;
const head = (eyebrow,title,intro,button='') => `<div class="page-head"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="intro">${intro}</p></div>${button}</div>`;
const note = `<div class="notice"><span><strong>Verified case study.</strong> Figures were manually checked against company documents. Comparison verdicts are calculated in code. AI extraction is not connected.</span><a href="#sources">Inspect sources ↗</a></div>`;

function briefing(){
 const company = data.companies.INFY;
 const end = new Date((replay?endDate:data.as_of)+'T23:59:59Z');
 const start = new Date(end.getTime()-days*86400000);
 const events = company.sources.filter(s=>s.kind==='transcript' && s.date && new Date(s.date+'T12:00:00Z')>=start && new Date(s.date+'T12:00:00Z')<=end);
 events.sort((a,b)=>b.date.localeCompare(a.date));
 const alerts=(data.market.records||[]).filter(r=>r.status==='ok').map(r=>({record:r,calc:marketRule(r)})).filter(r=>r.calc?.trigger);
 const marketSignals=`<div class="section-head"><div><h2>Market signals</h2><div class="eyebrow">EOD SNAPSHOT · SEPARATE FROM THE EVENT REPLAY</div></div><a class="text-button" href="#portfolio">Configure thresholds →</a></div><div class="library">${alerts.length?alerts.map(({record:r,calc:c})=>`<article class="card"><div class="eyebrow">${escape(r.ticker)} · ${dateLabel(r.session_date)}</div><h3>${Math.abs(c.change)>=settings.price?'Price threshold crossed':'Unusual volume'}</h3><div class="mini-metrics" style="width:100%"><div><b class="${c.change<0?'down':'up'}">${c.change>0?'+':''}${c.change.toFixed(2)}%</b><span>Close-to-close change</span></div><div><b>${c.volume.toFixed(2)}×</b><span>Prior 20-session volume</span></div></div><p>Triggered by your rules: ±${settings.price}% price or ${settings.volume}× volume. A threshold crossing does not explain its cause.</p><a href="#portfolio" class="text-button">Inspect portfolio →</a></article>`).join(''):'<div class="empty">No configured thresholds crossed in the available price snapshot.</div>'}</div>`;
 return head('A LITTLE LESS NOISE','Your attention, directed.','A focused view of what changed, what matters, and the evidence behind it.')+
 `<div class="notice ${replay?'warn':''}"><span><strong>${replay?'Historical replay · '+dateLabel(endDate):'Current snapshot · '+dateLabel(data.as_of)}</strong> · ${replay?'Real historical company disclosures; this is not a live exchange feed.':'Only the verified case-study documents are indexed. Portfolio-wide exchange ingestion is not connected.'}</span><button class="text-button" id="toggle-replay">${replay?'Use current date':'Open historical replay'} ↗</button></div>`+
 `<section class="hero" aria-label="Featured research"><div class="hero-copy"><div class="eyebrow">THE SIGNAL / INFOSYS / FY25</div><h2>Growth delivered.<br>The latest promise didn’t.</h2><p>FY25 revenue growth beat the earlier Q1 range, met the Q2 range, and fell below the final Q3 range. The reference point changes the conclusion.</p><a class="text-button" href="#research">Follow the promise →</a></div><div class="hero-figure"><div class="big-number">−0.3<small> pp</small></div><div class="figure-label">Below latest guidance’s lower bound<br>4.2% actual vs. 4.5–5% guided<br>Full-year constant-currency growth</div></div></section>`+
 `<div class="section-head"><div><h2>In your window</h2><div class="eyebrow">${events.length} VERIFIED EVENTS · INFY COVERAGE</div></div><div class="controls"><select id="window" aria-label="Digest time window"><option value="1" ${days===1?'selected':''}>Last 24 hours</option><option value="7" ${days===7?'selected':''}>Last 7 days</option><option value="90" ${days===90?'selected':''}>Last 90 days</option><option value="365" ${days===365?'selected':''}>Last year</option></select>${replay?`<input type="date" id="end-date" aria-label="Replay end date" value="${endDate}" max="${data.as_of}">`:''}</div></div>`+
 `<div class="grid"><section>${events.length?events.map(s=>`<article class="card event"><div class="meta"><div><span class="ticker">INFY</span><span class="tag">${s.id==='q4'?'RESULTS':'GUIDANCE'}</span></div><span class="eyebrow">${dateLabel(s.date)}</span></div><h3>${s.id==='q4'?'FY25 growth below latest guidance; margin within range':s.id==='q2fy27'?'FY27 growth guidance: full-year outcome pending':'FY25 guidance revised · '+s.title.split(' ')[0]}</h3><p>${escape(s.summary)}</p>${s.id==='q4'?'<div class="mini-metrics"><div><b>4.2%</b><span>FY25 CC revenue growth</span></div><div><b>21.1%</b><span>FY25 operating margin</span></div></div>':''}${sourceButton(s.id)} · <a class="text-button" href="#research">Research →</a></article>`).join(''):'<div class="empty"><strong>No indexed disclosures in this window.</strong>This does not establish that no filings occurred. Expand the window or explore the historical replay.</div>'}<div class="small-copy">Ranked using a curated materiality judgment for this case study. Routine-filings ingestion and automatic ranking are not connected. NSE API and RSS access returned HTTP 403 during testing.</div></section><aside><section class="card"><div class="eyebrow">THE NEXT QUESTION</div><h3 style="margin-top:12px">Did the forecast move, or did the business?</h3><p class="small-copy">Read each revision against the same final outcome. Earlier guidance stays visible; a later revision does not rewrite history.</p><a class="text-button" href="#research">Open guidance history →</a><hr class="divider"><div class="eyebrow">COVERAGE, HONESTLY</div><p class="small-copy">18 portfolio companies configured.<br>1 company has verified research.<br>5 guidance comparisons.<br>6 primary-source references.</p></section></aside></div>`+marketSignals;
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
 if(!company) return markup+`<div class="empty"><strong>No verified research indexed for ${escape(selectedTicker)} yet.</strong>The prototype currently has one verified company. It does not generate research from a model’s memory.<br><button class="text-button" id="reset-ticker">Explore Infosys instead →</button></div>`;
 const promises = company.promises.filter(p=>comparisonFilter==='all'||p.id==='growth_q3'||p.id==='margin_q3'||p.id==='growth_fy27');
 return markup+note+`<div class="section-head"><div><h2><span class="ticker">INFY</span> Infosys</h2><p class="small-copy">${escape(company.description)}</p></div><button class="button secondary" id="export">Export evidence ↓</button></div><div class="stats"><div class="stat"><div class="eyebrow">REVENUE GUIDANCE</div><b class="down">Missed</b><small>Latest FY25 range · 4.5–5%</small></div><div class="stat"><div class="eyebrow">MARGIN GUIDANCE</div><b class="up">Met</b><small>FY25 range · 20–22%</small></div><div class="stat"><div class="eyebrow">FY27 GROWTH</div><b>Pending</b><small>Full year ends March 2027</small></div></div><div class="grid"><section><div class="section-head"><h2>The delivery record</h2><select id="comparison-filter" aria-label="Guidance comparison filter"><option value="latest" ${comparisonFilter==='latest'?'selected':''}>Latest guidance</option><option value="all" ${comparisonFilter==='all'?'selected':''}>Include earlier revisions</option></select></div>${promises.map(comparison).join('')}<p class="small-copy">FY25 is a completed historical case, not the latest four-quarter research view. No investment recommendation or explanation of causality is inferred from these comparisons.</p></section><aside><section class="card"><div class="eyebrow">SAME YEAR / DIFFERENT EXPECTATIONS</div><h3 style="margin-top:12px">How the goalposts moved</h3><div class="timeline">${company.promises.filter(p=>p.metric==='revenue_growth'&&p.period==='FY2025').map(p=>`<div class="timeline-item"><small>${dateLabel(source(p.source).date)} · ${source(p.source).title.split(' ')[0]}</small><b>${p.low}–${p.high}%</b><p>${p.assessment.status==='exceeded'?'Final outcome above this range':p.assessment.status==='met'?'Final outcome within this range':'Final outcome below this range'}</p>${sourceButton(p.source,'Source ↗')}</div>`).join('')}<div class="timeline-item"><small>17 Apr 2025 · Full-year outcome</small><b>4.2%</b><p>Constant-currency revenue growth</p>${sourceButton('q4','Source ↗')}</div></div></section><section class="card" style="margin-top:18px"><div class="eyebrow">EVIDENCE DISCIPLINE</div><p class="small-copy">Same financial year. Same metric. Same currency basis. Consolidated scope. Annual guidance is compared with annual delivery.</p><p class="small-copy">The later annual report corroborates growth; it is not used to backdate the April event.</p>${sourceButton('ar25','Annual-report corroboration ↗')}</section></aside></div>`;
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
 const filtered=data.portfolio.filter(c=>(c.ticker+' '+c.sector).toLowerCase().includes(search.toLowerCase()));
 return head('PORTFOLIO / END OF DAY','Watch what matters.','Your mock portfolio and configurable unusual-move rules. Daily prices are snapshots, with their trading date shown.')+
 `<div class="notice ${ok.length?'':'warn'}"><span><strong>${ok.length}/18 price sources available.</strong> ${data.market.refreshed_at?'Last refresh attempt: '+escape(new Date(data.market.refreshed_at).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'}))+' IST.':''} This deployed view does not refresh automatically.</span><button class="text-button" id="reload">Reload saved snapshot ↻</button></div>`+
 `<section class="card"><div class="section-head" style="margin-top:0"><h2>What counts as unusual?</h2><span class="tag">SAVED ON THIS DEVICE</span></div><div class="settings"><label>Daily price move: <output id="price-output">±${settings.price}%</output><input type="range" id="price-threshold" min="1" max="10" step="0.5" value="${settings.price}" aria-label="Daily price move threshold"></label><label>Volume vs. prior 20-session average: <output id="volume-output">${settings.volume}×</output><input type="range" id="volume-threshold" min="1" max="5" step="0.25" value="${settings.volume}" aria-label="Volume multiple threshold"></label></div><p class="small-copy">The current session is excluded from the average. Alerts use completed sessions. Splits and other corporate actions can cause mechanical price moves.</p></section><div class="section-head"><h2>The watchlist <span class="muted">/ 18</span></h2><input id="portfolio-search" type="search" placeholder="Filter companies or sectors" aria-label="Filter portfolio" value="${escape(search)}" style="width:240px;padding:10px;font-size:12px"></div><div class="card table-wrap" style="padding:0"><table class="portfolio-table"><thead><tr><th>COMPANY / SECTOR</th><th>CLOSE</th><th>DAILY MOVE</th><th>VOLUME</th><th>SESSION / STATUS</th></tr></thead><tbody>${filtered.map(c=>{const r=records.find(r=>r.ticker===c.ticker);const calc=r?.status==='ok'?marketRule(r):null;return `<tr><td><button data-ticker="${escape(c.ticker)}">${escape(c.ticker)} ↗</button><div class="small-copy" style="font-size:10px;margin:2px 0">${escape(c.sector)}</div></td><td>${r?.status==='ok'?escape(r.currency)+' '+r.close.toLocaleString('en-IN'):'—'}</td><td class="${calc?.change<0?'down':'up'}">${calc?(calc.change>0?'+':'')+calc.change.toFixed(2)+'%':'—'}</td><td>${calc?calc.volume.toFixed(2)+'×':'—'}</td><td>${r?.status==='ok'?dateLabel(r.session_date)+`<div class="small-copy">${calc?.trigger?'Threshold crossed':'No configured trigger'}</div>`:`<span class="muted">Data unavailable</span>`}</td></tr>`}).join('')}</tbody></table>${!filtered.length?'<p class="empty">No matching companies.</p>':''}</div>`;
}

function sources(){
 const docs=data.companies.INFY.sources.filter(s=>(s.title+' '+s.summary).toLowerCase().includes(sourceQuery.toLowerCase()));
 return head('SOURCE LIBRARY / INFY','Follow the evidence.','Original company disclosures, with a page reference for every comparison. Source summaries below are paraphrases.')+
 `<div class="notice warn"><span><strong>Collection status:</strong> six references were verified through a web PDF reader. Direct downloads returned HTTP 403, so full PDF text is not stored or searchable here. Original links may also be blocked in some environments.</span></div><form class="search-form" id="source-search-form"><input type="search" id="source-search" aria-label="Search verified source summaries" placeholder="Search verified summaries: growth, margin, FY27…" value="${escape(sourceQuery)}"><button class="button">Search →</button></form><div class="section-head"><h2>${docs.length} source references</h2><span class="eyebrow">PRIMARY DOCUMENTS ONLY</span></div><div class="library">${docs.map(s=>`<article class="card"><span class="source-kind">${s.kind.replaceAll('_',' ')} / PDF PAGE ${s.page}</span><h3>${escape(s.title)}</h3><span class="eyebrow">${dateLabel(s.date)}</span><p>${escape(s.summary)}</p>${sourceButton(s.id,'Inspect source ↗')}</article>`).join('')}</div>${!docs.length?'<div class="empty">No verified summary matches this search. Full-document semantic search is not connected.</div>':''}`;
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
 if($('#end-date'))$('#end-date').onchange=e=>{if(e.target.value){endDate=e.target.value;render()}};
 if($('#ticker-form'))$('#ticker-form').onsubmit=e=>{e.preventDefault();selectedTicker=$('#ticker').value.trim().toUpperCase();render()};
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
try{const response=await fetch('snapshot.json');if(!response.ok)throw Error('Research snapshot unavailable');data=await response.json();render()}catch(e){$('#content').innerHTML='<div class="empty"><strong>Research could not load.</strong>Please reload this page. Serve the app over HTTP rather than opening the HTML file directly.</div>';console.error(e)}
