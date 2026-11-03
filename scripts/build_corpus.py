"""Build lazy-loaded page-level primary-document corpora for browser retrieval."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from research_pipeline import document_quality, document_directory

ROOT=Path(__file__).resolve().parents[1]


def transcript_metadata(pages):
    text=re.sub(r'\s+',' ',' '.join(p['text'] for p in pages[:5]))
    if re.search(r'investor\s+AI\s+day|analyst\s+day',text,re.I):
        return {'event_type':'investor_event','reporting_period':None}
    if re.search(r'media\s+conference\s+call',text,re.I):
        return {'event_type':'media_conference','reporting_period':None}
    explicit=re.search(r'Q([1-4])\s*[,\s\'’]*(?:and\s+(?:annual|full.year)\s*)?FY\s*[\'’]?\s*(20\d{2}|\d{2})\b',text,re.I)
    if explicit:
        year=int(explicit.group(2))
        year=year+2000 if year<100 else year
        return {'event_type':'earnings_call','reporting_period':f'Q{explicit.group(1)} FY{year}'}
    ended=re.search(r'quarter\s+(?:and\s+year\s+)?ended\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+(20\d{2})',text,re.I)
    if ended:
        month=datetime.strptime(ended.group(1),'%B').month
        year=int(ended.group(2))+(month>=4)
        quarter=(month-4)%12//3+1
        return {'event_type':'earnings_call','reporting_period':f'Q{quarter} FY{year}'}
    return {'event_type':'other_company_call','reporting_period':None}


def chunks(text,limit=1400,overlap=180):
    text=re.sub(r'\s+',' ',text).strip()
    start=0
    while start<len(text):
        end=min(len(text),start+limit)
        if end<len(text):
            boundary=text.rfind(' ',start+limit//2,end)
            if boundary>start:
                end=boundary
        yield text[start:end]
        if end==len(text):
            break
        start=max(start+1,end-overlap)


def build():
    path=ROOT/'data/company_discovery.json'
    if not path.exists():
        return {}
    discovery=json.loads(path.read_text())
    static=ROOT/'dist' if (ROOT/'.openai/hosting.json').exists() else ROOT/'finn-site/dist'
    target=static/'corpora'
    target.mkdir(exist_ok=True)
    coverage={}
    for ticker,company in discovery['companies'].items():
        saved_rejections=[{'kind':d['kind'],'period':d['period'],'reason':d.get('quality',{}).get('reason',d.get('error','Unavailable source'))} for d in company.get('documents',[]) if d.get('status')=='failed' or d.get('quality',{}).get('usable') is False]
        docs=[]
        passages=[]
        rejected=[]
        for document in company.get('documents',[]):
            quality=document_quality(document,company.get('name',ticker))
            if not quality['reason'].startswith('Original PDF text is not downloaded'):
                document['quality']=quality
            if not quality['usable']:
                rejected.append({'kind':document['kind'],'period':document['period'],'reason':quality['reason']})
                continue
            manifest=json.loads((document_directory(document)/'manifest.json').read_text())
            doc_id=manifest['document_id']
            pages=json.loads((document_directory(document)/'pages.json').read_text())
            metadata=transcript_metadata(pages) if document['kind']=='transcript' else {'event_type':'annual_report','reporting_period':document['period']}
            label=metadata['reporting_period'] or metadata['event_type'].replace('_',' ').title()
            docs.append({'id':doc_id,'kind':document['kind'],'period':label,'directory_label':document['period'],'title':document['kind'].replace('_',' ').title()+' · '+label,'url':document['url'],'page_count':len(pages),'sha256':manifest['sha256'],'imported_at':manifest['imported_at'],'primary_via':document.get('discovered_via'),'identity_check':quality['reason'],**metadata})
            for page in pages:
                for i,chunk in enumerate(chunks(page['text'])):
                    passages.append({'id':f'{doc_id[:12]}-{page["pdf_page"]}-{i}','document':doc_id,'page':page['pdf_page'],'text':chunk})
        file=target/f'{ticker}.json'
        if not docs and file.exists() and any(d.get('status')!='failed' for d in company.get('documents',[])):
            # A source checkout includes the generated index, not ignored raw PDFs.
            # Keep that published index until original documents are re-collected.
            corpus=json.loads(file.read_text())
            docs=corpus['documents']
            passages=corpus['passages']
            rejected=saved_rejections
            print(ticker,'retained prebuilt index; raw source PDFs are not available locally')
        else:
            corpus={'ticker':ticker,'name':company.get('name',ticker),'documents':docs,'passages':passages,'generated_at':datetime.now(timezone.utc).isoformat(),'retrieval_method':'Keyword-ranked passages from imported primary PDFs. No generated financial conclusions.'}
            temporary=file.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(corpus,ensure_ascii=False,separators=(',',':'))+'\n')
            temporary.replace(file)
        coverage[ticker]={'ticker':ticker,'name':corpus['name'],'document_count':len(docs),'transcripts':sum(d['kind']=='transcript' for d in docs),'annual_reports':sum(d['kind']=='annual_report' for d in docs),'page_count':sum(d['page_count'] for d in docs),'passage_count':len(passages),'corpus_url':f'corpora/{ticker}.json','corpus_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'rejected':rejected,'discovery_url':company.get('discovery_url'),'status':'indexed' if docs else 'no_usable_documents'}
        print(ticker,f'{len(docs)} usable documents',f'{len(passages)} passages',f'{len(rejected)} rejected')
    (ROOT/'data/research_coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
    path.write_text(json.dumps(discovery,indent=2)+'\n')
    return coverage


if __name__=='__main__':
    build()
