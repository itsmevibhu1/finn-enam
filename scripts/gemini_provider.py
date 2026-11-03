"""Gemini free-tier-eligible transport; credentials stay outside browser assets."""
from dataclasses import dataclass,field
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
FREE_ELIGIBLE_MODELS={'gemini-3.5-flash-lite'}
ENV_KEYS={'FINN_AI_PROVIDER','GEMINI_API_KEY','GEMINI_MODEL','FINN_GEMINI_DAILY_REQUEST_LIMIT'}


def configuration(root=None):
    """Read a small dotenv subset without executing or interpolating its values."""
    root=root or ROOT
    values={}
    path=root/'.env.local'
    if path.exists():
        for line in path.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith('#'):
                continue
            key,separator,value=line.partition('=')
            key=key.strip()
            if not separator or key not in ENV_KEYS:
                continue
            value=value.strip()
            if len(value)>=2 and value[0]==value[-1] and value[0] in {'"',"'"}:
                value=value[1:-1]
            values[key]=value
    for key in ENV_KEYS:
        if key in os.environ:
            values[key]=os.environ[key]
    return values


@dataclass
class Settings:
    api_key:str=field(repr=False)
    model:str='gemini-3.5-flash-lite'
    daily_limit:int=8


def settings(require_key=True):
    values=configuration()
    model=values.get('GEMINI_MODEL','gemini-3.5-flash-lite')
    if model not in FREE_ELIGIBLE_MODELS:
        raise ValueError('Only the configured free-tier-eligible Gemini model is allowed; paid-model fallback is disabled.')
    key=values.get('GEMINI_API_KEY','').strip()
    if require_key and (len(key)<12 or key.lower() in {'your_api_key_here','replace_me'}):
        raise ValueError('Create a Gemini API key in AI Studio and set GEMINI_API_KEY in the ignored .env.local file. Do not paste it into chat.')
    if '\r' in key or '\n' in key:
        raise ValueError('API key contains invalid whitespace')
    try:
        limit=int(values.get('FINN_GEMINI_DAILY_REQUEST_LIMIT','8'))
    except ValueError:
        raise ValueError('Daily request limit must be a whole number') from None
    if not 1<=limit<=20:
        raise ValueError('Daily request limit must be between one and twenty attempts')
    return Settings(key,model,limit)


def reserve_request(config,root=None):
    root=root or ROOT
    directory=root/'data/model_cache'
    directory.mkdir(parents=True,exist_ok=True)
    state_path=directory/'gemini_usage.json'
    with (directory/'gemini_usage.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        today=datetime.now(timezone.utc).date().isoformat()
        state=json.loads(state_path.read_text()) if state_path.exists() else {}
        count=state.get('attempts',0) if state.get('utc_date')==today else 0
        if count>=config.daily_limit:
            raise ValueError('Application daily Gemini request cap reached. Cached research and document search remain available.')
        state={'utc_date':today,'attempts':count+1,'limit':config.daily_limit}
        temporary=state_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state)+'\n')
        temporary.replace(state_path)


def complete(messages,schema):
    config=settings()
    system='\n'.join(m['content'] for m in messages if m['role']=='system')
    contents=[{'role':'model' if m['role']=='assistant' else 'user','parts':[{'text':m['content']}]} for m in messages if m['role']!='system']
    body={'systemInstruction':{'parts':[{'text':system}]},'contents':contents,'generationConfig':{'temperature':0.1,'maxOutputTokens':1536,'responseMimeType':'application/json','responseJsonSchema':schema}}
    reserve_request(config)
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{config.model}:generateContent'
    request=Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','x-goog-api-key':config.api_key},method='POST')
    try:
        with urlopen(request,timeout=90) as response:
            result=json.load(response)
    except HTTPError as exc:
        messages={400:'Gemini rejected the request format or model configuration.',401:'Gemini API key was not accepted.',403:'Gemini API access is not enabled for this key or project.',429:'Gemini rate limit or free-tier quota was reached; no paid fallback was attempted.'}
        raise ValueError(messages.get(exc.code,f'Gemini request failed with HTTP {exc.code}; no paid fallback was attempted.')) from None
    except (URLError,TimeoutError):
        raise ValueError('Could not reach Gemini or the request timed out. Authentication is unverified; no paid fallback was attempted.') from None
    candidates=result.get('candidates',[])
    if not candidates or candidates[0].get('finishReason') not in (None,'STOP'):
        raise ValueError('Gemini did not return a complete answer; no research draft was published.')
    text=''.join(p.get('text','') for p in candidates[0].get('content',{}).get('parts',[]) if not p.get('thought'))
    if not text.strip():
        raise ValueError('Gemini returned no answer text')
    return {'choices':[{'message':{'content':text}}],'usage':result.get('usageMetadata',{}),'model_version':result.get('modelVersion',config.model)}
