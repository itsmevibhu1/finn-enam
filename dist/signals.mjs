// Historical calculations remain inspectable; only verified current sessions alert.
export function effectiveFreshness(record,calendar,now=new Date()){
 if(!calendar)return record.freshness||{status:'unknown_calendar'};
 const parts=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:calendar.timezone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(now).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));
 if(!calendar.years.includes(Number(parts.year)))return {status:'unknown_calendar'};
 const time=`${parts.hour}:${parts.minute}:${parts.second}`;
 let expected=null;
 for(let offset=0;offset<15;offset++){
  const day=new Date(Date.UTC(Number(parts.year),Number(parts.month)-1,Number(parts.day)-offset,12));
  const key=day.toISOString().slice(0,10);
  if(!calendar.years.includes(day.getUTCFullYear()))break;
  const special=calendar.special_sessions?.[key];
  if(!special&&([0,6].includes(day.getUTCDay())||calendar.holidays.includes(key)))continue;
  let cutoff=special?.eod_available_after||calendar.regular_eod_available_after;
  if(cutoff.length===5)cutoff+=':00';
  if(offset===0&&time<cutoff)continue;
  expected=key;break;
 }
 if(!expected)return {status:'unknown_calendar'};
 return {status:record.session_date===expected?'current':record.session_date<expected?'stale':'unexpected_session',expected_session:expected};
}
export function priceSignal(record,settings,calendar,now){
 const rows=record.history;
 if(!rows||rows.length<21)return null;
 const average=rows.slice(-21,-1).reduce((sum,r)=>sum+r.volume,0)/20;
 const prior=rows.at(-2).close;
 if(!(average>0&&prior>0))return null;
 const change=(rows.at(-1).close/prior-1)*100;
 const volume=rows.at(-1).volume/average;
 const eligible=effectiveFreshness(record,calendar,now).status==='current';
 const crossed=Math.abs(change)>=settings.price||volume>=settings.volume;
 return {change,volume,eligible,crossed,trigger:eligible&&crossed};
}
