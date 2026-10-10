#!/usr/bin/env bash
set -euo pipefail
cd /workspace/Local-AI-Agent
runtime_root=/workspace/runtime
mkdir -p "$runtime_root/downloads" "$runtime_root/ollama" "$runtime_root/models"
if [[ ! -x "$runtime_root/ollama/bin/ollama" ]]; then
    curl -fsSL https://github.com/ollama/ollama/releases/download/v0.40.2/ollama-linux-amd64.tar.zst -o "$runtime_root/downloads/ollama-linux-amd64.tar.zst"
    curl -fsSL https://github.com/ollama/ollama/releases/download/v0.40.2/sha256sum.txt -o "$runtime_root/downloads/sha256sum.txt"
    python3 - <<'PY'
from pathlib import Path
import hashlib
root = Path('/workspace/runtime/downloads')
expected = next(line.split()[0] for line in (root/'sha256sum.txt').read_text().splitlines() if line.endswith('./ollama-linux-amd64.tar.zst'))
actual = hashlib.file_digest((root/'ollama-linux-amd64.tar.zst').open('rb'), 'sha256').hexdigest()
assert actual == expected, 'Ollama official checksum mismatch'
PY
    tar --zstd -xf "$runtime_root/downloads/ollama-linux-amd64.tar.zst" -C "$runtime_root/ollama"
fi
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
PIP_CACHE_DIR="$runtime_root/pip-cache" .venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python main.py init
bash scripts/start-ollama.sh
while IFS= read -r registered_model_id; do
    if .venv/bin/python main.py doctor --model "$registered_model_id" >/dev/null 2>&1; then
        continue
    fi
    registered_model_tag=$(.venv/bin/python - "$registered_model_id" <<'PYMODEL'
import sys
from app.database import Database
from app.core.registry import Registry
model = Registry(Database('data/platform.sqlite')).get_model(sys.argv[1])
if model.model_name not in ('qwen3:1.7b', 'qwen3:4b'):
    raise SystemExit('Use a supported verified import to install the registered model: ' + model.model_name)
print(model.model_name.split(':', 1)[1])
PYMODEL
)
    .venv/bin/python scripts/import-cloud-model.py --tag "$registered_model_tag"
done < <(.venv/bin/python - <<'PYMODELS'
from app.database import Database
from app.core.registry import Registry
for model in Registry(Database('data/platform.sqlite')).list_models(enabled_only=True):
    if model.provider == 'ollama':
        print(model.id)
PYMODELS
)
.venv/bin/python main.py doctor
# Model files are retained; processes must restart after restoring a snapshot.
# No tracked files or lockfiles are modified.
