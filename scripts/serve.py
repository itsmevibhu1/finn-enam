#!/usr/bin/env python3
"""Local FINN server with bounded, on-demand primary-document ingestion."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
from threading import Lock
from urllib.parse import urlsplit
import uuid

from research_pipeline import collect,retain_collection
from build_snapshot import build
from model_research import available,generate

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'dist' if (ROOT/'.openai/hosting.json').exists() else ROOT/'finn-site/dist'
LOCK=Lock()
JOBS={}
POOL=ThreadPoolExecutor(max_workers=1)
MODEL_POOL=ThreadPoolExecutor(max_workers=1)


def run_research(job_id,payload):
    with LOCK:
        JOBS[job_id]['status']='running'
    try:
        result=generate(**payload)
        with LOCK:
            JOBS[job_id].update(status='complete',result=result)
    except (ValueError,FileNotFoundError) as exc:
        with LOCK:
            JOBS[job_id].update(status='failed',error=str(exc) if isinstance(exc,ValueError) else 'No primary-document corpus indexed for this company.')
    except Exception:
        with LOCK:
            JOBS[job_id].update(status='failed',error='Research could not complete. No draft was published.')


def run_job(job_id,ticker):
    with LOCK:
        JOBS[job_id]['status']='running'
    try:
        company=collect(ticker)
        with LOCK:
            path=ROOT/'data/company_discovery.json'
            existing=json.loads(path.read_text()) if path.exists() else {'companies':{}}
            retain_collection(existing,ticker,company)
            path.write_text(json.dumps(existing,indent=2)+'\n')
            build()
            JOBS[job_id].update(status='complete' if company['status']=='ok' else 'failed',result=company['status'])
    except Exception as exc:
        with LOCK:
            JOBS[job_id].update(status='failed',error=str(exc))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(STATIC),**kwargs)

    def json(self,payload,status=200):
        content=json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/healthz':
            return self.json({'status':'ok'})
        if path=='/api/capabilities':
            return self.json({'on_demand_ingestion':True,'model_generation':available()})
        if path.startswith('/api/jobs/'):
            with LOCK:
                job=JOBS.get(path.rsplit('/',1)[-1])
                return self.json(dict(job) if job else {'error':'Unknown job'},200 if job else 404)
        if path.startswith('/api/'):
            return self.json({'error':'Unknown endpoint'},404)
        return super().do_GET()

    def do_POST(self):
        endpoint=urlsplit(self.path).path
        if endpoint not in {'/api/collect','/api/research'}:
            return self.json({'error':'Unknown endpoint'},404)
        # A custom same-origin header prevents another website from submitting jobs.
        origin=self.headers.get('Origin')
        host=self.headers.get('Host')
        if self.headers.get('X-FINN-Request')!='local' or (origin and urlsplit(origin).netloc!=host):
            return self.json({'error':'Same-origin FINN request required'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=4096:
                raise ValueError('Invalid request size')
            payload=json.loads(self.rfile.read(length))
            if not isinstance(payload,dict):
                raise ValueError('Request must be a JSON object')
            ticker=str(payload.get('ticker','')).strip().upper()
            if not re.fullmatch(r'[A-Z0-9][A-Z0-9&_.-]{0,39}',ticker):
                raise ValueError('Invalid NSE ticker')
            if endpoint=='/api/research':
                question=payload.get('question','')
                scope=payload.get('scope','auto')
                period=payload.get('period','all')
                if not isinstance(question,str) or not 3<=len(question.strip())<=300:
                    raise ValueError('Question must contain between three and three hundred characters')
                if scope not in ('auto','all','earnings','annual'):
                    raise ValueError('Invalid document scope')
                if not isinstance(period,str) or not re.fullmatch(r'all|latest4|Q[1-4] FY[0-9]{4}',period):
                    raise ValueError('Invalid reporting period')
                payload={'ticker':ticker,'question':question.strip(),'scope':scope,'period':period}
        except (ValueError,TypeError) as exc:
            return self.json({'error':str(exc)},400)
        with LOCK:
            kind='research' if endpoint=='/api/research' else 'collect'
            active=[(key,job) for key,job in JOBS.items() if job['status'] in ('queued','running')]
            for key,job in active:
                if job.get('kind','collect')==kind and (job.get('request')==payload if kind=='research' else job['ticker']==ticker):
                    return self.json({'job_id':key,**job},202)
            if len(active)>=3:
                return self.json({'error':'Three jobs are already active; retry after one finishes.'},429)
            job_id=uuid.uuid4().hex
            # Retain a bounded set of completed jobs for polling clients.
            for key in list(JOBS):
                if len(JOBS)<60:
                    break
                if JOBS[key]['status'] not in ('queued','running'):
                    del JOBS[key]
            JOBS[job_id]={'ticker':ticker,'kind':kind,'status':'queued','request':payload if kind=='research' else {'ticker':ticker}}
            if kind=='research':
                MODEL_POOL.submit(run_research,job_id,payload)
            else:
                POOL.submit(run_job,job_id,ticker)
            return self.json({'job_id':job_id,**JOBS[job_id]},202)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=int(os.environ.get('PORT','8000')))
    parser.add_argument('--host',choices=['127.0.0.1','0.0.0.0'],default='127.0.0.1')
    args=parser.parse_args()
    print(f'FINN research server: http://{args.host}:{args.port}',flush=True)
    try:
        ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        POOL.shutdown(wait=False,cancel_futures=True)
        MODEL_POOL.shutdown(wait=False,cancel_futures=True)


if __name__=='__main__':
    main()
