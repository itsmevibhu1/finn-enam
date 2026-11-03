#!/usr/bin/env python3
"""Download official, checksum-verified local inference assets into ignored paths."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
from urllib.request import Request,urlopen
import zipfile

ROOT=Path(__file__).resolve().parents[1]
HEADERS={'User-Agent':'FINN-local-model-setup/0.1'}


def get_json(url):
    with urlopen(Request(url,headers=HEADERS),timeout=40) as response:
        return json.load(response)


def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as source:
        while chunk:=source.read(8*1024*1024):
            result.update(chunk)
    return result.hexdigest()


def download(url,path,expected_sha):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and digest(path)==expected_sha:
        print('Verified cached asset:',path.name,flush=True)
        return
    part=path.with_suffix(path.suffix+'.part')
    offset=part.stat().st_size if part.exists() else 0
    headers=dict(HEADERS)
    if offset:
        headers['Range']=f'bytes={offset}-'
    with urlopen(Request(url,headers=headers),timeout=120) as response:
        resumed=offset and response.status==206
        received=offset if resumed else 0
        last=received
        with part.open('ab' if resumed else 'wb') as destination:
            while chunk:=response.read(8*1024*1024):
                destination.write(chunk)
                received+=len(chunk)
                if received-last>=128*1024*1024:
                    print(path.name,f'{received/1024/1024:.0f} MiB downloaded',flush=True)
                    last=received
    if digest(part)!=expected_sha:
        raise ValueError(f'Checksum mismatch for {path.name}; partial asset preserved for inspection')
    part.replace(path)
    print('Checksum verified:',path.name,flush=True)


def main():
    if shutil.disk_usage(ROOT).free<8*1024**3:
        raise SystemExit('At least 8 GiB free disk is required for local setup.')
    release=get_json('https://api.github.com/repos/ggml-org/llama.cpp/releases/latest')
    assets=[a for a in release['assets'] if re.search(r'bin-ubuntu-x64\.(tar\.gz|zip)$',a['name']) and not re.search(r'cuda|vulkan|rocm|sycl',a['name'],re.I)]
    if not assets:
        for candidate in get_json('https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=20'):
            matches=[a for a in candidate['assets'] if re.search(r'bin-ubuntu-x64\.(tar\.gz|zip)$',a['name']) and not re.search(r'cuda|vulkan|rocm|sycl',a['name'],re.I)]
            if matches:
                release,assets=candidate,matches
                break
    if not assets:
        print('Available official release assets:',[a['name'] for a in release['assets']],flush=True)
        raise SystemExit('No official CPU-compatible Ubuntu x64 release asset found.')
    asset=assets[0]
    archive_sha=(asset.get('digest') or '').removeprefix('sha256:')
    if not re.fullmatch('[0-9a-f]{64}',archive_sha):
        raise SystemExit('Official release does not provide a SHA-256 digest; refusing an unverified runtime.')
    model=get_json('https://huggingface.co/api/models/Qwen/Qwen3-4B-GGUF?blobs=true')
    file=next(s for s in model['siblings'] if s['rfilename']=='Qwen3-4B-Q4_K_M.gguf')
    model_sha=file['lfs']['sha256']
    runtime=ROOT/'.tools/llama'/release['tag_name']
    archive=ROOT/'.tools/llama'/asset['name']
    print('Runtime:',release['tag_name'],asset['name'],flush=True)
    download(asset['browser_download_url'],archive,archive_sha)
    runtime.mkdir(parents=True,exist_ok=True)
    if archive.name.endswith('.zip'):
        with zipfile.ZipFile(archive) as source:
            for entry in source.infolist():
                if not (runtime/entry.filename).resolve().is_relative_to(runtime.resolve()):
                    raise ValueError('Archive contains an unsafe path')
            source.extractall(runtime)
    else:
        with tarfile.open(archive) as source:
            source.extractall(runtime,filter='data')
    binaries=list(runtime.rglob('llama-server'))
    if not binaries:
        binaries=list(runtime.rglob('llama'))
    if not binaries:
        raise SystemExit('Runtime archive has no inference executable.')
    binary=binaries[0]
    binary.chmod(binary.stat().st_mode|0o111)
    model_path=ROOT/'.models'/file['rfilename']
    download('https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/main/'+file['rfilename'],model_path,model_sha)
    lock={'model_repository':'Qwen/Qwen3-4B-GGUF','model_revision':model['sha'],'model_filename':file['rfilename'],'model_sha256':model_sha,'model_relative_path':str(model_path.relative_to(ROOT)),'llama_release':release['tag_name'],'runtime_archive_sha256':archive_sha,'runtime_relative_path':str(binary.relative_to(ROOT)),'context_tokens':4096,'threads':4}
    (ROOT/'config/local_model.lock.json').write_text(json.dumps(lock,indent=2)+'\n')
    print('Local inference assets ready. No model API credentials were used.',flush=True)


if __name__=='__main__':
    main()
