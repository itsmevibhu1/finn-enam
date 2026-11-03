#!/usr/bin/env python3
"""Fetch NSE's public portfolio announcements; retain source subjects verbatim."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
from http.cookiejar import CookieJar
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlencode, urlsplit
from urllib.request import build_opener, HTTPCookieProcessor, Request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ISSUER_NAMES={'RELIANCE':'Reliance Industries','TCS':'Tata Consultancy Services','INFY':'Infosys','HDFCBANK':'HDFC Bank','ICICIBANK':'ICICI Bank','ITC':'ITC','HINDUNILVR':'Hindustan Unilever','SUNPHARMA':'Sun Pharmaceutical Industries','CIPLA':'Cipla','MARUTI':'Maruti Suzuki India','EICHERMOT':'Eicher Motors','LT':'Larsen & Toubro','TITAN':'Titan Company','PIDILITIND':'Pidilite Industries','POLYCAB':'Polycab India','APLAPOLLO':'APL Apollo Tubes','CERA':'Cera Sanitaryware','VSTIND':'VST Industries'}
RULES = [
    ('results', 90, r'financial results|quarterly results|financial statements|audited results'),
    ('management_change', 85, r'resignation|chief financial|chief executive|change in management|appointment.*(director|officer)'),
    ('M&A', 85, r'acquisition|merger|demerger|joint venture'),
    ('litigation', 80, r'litigation|penalty|regulatory order|insolvency'),
    ('fund_raise', 75, r'fund rais|rights issue|preferential|buyback|buy-back'),
    ('credit_rating', 65, r'credit rating|rating.*(upgrade|downgrade)'),
    ('capex', 65, r'capacity expansion|capital expenditure|new plant'),
    ('dividend', 55, r'dividend'),
    ('earnings_call', 50, r'transcript|earnings call|conference call'),
    ('investor_meetings', 10, r'analyst.*meet|investor.*meet|schedule.*investor'),
    ('routine', 5, r'compliance|certificate|newspaper|loss of share|duplicate share|esop|trading window|postal ballot'),
    ('press_release', 40, r'press release|bagging/receiving|order win'),
]


def classify(text):
    if re.search(r'newspaper|trading window|duplicate share|loss of share|compliance certificate|schedule.*(analyst|investor)|intimation.*board meeting', text, re.I):
        return 'routine', 5
    if re.search(r'\btranscript\b|(?:audio|video|link of)\s*recording',text,re.I):
        return 'earnings_call',50
    if re.search(r'allotment of securities',text,re.I) and not re.search(r'rights issue|qip|preferential|buy.?back|commercial paper|debentur',text,re.I):
        return 'unclassified',30
    for category, priority, pattern in RULES:
        if re.search(pattern, text, re.I):
            return category, priority
    return 'unclassified', 30


def normalized_issuer(value):
    value=re.sub(r'\b(?:limited|ltd)\.?\s*$','',value.strip(),flags=re.I)
    return re.sub(r'[^a-z0-9]','',value.lower())


def match_issuer(title,description,tickers):
    # Some feeds provide an explicit symbol prefix; only an exact symbol qualifies.
    explicit=re.match(r'^\s*([A-Z0-9&_.-]+)\s*:',description)
    if explicit:
        return explicit.group(1) if explicit.group(1) in tickers else None
    issuer=normalized_issuer(title)
    matches=[ticker for ticker in tickers if issuer in {normalized_issuer(ticker),normalized_issuer(ISSUER_NAMES.get(ticker,''))}]
    return matches[0] if len(matches)==1 else None


def parse_timestamp(value):
    """NSE RSS uses DD-MON-YYYY HH:MM rather than an RFC email date."""
    for fmt in ('%d-%b-%Y %H:%M', '%d-%b-%Y %H:%M:%S', '%d-%m-%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=ZoneInfo('Asia/Kolkata'))
        except (ValueError, AttributeError):
            pass
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=ZoneInfo('Asia/Kolkata'))
    except (ValueError, TypeError, AttributeError):
        return None


def normalize(row, tickers):
    ticker = row.get('symbol', '')
    if ticker not in tickers:
        return None
    subject = str(row.get('desc') or row.get('subject') or 'Announcement')
    details = str(row.get('attchmntText') or '')
    raw_time = row.get('an_dt') or row.get('sort_date') or ''
    timestamp = parse_timestamp(raw_time)
    published = timestamp.isoformat() if timestamp else None
    # Undated rows must not silently acquire the current date.
    if not published:
        return None
    category, priority = classify(subject+' '+details)
    url = row.get('attchmntFile') or ''
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.nseindia.com'):
        url = 'https://www.nseindia.com/companies-listing/corporate-filings-announcements'
    identity = hashlib.sha256((ticker + published + subject + url).encode()).hexdigest()[:20]
    return {'id': identity, 'ticker': ticker, 'subject': subject, 'details': details, 'published_at': published, 'source_url': url, 'category': category, 'priority': priority, 'classification_method': 'Keyword rules; not an AI materiality assessment'}


def main():
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo('Asia/Kolkata')).date()
    query = urlencode({'index':'equities','from_date':(today-timedelta(days=7)).strftime('%d-%m-%Y'),'to_date':today.strftime('%d-%m-%Y')})
    url = 'https://www.nseindia.com/api/corporate-announcements?' + query
    path = ROOT/'data/announcements.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    headers = {'User-Agent':'Mozilla/5.0', 'Accept':'application/json,text/html', 'Referer':'https://www.nseindia.com/companies-listing/corporate-filings-announcements'}
    result = {'fetched_at':now.isoformat(),'source_url':url,'coverage_start':str(today-timedelta(days=7)),'coverage_end':str(today),'records':[]}
    try:
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        with opener.open(Request('https://www.nseindia.com',headers=headers),timeout=30) as response:
            response.read()
        with opener.open(Request(url,headers=headers),timeout=30) as response:
            rows = json.load(response)
        if not isinstance(rows,list):
            raise ValueError('Unexpected announcement response')
        tickers = {c['ticker'] for c in json.loads((ROOT/'config/portfolio.json').read_text())['companies']}
        records = [record for row in rows if (record:=normalize(row,tickers))]
        result.update(status='ok', records=list({r['id']:r for r in records}.values()),total_exchange_rows=len(rows))
    except Exception as exc:
        result.update(status='failed',error=str(exc))
        # NSE also publishes a public RSS feed. Its rolling coverage is not a 7-day archive.
        rss_url = 'https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml'
        try:
            with build_opener().open(Request(rss_url,headers=headers),timeout=30) as response:
                raw = response.read()
            cache = ROOT/'data/cache'
            cache.mkdir(exist_ok=True)
            (cache/'nse-announcements.xml').write_bytes(raw)
            tree = ET.fromstring(raw)
            companies = json.loads((ROOT/'config/portfolio.json').read_text())['companies']
            records=[]
            dates=[]
            skipped_dates=0
            for item in tree.findall('.//item'):
                title = item.findtext('title') or ''
                description = item.findtext('description') or ''
                published = parse_timestamp(item.findtext('pubDate') or '')
                if not published:
                    skipped_dates+=1
                    continue
                dates.append(published)
                ticker=match_issuer(title,description,{c['ticker'] for c in companies})
                if not ticker:
                    continue
                link=item.findtext('link') or ''
                parsed=urlsplit(link)
                if parsed.scheme!='https' or not (parsed.hostname or '').endswith('.nseindia.com'):
                    link='https://www.nseindia.com/companies-listing/corporate-filings-announcements'
                text=re.sub('<[^>]+>',' ',description)
                category,priority=classify(text)
                identity=hashlib.sha256((ticker+published.isoformat()+link+text).encode()).hexdigest()[:20]
                records.append({'id':identity,'ticker':ticker,'subject':title,'details':text,'published_at':published.isoformat(),'source_url':link,'category':category,'priority':priority,'classification_method':'Keyword rules on exchange RSS description','issuer_match':'Exact normalized issuer name or explicit exchange symbol'})
            if not dates:
                raise ValueError('RSS contains no dated items')
            result.update(status='ok',provider='NSE RSS',source_url=rss_url,records=list({r['id']:r for r in records}.values()),coverage_start=min(dates).isoformat(),coverage_end=max(dates).isoformat(),coverage_note='Rolling RSS snapshot only; not a complete historical archive.',api_error=str(exc),skipped_dates=skipped_dates,total_exchange_rows=len(dates))
            result.pop('error',None)
        except Exception as rss_exc:
            result['rss_error']=str(rss_exc)
        if result['status']=='failed' and previous.get('status')=='ok':
            result['last_successful']=previous
    # Persist successfully observed events so rolling feeds do not erase earlier observations.
    if result['status']=='ok':
        archive_path=ROOT/'data/announcement_archive.json'
        archived=json.loads(archive_path.read_text()) if archive_path.exists() else {'records':[]}
        merged={}
        rejected=archived.get('rejected_issuer_matches',[])
        tickers={c['ticker'] for c in json.loads((ROOT/'config/portfolio.json').read_text())['companies']}
        for record in archived['records']:
            if record.get('issuer_match') or match_issuer(record['subject'],record.get('details',''),tickers)==record['ticker']:
                record['category'],record['priority']=classify(record['subject']+' '+record.get('details',''))
                merged[record['id']]=record
            else:
                rejected.append({**record,'rejection_reason':'Legacy substring match did not identify the exact portfolio issuer'})
        merged.update({r['id']:r for r in result['records']})
        archived.update(records=sorted(merged.values(),key=lambda r:r['published_at'],reverse=True),updated_at=now.isoformat(),rejected_issuer_matches=list({r['id']:r for r in rejected}.values()))
        archive_path.write_text(json.dumps(archived,indent=2)+'\n')
        result['records']=archived['records']
        result['coverage_note']='Observed filings accumulated from rolling snapshots; gaps between refreshes may be missing.'
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(f'NSE announcements: {result["status"]}; {len(result["records"])} portfolio filings.',result.get('error',''))
    return 0 if result['status']=='ok' else 1


if __name__=='__main__':
    raise SystemExit(main())
