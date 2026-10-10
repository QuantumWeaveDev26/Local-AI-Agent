#!/usr/bin/env bash
set -euo pipefail
runtime_root=/workspace/runtime
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_MODELS="$runtime_root/models"
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_NO_CLOUD=1
if curl -fsS --max-time 2 http://127.0.0.1:11434/api/version >/dev/null; then
    exit 0
fi
nohup "$runtime_root/ollama/bin/ollama" serve > "$runtime_root/ollama.log" 2>&1 < /dev/null &
for attempt in {1..30}; do
    if curl -fsS --max-time 2 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
        exit 0
    fi
    sleep 1
done
printf '%s\n' 'Ollama failed to start. Inspect /workspace/runtime/ollama.log.' >&2
exit 1
