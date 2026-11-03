"""Copy reproducible application sources into the separate Sites checkout."""
from pathlib import Path
import json
import shutil

root=Path(__file__).resolve().parents[1]
site=root/'finn-site'
if root==site or not site.exists():
    raise SystemExit('Run this helper from the original assignment workspace.')
for directory in ('scripts','tests','config','docs'):
    shutil.copytree(root/directory,site/directory,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
(site/'data').mkdir(exist_ok=True)
for name in ('research.json','market.json','announcements.json','announcement_archive.json','source_index.json','company_discovery.json','research_coverage.json','announcement_eval.json'):
    if (root/'data'/name).exists():
        if name=='company_discovery.json':
            discovery=json.loads((root/'data'/name).read_text())
            for company in discovery['companies'].values():
                for document in company.get('documents',[]):
                    if document.get('directory'):
                        original=Path(document['directory'])
                        if original.is_absolute():
                            document['directory']=str(original.relative_to(root))
            (site/'data'/name).write_text(json.dumps(discovery,indent=2)+'\n')
        else:
            shutil.copyfile(root/'data'/name,site/'data'/name)
for name in ('README.md','.gitignore','.env.example','Dockerfile','.dockerignore','render.yaml'):
    shutil.copyfile(root/name,site/name)
print('Prepared source checkout with UI, pipeline, records, tests, and documentation. No credentials or raw assignment PDFs included.')
