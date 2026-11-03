#!/usr/bin/env python3
"""Discover primary PDFs for any NSE ticker and build a page-level search index.

Screener is used only as a link directory. Its financial tables, commentary, and
AI summaries never enter the research corpus.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, urlopen

from import_document import import_document

ROOT=Path(__file__).resolve().parents[1]


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


def safe_primary(url,website_host):
    parsed=urlsplit(url)
    host=(parsed.hostname or '').lower()
    if parsed.scheme!='https' or parsed.username or parsed.password:
        return False
    domains=['bseindia.com','nseindia.com']
    if website_host:
        domains.append(website_host.removeprefix('www.'))
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
        if not safe_primary(primary_url,website_host):
            continue
        candidates.append({'ticker':ticker,'kind':kind,'period':period,'url':primary_url,'discovered_via':url,'publisher_status':'Exchange-hosted or company-domain link; document identity still needs review'})
    unique=list({(c['kind'],c['url']):c for c in candidates}.values())
    return {'ticker':ticker,'name':parser.name or ticker,'website_host':website_host,'discovery_url':url,'discovered_at':datetime.now(timezone.utc).isoformat(),'candidates':unique}


def download(candidate):
    try:
        with urlopen(Request(candidate['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=60) as response:
            final=response.url
            if not safe_primary(final,candidate.get('website_host','')):
                raise ValueError('Redirect does not end on an approved primary-source domain')
            content=response.read(40*1024*1024+1)
        if len(content)>40*1024*1024:
            raise ValueError('PDF exceeds 40 MB')
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


def collect(ticker,transcripts=4,annual_reports=1):
    result=discover(ticker)
    selected=[]
    for kind,limit in [('annual_report',annual_reports),('transcript',transcripts)]:
        selected.extend([dict(c,website_host=result['website_host']) for c in result['candidates'] if c['kind']==kind][:limit])
    with ThreadPoolExecutor(max_workers=3) as pool:
        result['documents']=list(pool.map(download,selected))
    for document in result['documents']:
        document['quality']=document_quality(document,result['name'])
    result['status']='ok' if any(d['quality']['usable'] for d in result['documents']) else 'no_documents_imported'
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tickers',nargs='+')
    parser.add_argument('--transcripts',type=int,default=4)
    parser.add_argument('--annual-reports',type=int,default=1)
    args=parser.parse_args()
    output=ROOT/'data/company_discovery.json'
    existing=json.loads(output.read_text()) if output.exists() else {'companies':{}}
    for ticker in args.tickers:
        try:
            result=collect(ticker,args.transcripts,args.annual_reports)
        except Exception as exc:
            result={'ticker':ticker.upper(),'status':'failed','error':str(exc),'documents':[]}
        existing['companies'][ticker.upper()]=result
        succeeded=sum(d['status']!='failed' for d in result.get('documents',[]))
        print(ticker,result['status'],f'{succeeded}/{len(result.get("documents",[]))} PDFs imported',result.get('error',''),flush=True)
        for document in result.get('documents',[]):
            print(' ',document['kind'],document['period'],document['status'],document.get('error',''),flush=True)
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(existing,indent=2)+'\n')
    return 0 if any(c.get('status')=='ok' for c in existing['companies'].values()) else 1


if __name__=='__main__':
    raise SystemExit(main())
