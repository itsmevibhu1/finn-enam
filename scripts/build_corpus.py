"""Build lazy-loaded page-level primary-document corpora for browser retrieval."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from research_pipeline import document_quality, document_directory
from source_metadata import transcript_metadata, quarter_coverage

ROOT=Path(__file__).resolve().parents[1]


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
        indexed_ids=set()
        for document in company.get('documents',[]):
            quality=document_quality(document,company.get('name',ticker))
            if not quality['reason'].startswith('Original PDF text is not downloaded'):
                document['quality']=quality
            if not quality['usable']:
                rejected.append({'kind':document['kind'],'period':document['period'],'reason':quality['reason']})
                continue
            manifest=json.loads((document_directory(document)/'manifest.json').read_text())
            doc_id=manifest['document_id']
            if doc_id in indexed_ids:
                continue
            indexed_ids.add(doc_id)
            pages=json.loads((document_directory(document)/'pages.json').read_text())
            metadata=transcript_metadata(pages) if document['kind']=='transcript' else {'event_type':'annual_report','reporting_period':document['period']}
            label=metadata['reporting_period'] or metadata['event_type'].replace('_',' ').title()
            docs.append({'id':doc_id,'kind':document['kind'],'period':label,'directory_label':document['period'],'title':document['kind'].replace('_',' ').title()+' · '+label,'url':document['url'],'page_count':len(pages),'sha256':manifest['sha256'],'imported_at':manifest['imported_at'],'primary_via':document.get('discovered_via'),'identity_check':quality['reason'],**metadata})
            for page in pages:
                section=next((s for s in metadata.get('sections',[]) if s['start_page']<=page['pdf_page']<=s['end_page']),None)
                for i,chunk in enumerate(chunks(page['text'])):
                    passages.append({'id':f'{doc_id[:12]}-{page["pdf_page"]}-{i}','document':doc_id,'page':page['pdf_page'],'text':chunk,'event_type':section['event_type'] if section else metadata['event_type'],'reporting_period':section['reporting_period'] if section else metadata.get('reporting_period')})
        quarter_state=quarter_coverage([p for d in docs for p in d.get('earnings_periods',[])])
        window=set(quarter_state['expected_from_latest_available'])
        archived={d['id'] for d in docs if d.get('earnings_periods') and not window.intersection(d['earnings_periods'])}
        docs=[d for d in docs if d['id'] not in archived]
        passages=[p for p in passages if p['document'] not in archived]
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
            corpus={'ticker':ticker,'name':company.get('name',ticker),'documents':docs,'passages':passages,'generated_at':datetime.now(timezone.utc).isoformat(),'retrieval_method':'Keyword-ranked passages from imported primary PDFs. No generated financial conclusions.','archive_document_count':len(archived)}
            previous=json.loads(file.read_text()) if file.exists() else None
            content=lambda value:{k:v for k,v in value.items() if k!='generated_at'}
            if previous and content(previous)==content(corpus):
                corpus=previous
            else:
                temporary=file.with_suffix('.json.tmp')
                temporary.write_text(json.dumps(corpus,ensure_ascii=False,separators=(',',':'))+'\n')
                temporary.replace(file)
        periods=[p for d in docs for p in d.get('earnings_periods',[])]
        coverage[ticker]={'ticker':ticker,'name':corpus['name'],'document_count':len(docs),'transcripts':sum(d['kind']=='transcript' for d in docs),'annual_reports':sum(d['kind']=='annual_report' for d in docs),'page_count':sum(d['page_count'] for d in docs),'passage_count':len(passages),'corpus_url':f'corpora/{ticker}.json','corpus_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'rejected':rejected,'discovery_url':company.get('discovery_url'),'status':'indexed' if docs else 'no_usable_documents','quarter_coverage':quarter_coverage(periods),'archive_document_count':corpus.get('archive_document_count',0)}
        print(ticker,f'{len(docs)} usable documents',f'{len(passages)} passages',f'{len(rejected)} rejected')
    (ROOT/'data/research_coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
    path.write_text(json.dumps(discovery,indent=2)+'\n')
    return coverage


if __name__=='__main__':
    build()
