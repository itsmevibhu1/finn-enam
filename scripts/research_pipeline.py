#!/usr/bin/env python3
"""Discover primary PDFs for any NSE ticker and build a page-level search index.

Screener is used only as a link directory. Its financial tables, commentary, and
AI summaries never enter the research corpus.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, urlopen

from import_document import import_document
from source_metadata import transcript_metadata, quarter_coverage, reporting_period, period_sort_key

ROOT=Path(__file__).resolve().parents[1]
DOWNLOAD_WORKERS=max(1,min(3,int(os.environ.get('FINN_DOWNLOAD_WORKERS','3'))))


class DirectoryParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.heading_tag=None
        self.heading=[]
        self.section=''
        self.name=''
        self.anchor=None
        self.links=[]
        self.context=''

    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs)
        if tag in ('h1','h2','h3'):
            self.heading_tag=tag
            self.heading=[]
        if tag=='a':
            self.anchor={'href':attributes.get('href',''),'text':'','section':self.section,'context':self.context[-180:]}

    def handle_data(self,text):
        clean=' '.join(text.split())
        if clean:
            self.context=(self.context+' '+clean)[-400:]
        if self.heading_tag:
            self.heading.append(text)
        if self.anchor is not None:
            self.anchor['text']+=text

    def handle_endtag(self,tag):
        if tag==self.heading_tag:
            title=' '.join(''.join(self.heading).split())
            if tag=='h1' and not self.name:
                self.name=title
            if tag in ('h2','h3'):
                self.section=title.lower()
            self.heading_tag=None
        if tag=='a' and self.anchor is not None:
            self.anchor['text']=' '.join(self.anchor['text'].split())
            self.links.append(self.anchor)
            self.anchor=None


def safe_primary(url,website_host,extra_hosts=()):
    parsed=urlsplit(url)
    host=(parsed.hostname or '').lower()
    if parsed.scheme!='https' or parsed.username or parsed.password:
        return False
    domains=['bseindia.com','nseindia.com']
    if website_host:
        domains.append(website_host.removeprefix('www.'))
    domains.extend(host.removeprefix('www.') for host in extra_hosts)
    return any(host==domain or host.endswith('.'+domain) for domain in domains)


def discover(ticker):
    ticker=ticker.strip().upper()
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9&_.-]{0,39}',ticker):
        raise ValueError('Invalid NSE ticker')
    url=f'https://www.screener.in/company/{quote(ticker,safe="")}/consolidated/'
    request=Request(url,headers={'User-Agent':'Mozilla/5.0'})
    with urlopen(request,timeout=30) as response:
        html=response.read(3*1024*1024).decode('utf-8')
    parser=DirectoryParser()
    parser.feed(html)
    website_host=''
    for link in parser.links:
        if link['text'].strip().lower()=='website':
            website_host=urlsplit(link['href']).hostname or ''
            break
    candidates=[]
    for link in parser.links:
        text=link['text'].lower()
        section=link['section']
        if 'annual report' in section and 'annual report' in text:
            kind='annual_report'
            year=re.search(r'20\d{2}',link['text'])
            period='FY'+year.group() if year else 'Period not established'
        elif 'concall' in section and text in ('transcript','transcripts'):
            kind='transcript'
            dates=re.findall(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+20\d{2}',link['context'],re.I)
            period=dates[-1] if dates else 'Period not established'
        else:
            continue
        primary_url=urljoin(url,link['href'])
        candidates.append({'ticker':ticker,'kind':kind,'period':period,'url':primary_url,'discovered_via':url,'primary_host_approved':safe_primary(primary_url,website_host),'publisher_status':'Document-link candidate; primary domain and PDF identity must be checked before indexing'})
    unique=list({(c['kind'],c['url']):c for c in candidates}.values())
    return {'ticker':ticker,'name':parser.name or ticker,'website_host':website_host,'discovery_url':url,'discovered_at':datetime.now(timezone.utc).isoformat(),'candidates':unique}


def download(candidate):
    try:
        if not safe_primary(candidate['url'],candidate.get('website_host',''),candidate.get('verified_hosts',[])):
            raise ValueError('Document host is not verified as a primary source')
        registry=ROOT/'data/company_discovery.json'
        if registry.exists():
            cached=json.loads(registry.read_text()).get('companies',{}).get(candidate['ticker'],{}).get('documents',[])
            for record in cached:
                if record.get('status')!='failed' and all(record.get(k)==candidate.get(k) for k in ('url','kind','period')) and (document_directory(record)/'original.pdf').exists():
                    return {**record,**candidate,'cache_hit':True}
        with urlopen(Request(candidate['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=60) as response:
            final=response.url
            if not safe_primary(final,candidate.get('website_host',''),candidate.get('verified_hosts',[])):
                raise ValueError('Redirect does not end on an approved primary-source domain')
            content=response.read(40*1024*1024+1)
        if len(content)>40*1024*1024:
            raise ValueError('PDF exceeds 40 MB')
        digest=hashlib.sha256(content).hexdigest()
        previous=ROOT/'data/documents'/candidate['ticker']/candidate['kind']/digest
        if (previous/'manifest.json').exists() and (previous/'original.pdf').exists():
            manifest=json.loads((previous/'manifest.json').read_text())
            if hashlib.sha256((previous/'original.pdf').read_bytes()).hexdigest()!=digest:
                raise ValueError('Cached original failed its content-hash check')
            return {**candidate,'status':'already_imported','directory':str(previous),'document_id':digest,'canonical_source_url':manifest['source_url'],'source_alias_of':manifest['source_url'] if candidate['url']!=manifest['source_url'] else None}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.pdf'
            path.write_bytes(content)
            result=import_document(SimpleNamespace(pdf=path,ticker=candidate['ticker'],kind=candidate['kind'],period=candidate['period'],source_url=candidate['url'],output=ROOT/'data/documents'))
        return {**candidate,**result}
    except Exception as exc:
        return {**candidate,'status':'failed','error':str(exc)}


def document_directory(document):
    directory=Path(document['directory'])
    return directory if directory.is_absolute() else ROOT/directory


def document_quality(document,company_name):
    if document.get('status')=='failed':
        return {'usable':False,'reason':document.get('error','Download failed')}
    path=document_directory(document)/'pages.json'
    if not path.exists():
        return {'usable':False,'reason':'Original PDF text is not downloaded on this machine; rerun the ticker pipeline.'}
    pages=json.loads(path.read_text())
    body=' '.join(p['text'] for p in pages)
    opening=' '.join(p['text'] for p in pages[:5]).lower()
    if document['kind']=='transcript' and (len(pages)<3 or len(body.split())<1000 or not re.search(r'transcript|conference call',body,re.I)):
        return {'usable':False,'reason':'Not a substantive transcript; may be an audio-recording notice or cover letter.'}
    if document['kind']=='annual_report' and (len(pages)<15 or 'annual report' not in opening):
        return {'usable':False,'reason':'Annual-report identity could not be established from the PDF.'}
    tokens=[word for word in re.findall(r'[a-z]+',company_name.lower()) if word not in {'ltd','limited','india','technologies','systems','the'}]
    if not any(token in opening for token in tokens):
        return {'usable':False,'reason':'Company identity did not match the opening PDF pages.'}
    return {'usable':True,'reason':'PDF content matches expected document type and a company-name token; extracted claims still require verification.','pages':len(pages),'words':len(body.split())}


def issuer_host_evidence(document):
    """Use explicit issuer-website statements, not every URL in an annual report."""
    pages=json.loads((document_directory(document)/'pages.json').read_text())
    evidence=[]
    for page in pages[:5]:
        text=re.sub(r'\s+',' ',page['text'])
        pattern=r'(?:website|company\s+at|web\s*site)\s*(?:of\s+the\s+company)?\s*(?:at)?\s*[:\-]?\s*((?:https?://|www\.)[a-z0-9.-]+)'
        for match in re.finditer(pattern,text,re.I):
            url=match.group(1)
            host=(urlsplit(url if '://' in url else 'https://'+url).hostname or '').removeprefix('www.')
            if re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}',host) and host not in {'localhost','example.com'}:
                evidence.append({'host':host,'source_url':document['url'],'pdf_page':page['pdf_page'],'basis':'Explicit issuer website statement in identity-checked annual report'})
    return list({e['host']:e for e in evidence}.values())


def discover_issuer_transcripts(company,hosts,max_pages=4):
    """Bounded navigation of verified issuer IR directories; never crawl news sites."""
    domains=list(dict.fromkeys(hosts+[company['website_host'].removeprefix('www.')]))
    queue=[(100,f'https://www.{host}/investors/') for host in domains if host]
    visited=set()
    documents=[]
    attempts=[]
    while queue and len(visited)<max_pages:
        queue.sort(key=lambda item:item[0],reverse=True)
        _,url=queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        if not safe_primary(url,company['website_host'],hosts):
            continue
        try:
            with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as response:
                if not safe_primary(response.url,company['website_host'],hosts):
                    raise ValueError('IR directory redirected outside verified domains')
                parser=DirectoryParser()
                parser.feed(response.read(4*1024*1024).decode('utf-8'))
            attempts.append({'url':url,'status':'ok'})
            for link in parser.links:
                target=urljoin(url,link['href']).split('#')[0]
                if not safe_primary(target,company['website_host'],hosts):
                    continue
                label=link['text']
                if re.search(r'transcript',label,re.I) and re.search(r'\.pdf(?:$|[?#])',target,re.I):
                    period=reporting_period(label+' '+urlsplit(target).path) or 'Issuer directory link'
                    documents.append({'ticker':company['ticker'],'kind':'transcript','period':period,'url':target,'discovered_via':url,'website_host':company['website_host'],'verified_hosts':hosts,'publisher_status':'Linked from verified issuer IR directory; PDF content still checked'})
                elif target not in visited and not re.search(r'\.(?:pdf|mp3|mp4|jpg|png)(?:$|[?#])',target,re.I):
                    hint=(label+' '+urlsplit(target).path).lower()
                    priority=0
                    if re.search(r'quarterly.results|financial.results|call.transcripts|earnings.transcripts',hint):
                        priority=90
                    elif re.search(r'disclosure.*(?:regulation|46)|regulation.*46',hint):
                        priority=85
                    elif re.search(r'Q[1-4]\s*FY\s*27',label,re.I):
                        priority=95
                    elif re.search(r'2026.27|2026.*quarter',hint):
                        priority=80
                    if priority:
                        queue.append((priority,target))
        except Exception as exc:
            attempts.append({'url':url,'status':'failed','error':str(exc)})
    return list({d['url']:d for d in documents}.values()),attempts


def collect(ticker,transcripts=4,annual_reports=1,max_candidates=12):
    if not 0<=transcripts<=8 or not 0<=annual_reports<=3 or not 1<=max_candidates<=24:
        raise ValueError('Collection limits out of range')
    result=discover(ticker)
    selected=[dict(c,website_host=result['website_host']) for c in result['candidates'] if c['kind']=='annual_report' and c['primary_host_approved']][:annual_reports]
    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        result['documents']=list(pool.map(download,selected))
    evidence=[]
    for document in result['documents']:
        document['quality']=document_quality(document,result['name'])
        if document['quality']['usable']:
            evidence.extend(issuer_host_evidence(document))
    hosts=sorted({e['host'] for e in evidence})
    result['issuer_host_evidence']=evidence
    eligible=[dict(c,website_host=result['website_host'],verified_hosts=hosts) for c in result['candidates'] if c['kind']=='transcript' and safe_primary(c['url'],result['website_host'],hosts)][:max_candidates]
    periods=[]
    attempted=0
    fallback_checked=False
    # Keep inspecting candidates when special events, duplicate quarters or notices
    # displace an earnings call in the directory's first four entries.
    while transcripts and not quarter_coverage(periods,transcripts)['complete']:
        if not fallback_checked and attempted>=min(6,len(eligible)):
            additions,attempts=discover_issuer_transcripts(result,hosts)
            result['issuer_directory_attempts']=attempts
            known={c['url'] for c in eligible}
            additions=[c for c in additions if c['url'] not in known]
            additions.sort(key=lambda c:(max([int(y) for y in re.findall(r'20\d{2}',c['url']+' '+c['period'])] or [0]),period_sort_key(c['period'])),reverse=True)
            eligible=(eligible[:attempted]+additions+eligible[attempted:])[:max_candidates]
            fallback_checked=True
        if attempted>=len(eligible):
            if fallback_checked:
                break
            continue
        batch=eligible[attempted:attempted+min(3,transcripts-len(set(periods)) if len(set(periods))<transcripts else 1)]
        with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
            documents=list(pool.map(download,batch))
        for document in documents:
            document['quality']=document_quality(document,result['name'])
            if document['quality']['usable']:
                pages=json.loads((document_directory(document)/'pages.json').read_text())
                document['call_metadata']=transcript_metadata(pages)
                periods.extend(document['call_metadata']['earnings_periods'])
        result['documents'].extend(documents)
        attempted+=len(batch)
    result['quarter_coverage']=quarter_coverage(periods,transcripts)
    result['unapproved_host_candidates']=len([c for c in result['candidates'] if not safe_primary(c['url'],result['website_host'],hosts)])
    result['status']='ok' if any(d['quality']['usable'] for d in result['documents']) else 'no_documents_imported'
    return result


def retain_collection(existing,ticker,result):
    """A transient collection failure must not erase last-known usable sources."""
    prior=existing['companies'].get(ticker)
    if result['status'] in ('failed','no_documents_imported') and prior and prior.get('documents'):
        prior['last_collection_attempt']={k:v for k,v in result.items() if k not in {'documents','candidates'}}
    else:
        existing['companies'][ticker]=result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tickers',nargs='+')
    parser.add_argument('--transcripts',type=int,default=4)
    parser.add_argument('--annual-reports',type=int,default=1)
    parser.add_argument('--add-transcript',help='Supplement a previously discovered company with a reviewed primary PDF URL')
    parser.add_argument('--discovered-via',help='Primary IR directory where the supplemental URL was found')
    parser.add_argument('--source-period',default='Reviewed issuer link')
    args=parser.parse_args()
    output=ROOT/'data/company_discovery.json'
    existing=json.loads(output.read_text()) if output.exists() else {'companies':{}}
    if args.add_transcript:
        if len(args.tickers)!=1 or not args.discovered_via:
            parser.error('--add-transcript requires one ticker and --discovered-via')
        ticker=args.tickers[0].upper()
        company=existing['companies'].get(ticker)
        if not company:
            parser.error('Discover this company before adding a supplemental document')
        hosts=[e['host'] for e in company.get('issuer_host_evidence',[])]
        if not safe_primary(args.discovered_via,company['website_host'],hosts):
            parser.error('The reviewed directory must be on a verified primary-source domain')
        candidate={'ticker':ticker,'kind':'transcript','period':args.source_period,'url':args.add_transcript,'discovered_via':args.discovered_via,'website_host':company['website_host'],'verified_hosts':hosts,'discovery_method':'Reviewed primary-directory link'}
        document=download(candidate)
        document['quality']=document_quality(document,company['name'])
        if not document['quality']['usable']:
            print('Supplement rejected:',document['quality']['reason'])
            return 1
        pages=json.loads((document_directory(document)/'pages.json').read_text())
        document['call_metadata']=transcript_metadata(pages)
        company['documents']=[d for d in company['documents'] if d['url']!=document['url']]+[document]
        periods=[p for d in company['documents'] if d.get('quality',{}).get('usable') for p in d.get('call_metadata',{}).get('earnings_periods',[])]
        company['quarter_coverage']=quarter_coverage(periods,args.transcripts)
        output.write_text(json.dumps(existing,indent=2)+'\n')
        print(ticker,'supplement indexed:',document['call_metadata']['earnings_periods'])
        return 0
    attempted_results=[]
    for ticker in args.tickers:
        try:
            result=collect(ticker,args.transcripts,args.annual_reports)
        except Exception as exc:
            result={'ticker':ticker.upper(),'status':'failed','error':str(exc),'documents':[]}
        attempted_results.append(result)
        retain_collection(existing,ticker.upper(),result)
        succeeded=sum(d['status']!='failed' for d in result.get('documents',[]))
        print(ticker,result['status'],f'{succeeded}/{len(result.get("documents",[]))} PDFs imported',result.get('error',''),flush=True)
        for document in result.get('documents',[]):
            print(' ',document['kind'],document['period'],document['status'],document.get('error',''),flush=True)
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(existing,indent=2)+'\n')
    return 0 if any(c.get('status')=='ok' for c in attempted_results) else 1


if __name__=='__main__':
    raise SystemExit(main())
