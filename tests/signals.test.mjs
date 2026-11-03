import {test} from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {readFileSync} from 'node:fs';
const local=new URL('../dist/signals.mjs',import.meta.url);
const {priceSignal,effectiveFreshness}=await import(existsSync(local)?local:new URL('../finn-site/dist/signals.mjs',import.meta.url));
const calendar=JSON.parse(readFileSync(new URL('../config/nse_calendar.json',import.meta.url)));
const record={history:[...Array.from({length:20},()=>({close:100,volume:100})),{close:104,volume:300}]};
test('current-session crossing can alert',()=>{
 assert(priceSignal({...record,freshness:{status:'current'}},{price:3,volume:2}).trigger);
});
test('stale crossing remains inspectable but cannot alert',()=>{
 const result=priceSignal({...record,freshness:{status:'stale'}},{price:3,volume:2});
 assert(result.crossed);assert(!result.trigger);assert(!result.eligible);
});
test('missing calendar verification cannot alert',()=>{
 assert(!priceSignal(record,{price:3,volume:2}).trigger);
});
test('a snapshot becomes stale after the next session cutoff',()=>{
 const snapshot={...record,session_date:'2026-11-02',freshness:{status:'current'}};
 assert(priceSignal(snapshot,{price:3,volume:2},calendar,new Date('2026-11-03T09:00:00+05:30')).trigger);
 assert(!priceSignal(snapshot,{price:3,volume:2},calendar,new Date('2026-11-03T17:00:00+05:30')).trigger);
});
test('runtime calendar includes the special Sunday session',()=>{
 const result=effectiveFreshness({session_date:'2026-11-08'},calendar,new Date('2026-11-09T09:00:00+05:30'));
 assert.equal(result.status,'current');
});
