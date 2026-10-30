#!/usr/bin/env python3
"""Refresh EOD prices for the configured portfolio; retain failures explicitly."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, time
import json
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from engine import market_alert

ROOT = Path(__file__).resolve().parents[1]


def fetch(company):
    ticker = company['ticker']
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker + ".NS")}?{urlencode({"range": "3mo", "interval": "1d"})}'
    fetched = datetime.now(timezone.utc)
    try:
        with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=25) as response:
            payload = json.load(response)
        result = payload['chart']['result'][0]
        quotes = result['indicators']['quote'][0]
        india = ZoneInfo('Asia/Kolkata')
        now = fetched.astimezone(india)
        rows = []
        for timestamp, close, volume in zip(result['timestamp'], quotes['close'], quotes['volume']):
            session = datetime.fromtimestamp(timestamp, india).date()
            # Keep only completed daily sessions; allow a buffer after the regular close.
            if session == now.date() and now.time() < time(16, 0):
                continue
            if close is not None and volume is not None:
                rows.append({'date': str(session), 'close': close, 'volume': volume})
        if not rows:
            raise ValueError('No completed sessions available')
        calculation = market_alert([r['close'] for r in rows], [r['volume'] for r in rows])
        return {'ticker': ticker, 'status': 'ok', 'fetched_at': fetched.isoformat(), 'provider': 'Yahoo Finance', 'source_url': url, 'session_date': rows[-1]['date'], 'close': round(rows[-1]['close'], 2), 'volume': rows[-1]['volume'], 'currency': result['meta'].get('currency'), 'history': rows[-21:], 'alert': calculation}
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
        if record['status'] == 'failed' and prior.get(record['ticker'], {}).get('status') == 'ok':
            record['last_successful'] = prior[record['ticker']]
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
