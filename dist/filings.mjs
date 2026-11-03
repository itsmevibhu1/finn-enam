// Window and group observed exchange records without inferring missing filings.
export function prepareFilings(records,start,end,category='all'){
 const inWindow=records.filter(r=>new Date(r.published_at)>=start&&new Date(r.published_at)<=end);
 const categories=[...new Set(inWindow.map(r=>r.category))].sort();
 const grouped=new Map();
 for(const r of inWindow.filter(r=>category==='all'||r.category===category)){
  const key=r.source_url.includes('/corporate-filings-announcements')?r.id:r.ticker+'|'+r.source_url;
  const existing=grouped.get(key);
  if(!existing)grouped.set(key,{...r,related_count:1});
  else existing.related_count++;
 }
 const ordered=[...grouped.values()].sort((a,b)=>b.priority-a.priority||b.published_at.localeCompare(a.published_at));
 return {inWindow,categories,important:ordered.filter(r=>r.priority>10),routine:ordered.filter(r=>r.priority<=10)};
}
