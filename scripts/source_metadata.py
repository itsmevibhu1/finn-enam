"""Identify reporting periods and distinct call sections inside primary PDFs."""
from datetime import datetime
import re


def reporting_period(text):
    text=re.sub(r'\s+',' ',text)
    for word,number in [('first',1),('second',2),('third',3),('fourth',4)]:
        text=re.sub(r'\b'+word+r'\s+quarter\b',f'Q{number}',text,flags=re.I)
    explicit=re.search(r'Q\s*([1-4])\s*[,/\s\'’]*(?:(?:and|&)\s*(?:(?:annual|full.year)\s*)?)?FY\s*[\'’]?\s*(20\d{2}|\d{2})\b',text,re.I)
    if explicit:
        year=int(explicit.group(2))
        return f'Q{explicit.group(1)} FY{year+2000 if year<100 else year}'
    ended=re.search(r'quarter\s+(?:and\s+year\s+)?ended\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+(20\d{2})',text,re.I)
    if ended:
        month=datetime.strptime(ended.group(1),'%B').month
        year=int(ended.group(2))+(month>=4)
        return f'Q{(month-4)%12//3+1} FY{year}'
    return None


def transcript_metadata(pages):
    opening=' '.join(p['text'] for p in pages[:5])
    fallback_period=reporting_period(opening)
    boundaries=[]
    for index,page in enumerate(pages):
        text=page['text']
        header=re.sub(r'\s+',' ',' '.join(text.splitlines()[:12]))
        kind=None
        if re.search(r'investor\s+AI\s+day|analysts?\s+(?:day|meet)',header,re.I):
            kind='investor_event'
        elif re.search(r'(?:media|press)\s+conference\s+call',header,re.I):
            kind='media_conference'
        else:
            match=re.search(r'earnings\s+(?:conference\s+)?call',header,re.I)
            if match and not re.search(r'moderator|welcome|thank you|sub\s*[:.]|dear sir|stock exchange',header[:match.start()],re.I):
                kind='earnings_call'
        if kind:
            period=reporting_period(text[:3000]) if kind=='earnings_call' else None
            boundaries.append({'start_page':index+1,'event_type':kind,'reporting_period':period})
    if not boundaries:
        kind='earnings_call' if fallback_period and re.search(r'(?:conference|earnings)\s+call',opening,re.I) else 'other_company_call'
        boundaries=[{'start_page':1,'event_type':kind,'reporting_period':fallback_period if kind=='earnings_call' else None}]
    # Consecutive title pages of the same call are a single section.
    merged=[]
    for section in boundaries:
        if merged and section['event_type']==merged[-1]['event_type'] and section['reporting_period']==merged[-1]['reporting_period']:
            continue
        merged.append(section)
    for index,section in enumerate(merged):
        section['end_page']=merged[index+1]['start_page']-1 if index+1<len(merged) else len(pages)
        if section['event_type']=='earnings_call' and not section['reporting_period']:
            section['reporting_period']=fallback_period
    periods=sorted({s['reporting_period'] for s in merged if s['event_type']=='earnings_call' and s['reporting_period']},key=period_sort_key,reverse=True)
    kinds={s['event_type'] for s in merged}
    kind=next(iter(kinds)) if len(kinds)==1 else 'mixed_transcripts'
    return {'event_type':kind,'reporting_period':periods[0] if len(periods)==1 else None,'earnings_periods':periods,'sections':merged}


def period_sort_key(value):
    match=re.fullmatch(r'Q([1-4]) FY(20\d{2})',value or '')
    return int(match.group(2))*4+int(match.group(1)) if match else -1


def quarter_coverage(periods,target=4):
    ordered=sorted(set(periods),key=period_sort_key,reverse=True)
    expected=[]
    if ordered:
        latest=period_sort_key(ordered[0])
        for offset in range(target):
            value=latest-offset
            year=(value-1)//4
            quarter=(value-1)%4+1
            expected.append(f'Q{quarter} FY{year}')
    return {'periods':ordered,'target':target,'expected_from_latest_available':expected,'missing':[p for p in expected if p not in ordered],'complete':len(ordered)>=target and all(p in ordered for p in expected)}
