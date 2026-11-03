import {test} from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
const local=new URL('../dist/retrieval.mjs',import.meta.url);
const {searchCorpus,filterCorpus}=await import(existsSync(local)?local:new URL('../finn-site/dist/retrieval.mjs',import.meta.url));

const corpus={documents:[{id:'a',url:'https://example.com/a.pdf'},{id:'b',url:'https://example.com/b.pdf'}],passages:[
 {id:'a1',document:'a',page:7,text:'The company revised its revenue growth guidance to reflect its outlook for the full financial year.'},
 {id:'a2',document:'a',page:8,text:'Our revenue growth guidance remains unchanged and our operating margin outlook is stable.'},
 {id:'b1',document:'b',page:3,text:'Cash flow from operations increased during the year while debt declined.'}
]};

test('matching passages retain original document and page references',()=>{
 const results=searchCorpus(corpus,'cash flow');
 assert.equal(results[0].document.id,'b');
 assert.equal(results[0].page,3);
});
test('one passage per document avoids duplicate evidence',()=>{
 assert.equal(searchCorpus(corpus,'growth guidance').length,1);
});
test('stopword-only questions produce no invented result',()=>{
 assert.deepEqual(searchCorpus(corpus,'what did the company say'),[]);
});
test('unknown terms produce an evidence gap',()=>{
 assert.deepEqual(searchCorpus(corpus,'zzzzzzzz'),[]);
});
test('excerpts stay within 25 words per document',()=>{
 for(const result of searchCorpus(corpus,'guidance cash'))assert(result.snippet.split(/\s+/).length<=25);
});
test('guidance search does not match unrelated industry forecasts',()=>{
 const unrelated={documents:[{id:'industry'}],passages:[{id:'forecast',document:'industry',page:1,text:'Industry technology spending forecast from an external trade association.'}]};
 assert.deepEqual(searchCorpus(unrelated,'growth guidance'),[]);
});
test('guide and guided retrieve a source that says guidance',()=>{
 assert(searchCorpus(corpus,'what did management guide').length>0);
});
test('earnings scope excludes earlier media pages in a combined PDF',()=>{
 const mixed={documents:[{id:'combined'}],passages:[{document:'combined',page:3,event_type:'media_conference',text:'growth guidance'},{document:'combined',page:24,event_type:'earnings_call',reporting_period:'Q2 FY2027',text:'growth guidance'}]};
 const result=searchCorpus(filterCorpus(mixed,{scope:'earnings'}),'growth guidance');
 assert.equal(result.length,1);assert.equal(result[0].page,24);
});
test('a missing reporting period cannot return another quarter',()=>{
 const one={documents:[{id:'a'}],passages:[{document:'a',page:1,event_type:'earnings_call',reporting_period:'Q1 FY2027',text:'growth guidance'}]};
 assert.equal(filterCorpus(one,{period:'Q4 FY2026'}).passages.length,0);
});
