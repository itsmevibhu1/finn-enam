"""Copy reproducible application sources into the separate Sites checkout."""
from pathlib import Path
import shutil

root=Path(__file__).resolve().parents[1]
site=root/'finn-site'
if root==site or not site.exists():
    raise SystemExit('Run this helper from the original assignment workspace.')
for directory in ('scripts','tests','config','docs'):
    shutil.copytree(root/directory,site/directory,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
(site/'data').mkdir(exist_ok=True)
for name in ('research.json','market.json','announcements.json','source_index.json'):
    if (root/'data'/name).exists():
        shutil.copyfile(root/'data'/name,site/'data'/name)
for name in ('README.md','.gitignore'):
    shutil.copyfile(root/name,site/name)
print('Prepared source checkout with UI, pipeline, records, tests, and documentation. No credentials or raw assignment PDFs included.')
