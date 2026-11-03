#!/usr/bin/env python3
"""Export project-scoped visible Codex conversations with credential redaction."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
from gemini_provider import configuration

ROOT=Path(__file__).resolve().parents[1]


def sanitize(text,secrets=()):
    for secret in sorted(set(secrets),key=len,reverse=True):
        if len(secret)>=12:
            text=text.replace(secret,'[REDACTED CREDENTIAL]')
    if re.search(r'Active file:\s*[^\n]*\.env',text):
        text=re.sub(r'(## Active selection of the file:\s*\n).*?(?=\n## Open tabs:|\n## My request:|\Z)',r'\1[REDACTED CREDENTIAL-FILE SELECTION]',text,flags=re.S)
    text=re.sub(r'\b(?:AIza[A-Za-z0-9_-]{25,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}|Q\.[A-Za-z0-9_-]{20,})','[REDACTED CREDENTIAL]',text)
    text=re.sub(r'(GEMINI_API_KEY\s*=\s*)[A-Za-z0-9_.-]{12,}',r'\1[REDACTED CREDENTIAL]',text)
    return text


def visible_messages(records):
    messages=[]
    for record in records:
        if record.get('type')!='response_item':
            continue
        payload=record.get('payload',{})
        if payload.get('type')!='message':
            continue
        role=payload.get('role')
        if role!='user' and not (role=='assistant' and payload.get('phase') in ('commentary','final_answer')):
            continue
        parts=payload.get('content',[])
        text='\n'.join(p['text'] for p in parts if isinstance(p,dict) and p.get('type') in ('text','input_text','output_text') and isinstance(p.get('text'),str))
        if text.strip():
            messages.append({'role':role,'timestamp':record.get('timestamp'),'text':text})
    return messages


def export(session_directory,project):
    sources=[];messages=[]
    for path in sorted(session_directory.rglob('*.jsonl')):
        raw=path.read_bytes()
        lines=raw.decode('utf-8').splitlines()
        if not lines:
            continue
        try:
            first=json.loads(lines[0])
        except ValueError:
            continue
        cwd=first.get('payload',{}).get('cwd')
        if not cwd or Path(cwd).resolve()!=project.resolve():
            continue
        records=[]
        for line in lines[1:]:
            try:records.append(json.loads(line))
            except ValueError:continue
        current=visible_messages(records)
        messages.extend(current)
        sources.append({'filename':path.name,'sha256':hashlib.sha256(raw).hexdigest(),'visible_message_count':len(current)})
    if not sources:
        raise ValueError('No local session logs match this project directory; add actual conversation exports manually.')
    secrets=[configuration().get('GEMINI_API_KEY','')]
    # Credential selections may be only a fragment of a key, or an older key.
    for message in messages:
        if re.search(r'Active file:\s*[^\n]*\.env',message['text']):
            match=re.search(r'## Active selection of the file:\s*\n(.*?)(?=\n## Open tabs:|\n## My request:|\Z)',message['text'],re.S)
            if match:
                secrets.extend(re.findall(r'[A-Za-z0-9_.-]{12,}',match.group(1)))
    output=['# Actual AI build conversation export','', 'This file exports visible user and assistant messages from the local Codex session for this project. It is an actual conversation export, not a reconstructed development narrative. Credentials and credential-file selections are redacted. Screenshots, tool arguments/outputs, internal reasoning and runtime metadata are omitted. Source code and reproducible checks are in the repository. Other AI tools or conversations, if used, must be added separately.','']
    for message in messages:
        output.extend([f'## {message["role"].title()} · {message["timestamp"]}','',sanitize(message['text'],secrets),''])
    text='\n'.join(output)
    if any(secret and len(secret)>=12 and secret in text for secret in secrets):
        raise ValueError('Credential redaction check failed; export was not saved.')
    directory=ROOT/'docs'
    (directory/'AI_BUILD_HISTORY.md').write_text(text)
    manifest={'exported_at':datetime.now(timezone.utc).isoformat(),'source':'Local project-scoped Codex JSONL sessions','sources':sources,'message_count':len(messages),'first_message':messages[0]['timestamp'] if messages else None,'last_message':messages[-1]['timestamp'] if messages else None,'redacted':True,'omissions':['Credentials and credential-file selections','Images','Tool arguments and outputs','Internal reasoning and runtime metadata'],'export_sha256':hashlib.sha256(text.encode()).hexdigest()}
    (directory/'AI_BUILD_HISTORY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-directory',type=Path,default=Path.home()/'.codex/sessions')
    parser.add_argument('--project-root',type=Path,default=ROOT.parent if ROOT.name=='finn-site' else ROOT)
    args=parser.parse_args()
    manifest=export(args.session_directory,args.project_root)
    print(json.dumps({'messages':manifest['message_count'],'first_message':manifest['first_message'],'last_message':manifest['last_message'],'credential_redaction_checked':True}))
