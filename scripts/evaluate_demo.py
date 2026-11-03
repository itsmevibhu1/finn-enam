#!/usr/bin/env python3
"""Run reproducible demo calibration checks without a model API call."""
from datetime import datetime,timezone
import json
from pathlib import Path
from engine import assess
from model_research import retrieve,static_directory,normalized
from refresh_announcements import classify,match_issuer

ROOT=Path(__file__).resolve().parents[1]


def evaluate():
    snapshot=json.loads((static_directory()/'snapshot.json').read_text())
    specification=json.loads((ROOT/'config/research_eval.json').read_text())
    cases=[]
    for case in specification['cases']+specification['negative_cases']:
        corpus=json.loads((static_directory()/'corpora'/f'{case["ticker"]}.json').read_text())
        coverage=snapshot['research_coverage'][case['ticker']]
        evidence=retrieve(corpus,case['question'],case['scope'],case['period'],coverage['quarter_coverage']['expected_from_latest_available'])
        expected=case.get('document_id')
        matches=[e for e in evidence if e['document_id']==expected and e['pdf_page']==case.get('page') and normalized(case.get('anchor','')).casefold() in normalized(e['text']).casefold()]
        cases.append({'ticker':case['ticker'],'question':case['question'],'scope':case['scope'],'period':case['period'],'expected':'source_passage' if expected else 'no_evidence','passed':bool(matches) if expected else not evidence,'retrieved':[{'url':e['url'],'pdf_page':e['pdf_page'],'reporting_period':e['call_reporting_period']} for e in evidence]})
    announcements=json.loads((ROOT/'data/announcement_eval.json').read_text())
    labels=[{'issuer':c['issuer'],'source_url':c['source_url'],'expected':c['expected_category'],'actual':classify(c['description'])[0],'baseline':c['baseline_category']} for c in announcements['cases']]
    false_issuers=['Slone Infosystems Limited','Reliance Mutual Fund','HDFC Asset Management Company Limited']
    issuer_checks=[{'issuer':name,'passed':match_issuer(name,'General Updates',{'INFY','RELIANCE','HDFCBANK'}) is None} for name in false_issuers]
    expected={'growth_q1':'exceeded','growth_q2':'met','growth_q3':'missed','margin_q3':'met','growth_fy27':'pending'}
    comparisons=[]
    for promise in json.loads((ROOT/'data/research.json').read_text())['companies']['INFY']['promises']:
        outcome=None
        if promise['actual'] is not None:
            outcome={k:promise[k] for k in ('metric','period','unit','basis','scope')}
            outcome.update(value=promise['actual'],published_at=promise['outcome_date'])
        actual=assess(promise,outcome,snapshot['as_of'])['status']
        comparisons.append({'id':promise['id'],'expected':expected[promise['id']],'actual':actual})
    summary={'research_passages':{'passed':sum(c['passed'] for c in cases if c['expected']=='source_passage'),'total':len(specification['cases'])},'negative_questions':{'passed':sum(c['passed'] for c in cases if c['expected']=='no_evidence'),'total':len(specification['negative_cases'])},'announcement_description_labels':{'baseline_correct':sum(c['baseline']==c['expected'] for c in labels),'current_correct':sum(c['actual']==c['expected'] for c in labels),'total':len(labels)},'false_issuer_matches_rejected':sum(c['passed'] for c in issuer_checks),'curated_comparisons':{'passed':sum(c['actual']==c['expected'] for c in comparisons),'total':len(comparisons)}}
    return {'generated_at':datetime.now(timezone.utc).isoformat(),'model_calls':0,'limitations':[specification['method'],announcements['method'],'Comparison checks reproduce the curated case in code; they are not automatic financial extraction.'], 'summary':summary,'research_cases':cases,'announcements':labels,'issuer_checks':issuer_checks,'comparisons':comparisons}


if __name__=='__main__':
    result=evaluate()
    (ROOT/'docs/EVALUATION_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['summary'],indent=2))
    failed=any(not c['passed'] for c in result['research_cases']+result['issuer_checks']) or any(c['actual']!=c['expected'] for c in result['announcements']+result['comparisons'])
    raise SystemExit(1 if failed else 0)
