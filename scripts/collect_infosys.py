#!/usr/bin/env python3
"""Collect official Infosys primary documents; preserve content-addressed PDFs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from urllib.request import Request, urlopen

from import_document import import_document

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.infosys.com/investors/reports-filings/'


def sources():
    for year, quarters in [('2024-2025', range(1, 5)), ('2025-2026', [3, 4]), ('2026-2027', [1, 2])]:
        for q in quarters:
            prefix = f'{BASE}quarterly-results/{year}/q{q}/documents/'
            for kind, suffix in [('transcript', 'transcripts/earningscall.pdf'), ('results', 'ifrs-usd-press-release.pdf')]:
                yield {'ticker': 'INFY', 'kind': kind, 'period': f'FY{year[5:]} Q{q}', 'url': prefix + suffix}
    for year in [25, 26]:
        yield {'ticker': 'INFY', 'kind': 'annual_report', 'period': f'FY20{year}', 'url': f'{BASE}annual-report/annual/documents/infosys-ar-{year}.pdf'}


def collect(source):
    try:
        request = Request(source['url'], headers={'User-Agent': 'FINN-Research-Prototype/0.1'})
        with urlopen(request, timeout=60) as response:
            content = response.read(40 * 1024 * 1024 + 1)
        if len(content) > 40 * 1024 * 1024:
            raise ValueError('Document exceeds 40 MB limit')
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'download.pdf'
            path.write_bytes(content)
            result = import_document(SimpleNamespace(pdf=path, ticker=source['ticker'], kind=source['kind'], source_url=source['url'], period=source['period'], output=ROOT / 'data/documents'))
        return {**source, **result, 'fetched_at': datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        return {**source, 'status': 'failed', 'error': str(exc)}


def main():
    with ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(collect, sources()))
    (ROOT / 'data').mkdir(exist_ok=True)
    (ROOT / 'data/source_index.json').write_text(json.dumps(records, indent=2) + '\n')
    for record in records:
        print(record['period'], record['kind'], record['status'], record.get('pages', ''), record.get('error', ''))
    return 0 if any(x['status'] != 'failed' for x in records) else 1


if __name__ == '__main__':
    sys.exit(main())
