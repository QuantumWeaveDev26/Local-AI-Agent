"""Cloud-only proxy-compatible import of official Qwen3 layers.

Downloads via verified HTTPS and checks registry SHA-256 digests before import.
Uses ollama create rather than editing Ollama's internal store or disabling checks.
Cached manifest/layers are retained to reproduce the exact model used here.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--tag',choices=['1.7b','4b'],default='4b')
args=parser.parse_args()
root=Path('/workspace/runtime/downloads')/f'qwen3-{args.tag}'
root.mkdir(parents=True,exist_ok=True)
manifest_path=root/'manifest.json'
if not manifest_path.exists():
    subprocess.run(['curl','-fsSL','--proto','=https','--proto-redir','=https',f'https://registry.ollama.ai/v2/library/qwen3/manifests/{args.tag}','-o',str(manifest_path)],check=True)
manifest=json.loads(manifest_path.read_text())
files={}
for layer in manifest['layers']:
    kind=layer['mediaType'].rsplit('.',1)[-1]
    destination=root/('model.gguf' if kind=='model' else kind+'.txt')
    expected=layer['digest'].split(':',1)[1]
    if not destination.exists() or destination.stat().st_size!=layer['size']:
        subprocess.run(['curl','-fsSL','--proto','=https','--proto-redir','=https',f"https://registry.ollama.ai/v2/library/qwen3/blobs/{layer['digest']}",'-o',str(destination)],check=True)
    assert hashlib.file_digest(destination.open('rb'),'sha256').hexdigest()==expected, f'{kind} checksum mismatch'
    print(kind,'official SHA256 verified',flush=True)
    files[kind]=destination
params=json.loads(files['params'].read_text())
modelfile=f'FROM {files["model"]}\nTEMPLATE """{files["template"].read_text()}"""\nLICENSE """{files["license"].read_text()}"""\n'
for key,value in params.items():
    for item in value if isinstance(value,list) else [value]:
        modelfile+=f'PARAMETER {key} {json.dumps(item)}\n'
(root/'Modelfile').write_text(modelfile)
subprocess.run(['/workspace/runtime/ollama/bin/ollama','create',f'qwen3:{args.tag}','-f',str(root/'Modelfile')],check=True)
