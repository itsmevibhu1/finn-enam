// Browser/local keyword retrieval over primary-document passages. No model calls.
const stop = new Set('a an and are as at be been by can company did do does for from had has have how i in is it its management of on or our say said should that the their them these this to us was we were what when where which who why will with would you your'.split(' '));
const canonical = term => /^(guide|guided|guidance|outlook)$/.test(term)?'guidance':term.replace(/s$/,'');
export const tokenize = text => text.toLowerCase().match(/[a-z0-9]+/g) || [];
export function filterCorpus(corpus,{scope='all',period='all',window=[]}={}){
 return {...corpus,passages:corpus.passages.filter(p=>{
  if(scope==='earnings'&&p.event_type!=='earnings_call')return false;
  if(scope==='annual'&&p.event_type!=='annual_report')return false;
  if(period==='latest4'&&!window.includes(p.reporting_period))return false;
  if(period!=='all'&&period!=='latest4'&&p.reporting_period!==period)return false;
  return true;
 })};
}
function queryTerms(query){
 const terms=[...new Set(tokenize(query).filter(t=>!stop.has(t)&&t.length>2))];
 const variants=new Set(terms);
 for(const term of terms){
  if(/^(guide|guided|guidance|outlook)$/.test(term))for(const x of ['guidance','outlook'])variants.add(x);
  if(/^margins?$/.test(term))for(const x of ['margin','margins'])variants.add(x);
  if(/^revenues?$/.test(term))for(const x of ['revenue','revenues'])variants.add(x);
 }
 return [...variants];
}
export function searchCorpus(corpus,query,limit=5){
 const terms=queryTerms(query);
 const originalTerms=tokenize(query).filter(t=>!stop.has(t)&&t.length>2);
 if(!terms.length)return [];
 const entries=corpus.passages.map(p=>({passage:p,words:tokenize(p.text)}));
 const average=entries.reduce((n,e)=>n+e.words.length,0)/Math.max(entries.length,1);
 const frequency=Object.fromEntries(terms.map(t=>[t,entries.filter(e=>e.words.includes(t)).length]));
 const ranked=entries.map(({passage,words})=>{
  let score=0;const matched=[];
  for(const term of terms){
   const count=words.filter(w=>w===term).length;
   if(!count)continue;
   matched.push(term);
   const inverse=Math.log(1+(entries.length-frequency[term]+0.5)/(frequency[term]+0.5));
   score+=inverse*(count*2.2)/(count+1.2*(0.25+0.75*words.length/Math.max(average,1)));
  }
  return {passage,score,matched};
 }).filter(r=>r.score>0&&r.matched.some(term=>originalTerms.some(original=>canonical(original)===canonical(term)))).sort((a,b)=>b.score-a.score);
 const documents=new Set();
 const results=[];
 for(const entry of ranked){
  if(documents.has(entry.passage.document))continue;
  documents.add(entry.passage.document);
  const words=entry.passage.text.split(/\s+/);
  // Select the short window with the most query coverage, rather than stopping
  // at an incidental early mention elsewhere in the same passage.
  let bestStart=0,bestScore=-1;
  for(let start=0;start<words.length;start++){
   const windowTokens=tokenize(words.slice(start,start+25).join(' '));
   const present=entry.matched.filter(term=>windowTokens.includes(term));
   const numericContext=Math.min(3,words.slice(start,start+25).filter(word=>/\d/.test(word)).length)*0.08;
   const score=present.reduce((sum,term)=>sum+Math.log(1+(entries.length-frequency[term]+0.5)/(frequency[term]+0.5)),0)+numericContext;
   if(score>bestScore){bestScore=score;bestStart=start}
  }
  const snippet=words.slice(bestStart,bestStart+25).join(' ');
  results.push({document:corpus.documents.find(d=>d.id===entry.passage.document),page:entry.passage.page,snippet,matched:entry.matched,score:entry.score,passage_id:entry.passage.id,event_type:entry.passage.event_type,reporting_period:entry.passage.reporting_period});
  if(results.length>=limit)break;
 }
 return results;
}
