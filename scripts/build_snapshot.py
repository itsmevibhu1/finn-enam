"""Build the static research snapshot from verified records and rule-based verdicts."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from zoneinfo import ZoneInfo
from engine import assess
from build_corpus import build as build_corpus

ROOT = Path(__file__).resolve().parents[1]


def build():
    research = json.loads((ROOT / 'data/research.json').read_text())
    research['as_of'] = datetime.now(timezone.utc).astimezone(ZoneInfo('Asia/Kolkata')).date().isoformat()
    research['research_coverage'] = build_corpus()
    for company in research['companies'].values():
        source_map = {s['id']: s for s in company['sources']}
        for promise in company['promises']:
            assert promise['source'] in source_map
            outcome = None
            if promise['actual'] is not None:
                assert promise['outcome_source'] in source_map
                outcome = {k: promise[k] for k in ('metric', 'period', 'unit', 'basis', 'scope')}
                outcome.update(value=promise['actual'], published_at=promise['outcome_date'])
            promise['assessment'] = assess(promise, outcome, research['as_of'])
    research['portfolio'] = json.loads((ROOT / 'config/portfolio.json').read_text())['companies']
    research['built_at'] = datetime.now(timezone.utc).isoformat()
    market_path = ROOT / 'data/market.json'
    research['market'] = json.loads(market_path.read_text()) if market_path.exists() else {'records': [], 'note': 'Market ingestion has not run.'}
    announcement_path = ROOT / 'data/announcements.json'
    research['announcements'] = json.loads(announcement_path.read_text()) if announcement_path.exists() else {'status':'not_connected', 'records':[]}
    dest = ROOT / 'dist' if (ROOT / '.openai/hosting.json').exists() else ROOT / 'finn-site/dist'
    dest.mkdir(parents=True, exist_ok=True)
    temporary=dest/'snapshot.json.tmp'
    temporary.write_text(json.dumps(research, indent=2) + '\n')
    temporary.replace(dest/'snapshot.json')
    portfolio = ROOT / 'config/portfolio.json'
    shutil.copyfile(portfolio, dest / 'portfolio.json')
    comparisons=sum(len(c['promises']) for c in research['companies'].values())
    print(f'Built snapshot: {len(research["companies"])} curated company, {len(research["research_coverage"])} document corpora, {comparisons} comparisons, {len(research["portfolio"])} portfolio companies')


if __name__ == '__main__':
    build()
