param([string]$Model = 'qwen3:1.7b', [string]$RouterModel = 'qwen3:4b')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Assert-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE" }
}
# Reuse installations; winget verifies package artifacts and publisher metadata.
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Install Python 3.11+ from python.org, then rerun.' }
    winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements
    Assert-Exit 'Python installation'
    throw 'Open a new PowerShell so Python is on PATH, then rerun this script.'
}
python -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ is required'"
Assert-Exit 'Python version check'
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    python -m venv .venv
    Assert-Exit 'Virtual environment creation'
}
& .\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
Assert-Exit 'Dependency installation'
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Install Ollama from ollama.com/download/windows, then rerun.' }
    winget install --id Ollama.Ollama --exact --accept-package-agreements --accept-source-agreements
    Assert-Exit 'Ollama installation'
    throw 'Open a new PowerShell and launch Ollama, then rerun this script.'
}
# Keep one inference worker/model and disable cloud features for the V1 session.
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_NO_CLOUD = '1'
try { $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/version' }
catch {
    $null = Start-Process ollama -ArgumentList 'serve' -PassThru
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        try { $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/version'; $ready = $true; break } catch {}
    }
    if (-not $ready) { throw 'Ollama did not become ready in 30 seconds.' }
}
foreach ($tag in @($Model, $RouterModel) | Select-Object -Unique) {
    ollama pull $tag
    Assert-Exit "Model pull: $tag"
}
& .\.venv\Scripts\python.exe main.py init --model $Model --router-model $RouterModel
Assert-Exit 'Registry initialization'
New-Item -ItemType Directory -Force workspace | Out-Null
foreach ($file in @('candidate.txt','job-description.md')) {
    if (-not (Test-Path "workspace\$file")) { Copy-Item "examples\$file" "workspace\$file" }
}
& .\.venv\Scripts\python.exe -m pytest -q
Assert-Exit 'Tests'
& .\.venv\Scripts\python.exe main.py doctor
Assert-Exit 'Readiness check'
$smokeOutput = & .\.venv\Scripts\python.exe main.py run 'Reply with exactly READY. Do not use tools.' --agent marketing
Assert-Exit 'Local inference smoke test'
$smoke = ($smokeOutput -join "`n") | ConvertFrom-Json
if ($smoke.status -ne 'completed' -or $smoke.result.Trim() -ne 'READY') {
    throw 'Local inference did not return READY. Inspect task logs and restart Ollama with the documented settings.'
}
Write-Output 'Run main.py benchmark and the examples in README.md to validate inference on this hardware.'
