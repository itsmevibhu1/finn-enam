#!/usr/bin/env python3
"""Exercise the configured demo questions through the hosted public API, serially."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]


def run(base):
    parsed=urlsplit(base)
    if parsed.scheme!='https' or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Provide an HTTPS service origin without credentials or query parameters')
    cases=json.loads((ROOT/'config/research_eval.json').read_text())['cases']
    report={'service':base,'checked_at':datetime.now(timezone.utc).isoformat(),'cases':[],'note':'Live functional sample, not a statistically meaningful accuracy benchmark. Failed provider requests count toward the runtime cap.'}
    for case in cases:
        payload={key:case[key] for key in ('ticker','question','scope','period')}
        row={**payload,'status':'failed'}
        try:
            request=Request(base+'/api/research',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Origin':base,'X-FINN-Request':'local'},method='POST')
            with urlopen(request,timeout=30) as response:job=json.load(response)
            for attempt in range(240):
                with urlopen(base+'/api/jobs/'+job['job_id'],timeout=30) as response:state=json.load(response)
                if state['status']=='complete':
                    row.update(status='complete',answer=state['result']);break
                if state['status']=='failed':
                    row['error']=state.get('error','Unspecified failure');break
                time.sleep(1)
            else:row['error']='Polling window expired'
        except Exception as exc:
            row['error']=type(exc).__name__
        report['cases'].append(row)
        path=ROOT/'docs/HOSTED_DEMO_RESULTS.json'
        path.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'ticker':case['ticker'],'status':row['status'],'answer_status':row.get('answer',{}).get('status'),'observations':len(row.get('answer',{}).get('observations',[])),'latency_seconds':row.get('answer',{}).get('latency_seconds'),'error':row.get('error')}),flush=True)
        if 'daily Gemini request cap' in row.get('error',''):
            break
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origin')
    run(parser.parse_args().origin.rstrip('/'))
