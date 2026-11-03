#!/usr/bin/env python3
"""Run the downloaded CPU model on loopback only."""
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
lock=json.loads((ROOT/'config/local_model.lock.json').read_text())
binary=ROOT/lock['runtime_relative_path']
model=ROOT/lock['model_relative_path']
environment=dict(os.environ)
environment['LD_LIBRARY_PATH']=str(binary.parent)+(':'+environment['LD_LIBRARY_PATH'] if environment.get('LD_LIBRARY_PATH') else '')
arguments=[str(binary),'-m',str(model),'--host','127.0.0.1','--port','8081','--ctx-size',str(lock['context_tokens']),'--threads',str(lock['threads']),'--parallel','1','--batch-size','128','--ubatch-size','128','--alias','finn-local','--jinja']
if binary.name=='llama':
    arguments.insert(1,'serve')
print('Local model server: http://127.0.0.1:8081 · CPU only · no API bill',flush=True)
raise SystemExit(subprocess.call(arguments,env=environment))
