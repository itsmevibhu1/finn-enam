#!/usr/bin/env python3
"""Refresh EOD prices for the configured portfolio; retain failures explicitly."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, time, timedelta
import json
import math
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from engine import market_alert
from market_freshness import freshness

ROOT = Path(__file__).resolve().parents[1]


def chart_rows(payload,now):
    error=payload.get('chart',{}).get('error')
    if error:
        raise ValueError('Price provider returned an error')
    result=payload['chart']['result'][0]
    quotes=result['indicators']['quote'][0]
    india=ZoneInfo('Asia/Kolkata')
    local=now.astimezone(india)
    rows={}
    for stamp,close,volume in zip(result['timestamp'],quotes['close'],quotes['volume']):
        session=datetime.fromtimestamp(stamp,india).date()
        if session>local.date() or (session==local.date() and local.time()<time(16,0)):
            continue
        if close is None or volume is None or not math.isfinite(close) or not math.isfinite(volume) or close<=0 or volume<0:
            continue
        rows[str(session)]={'date':str(session),'close':close,'volume':volume}
    if not rows:
        raise ValueError('No valid completed sessions available')
    return sorted(rows.values(),key=lambda r:r['date']),result['meta'].get('currency')


def fetch(company):
    ticker = company['ticker']
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker + ".NS")}?{urlencode({"range": "3mo", "interval": "1d"})}'
    fetched = datetime.now(timezone.utc)
    calendar=json.loads((ROOT/'config/nse_calendar.json').read_text())
    attempts=[]
    try:
        with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=25) as response:
            payload = json.load(response)
        rows,currency=chart_rows(payload,fetched)
        attempts.append({'url':url,'status':'ok','session_date':rows[-1]['date']})
        state=freshness(rows[-1]['date'],fetched,calendar)
        if state['status']=='stale':
            # One bounded retry with explicit timestamps and the alternate Yahoo host.
            params=urlencode({'period1':int((fetched-timedelta(days=90)).timestamp()),'period2':int(fetched.timestamp()),'interval':'1d'})
            retry_url=f'https://query2.finance.yahoo.com/v8/finance/chart/{quote(ticker+".NS")}?{params}'
            try:
                with urlopen(Request(retry_url,headers={'User-Agent':'Mozilla/5.0','Cache-Control':'no-cache'}),timeout=25) as response:
                    retry,currency_retry=chart_rows(json.load(response),fetched)
                attempts.append({'url':retry_url,'status':'ok','session_date':retry[-1]['date']})
                if retry[-1]['date']>rows[-1]['date']:
                    rows,currency,url=retry,currency_retry,retry_url
                state=freshness(rows[-1]['date'],fetched,calendar)
            except Exception as exc:
                attempts.append({'url':retry_url,'status':'failed','error':str(exc)})
        calculation = market_alert([r['close'] for r in rows], [r['volume'] for r in rows])
        return {'ticker': ticker, 'status': 'ok', 'fetched_at': fetched.isoformat(), 'provider': 'Yahoo Finance', 'source_url': url, 'session_date': rows[-1]['date'], 'close': round(rows[-1]['close'], 2), 'volume': rows[-1]['volume'], 'currency': currency, 'history': rows[-21:], 'alert': calculation,'freshness':state,'calendar_source':calendar['source_url'],'attempts':attempts}
    except Exception as exc:
        return {'ticker': ticker, 'status': 'failed', 'fetched_at': fetched.isoformat(), 'source_url': url, 'error': str(exc)}


def main():
    companies = json.loads((ROOT / 'config/portfolio.json').read_text())['companies']
    path = ROOT / 'data/market.json'
    previous = json.loads(path.read_text()) if path.exists() else {'records': []}
    prior = {r['ticker']: r for r in previous['records']}
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(fetch, companies))
    for record in records:
        old=prior.get(record['ticker'],{})
        if record['status'] == 'failed':
            last=old if old.get('status')=='ok' else old.get('last_successful')
            if last:
                record['last_successful']=last
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({'refreshed_at': datetime.now(timezone.utc).isoformat(), 'note': 'Completed daily sessions; price change uses close-to-close prices. Corporate actions may cause mechanical price alerts.', 'records': records}, indent=2) + '\n')
    ok = sum(r['status'] == 'ok' for r in records)
    print(f'Price ingestion: {ok}/{len(records)} succeeded. Failures are retained in data/market.json.')
    for record in records:
        if record['status'] == 'failed':
            print(record['ticker'], record['error'])
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
