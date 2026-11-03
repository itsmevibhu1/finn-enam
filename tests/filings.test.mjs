import {test} from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
const local=new URL('../dist/filings.mjs',import.meta.url);
const {prepareFilings}=await import(existsSync(local)?local:new URL('../finn-site/dist/filings.mjs',import.meta.url));
const start=new Date('2026-11-02T00:00:00+05:30'),end=new Date('2026-11-03T00:00:00+05:30');
const fixture=(id,category,priority,extra={})=>({id,ticker:'TEST',category,priority,published_at:'2026-11-02T12:00:00+05:30',source_url:'https://nsearchives.nseindia.com/'+id+'.pdf',...extra});

test('same attachment is grouped without collapsing unrelated filings',()=>{
 const first=fixture('one','results',90);
 const result=prepareFilings([first,{...first,id:'duplicate'},fixture('two','results',90)],start,end);
 assert.equal(result.important.length,2);
 assert.equal(result.important[0].related_count,2);
});
test('routine disclosures remain inspectable and unknowns stay visible',()=>{
 const result=prepareFilings([fixture('routine','routine',5),fixture('unknown','unclassified',30)],start,end);
 assert.equal(result.routine.length,1);
 assert.equal(result.important[0].category,'unclassified');
});
test('future disclosures do not enter the earlier digest window',()=>{
 const result=prepareFilings([fixture('future','results',90,{published_at:'2026-11-04T12:00:00+05:30'})],start,end);
 assert.equal(result.inWindow.length,0);
});
test('category choice filters the visible records',()=>{
 const result=prepareFilings([fixture('a','results',90),fixture('b','management_change',85)],start,end,'management_change');
 assert.equal(result.important.length,1);
 assert.equal(result.important[0].category,'management_change');
});
