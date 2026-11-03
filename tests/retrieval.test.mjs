import {test} from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
const local=new URL('../dist/retrieval.mjs',import.meta.url);
const {searchCorpus}=await import(existsSync(local)?local:new URL('../finn-site/dist/retrieval.mjs',import.meta.url));

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
