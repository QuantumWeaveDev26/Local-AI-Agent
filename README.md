# Local AI Agent Platform

A Python CLI for creating specialist agents from configuration. Agents share or
select different registered models, receive only explicitly assigned tools, and
persist execution history in SQLite. Ollama is the default local inference engine.
No ChatGPT Agent subscription or cloud API key is needed for local execution.

The entire codebase is in the repository root, `/workspace/Local-AI-Agent` in the
cloud. See the [folder map](docs/PROJECT_STRUCTURE.md) for source locations. On the
personal laptop, use a dedicated checkout such as `C:\Projects\Local-AI-Agent`; this cloud
session has not created or modified a Windows folder.

```text
Local-AI-Agent/
├── app/          # CLI, configurations, registries, tools and task execution
├── tests/        # Automated regression and integration tests
├── scripts/      # Windows/cloud setup, runtime startup and real-model checks
├── examples/     # Agent/model configs and fictional demonstration documents
├── docs/         # Design, implementation plan and validation evidence
├── data/         # Generated SQLite databases, logs and benchmarks (Git-ignored)
├── workspace/    # Approved agent inputs and outputs (Git-ignored)
├── main.py       # CLI entry point
├── pyproject.toml
└── requirements.lock
```

**Current validation:** automated tests exercise real SQLite/files/documents and
local HTTP protocol fixtures. See [validation evidence](docs/validation.md) for
real inference status. Windows/GPU benchmarks require execution on the target machine.

## Get the source

Clone this repository with Git, or use GitHub's **Code → Download ZIP** and extract
it into a dedicated project folder.

```powershell
New-Item -ItemType Directory -Force C:\Projects | Out-Null
Set-Location C:\Projects
git clone https://github.com/QuantumWeaveDev26/Local-AI-Agent.git
Set-Location Local-AI-Agent
```

Publishing a Codex cloud environment retains its workspace/setup. Source appears
on GitHub only after a Git commit and push. Model weights, private documents,
SQLite databases, local credentials and virtual environments are excluded by design.

## Windows on your current laptop

The current RTX 3050 6 GB personal laptop is the first deployment target. The
office Dell is a future destination and does not block development. Read the
[deployment and transfer guide](docs/deployment/portable-windows.md), then open
PowerShell in the checkout and run:

```powershell
powershell -NoProfile -File scripts/audit-windows.ps1
powershell -NoProfile -File scripts/setup-windows.ps1
.\.venv\Scripts\python.exe main.py benchmark --output data\benchmark-personal-laptop.json
.\.venv\Scripts\python.exe main.py run "Create a Meta Ads campaign strategy for a restaurant."
.\.venv\Scripts\python.exe main.py recruit candidate.txt job-description.md
```

The script reuses Python and Ollama, installs hash-verified Python dependencies,
starts Ollama when absent, and pulls two measured models: `qwen3:1.7b` for
specialist execution and `qwen3:4b` for Manager routing (about 4 GB combined).
A new installation may require opening a fresh PowerShell for PATH changes.
Do not weaken PowerShell policy globally; use the manual commands below if needed.

The 1.7B model misrouted a candidate assessment; 4B passed the four routing probes.
4B native tool execution repeatedly exceeded the 300-second CPU timeout, including
an unsuccessful template/parser configuration trial. Defaults retain the original
verified model templates and use 1.7B for tools. The 1.7B coding benchmark failed
manual quality review. Review generated code and business results; benchmark on the
actual target laptop before selecting a stronger execution model. Larger models may offload to RAM
and become slow; do not download them all.

The benchmark records host CPU/RAM, Ollama process RSS, load time, token throughput,
structured output and a tool-call probe. GPU reporting is a point-in-time snapshot
when `nvidia-smi` is present. Reasoning/coding outputs require human review.

If the Ollama tray application was already running, newly set concurrency/cloud
variables do not reconfigure that process. Quit it yourself and run `ollama serve`
in a PowerShell with these settings when you need them:

```powershell
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_NO_CLOUD = '1'
ollama serve
```

No Docker, administrator shell or GPU is required for the core CLI.

## Manual installation / Linux

Python 3.11+ is required (cloud validation uses Python 3.12). Install Ollama from
its official distribution. In the project directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
ollama serve                       # separate terminal, loopback only
ollama pull qwen3:1.7b
ollama pull qwen3:4b
.venv/bin/python main.py init
.venv/bin/python -m pytest -q
.venv/bin/python main.py doctor
```

On Windows, substitute `.venv\Scripts\python.exe` for `.venv/bin/python`.
Commands take global `--data-dir PATH`, `--workspace PATH`, and `--timeout SECONDS` before the subcommand.
By default, both directories are under this checkout and ignored by Git. `init`
is idempotent and never overwrites existing agent/model configs. Changing its
`--model` flag after initialization does not change existing model records.

For this Codex cloud workspace, `bash scripts/install-cloud.sh` refreshes dependencies
and verifies the pinned Ollama archive before extraction. `bash scripts/start-ollama.sh`
starts the retained runtime. The platform environment must allow Ollama model
registry/blob destinations. Scripts never reset or overwrite repository changes.
The cloud imports the official Qwen3 GGUF through verified HTTPS and checks
all registry SHA-256 digests, then uses `ollama create`. This avoids Ollama 0.40.2's
direct-DNS redirect check, which cannot resolve CDN hosts in the proxy-only container.
It preserves TLS and artifact verification. Cached manifest and layers pin the tested
model. Windows normally uses `ollama pull` directly.

An initial Ollama startup needs a writable user `.ollama` directory for its identity;
the cloud instance needed permission for that normal runtime file.

## Run tasks

Copy demonstration inputs into the approved workspace (without overwriting your files):

```bash
mkdir -p workspace
cp -n examples/candidate.txt examples/job-description.md workspace/
.venv/bin/python main.py run "Create a Meta Ads campaign strategy for a restaurant."
.venv/bin/python main.py run "Inspect this codebase and explain the bug."
.venv/bin/python main.py run "Summarize this candidate's experience" --agent recruitment --attach candidate.txt
.venv/bin/python main.py recruit candidate.txt job-description.md
```

`run` without `--agent` uses the Manager's semantic selection from live enabled
capability descriptions. `recruit` is a deterministic workflow selecting the named
recruitment agent (override with `--agent`); it loads both documents through assigned
tools, requests the validated assessment schema, and saves `workspace/reports/TASK_ID.json`.
Use `run` for Manager-routed recruitment tasks; `recruit` for validated reports.

PDF and DOCX are supported: put `candidate.pdf` in the workspace and pass that filename.
Scanned PDFs require OCR outside this V1. Oversized/empty/encrypted documents fail
with an actionable error. No silent truncation is used for document extraction.
Reports distinguish documented skills, gaps and questions; review all assessments
before any hiring decision. Demonstration profiles are fictional.

```bash
.venv/bin/python main.py task TASK_ID
.venv/bin/python main.py agents list
.venv/bin/python main.py models list
.venv/bin/python main.py tools list
```

This prepared cloud instance retains two benchmark candidates: `local` is
`qwen3:1.7b`, shared by specialists, and `router` is `qwen3:4b`, assigned to Manager.
Fresh Windows initialization uses the same two-model profile. CPU-only cloud inference is
slow; do not infer target GPU performance from these measurements.

CLI output contains the task ID, selected agent, model attempts, status, result and
error. Failed tasks return a nonzero exit code. Task inspection includes timestamps,
messages, durations, outputs, tool calls and errors. Audits store document content;
keep `data/` private and use only files you intend to give agents.

## Create any specialist without changing core code

```bash
.venv/bin/python main.py agents add examples/seo-agent.json
.venv/bin/python main.py agents show seo
.venv/bin/python main.py run "Plan a technical SEO audit for our restaurant website."
.venv/bin/python main.py agents disable seo
.venv/bin/python main.py agents enable seo
.venv/bin/python main.py agents update seo --permission 2 --tools document_read filesystem_write
```

Agent JSON includes `id`, `name`, `description`, `instructions`, `model_id`,
`fallback_model_id`, `permission_level`, `tools`, `settings`, `knowledge_sources`,
`parent_id`, and `enabled`. `knowledge_sources` are workspace-relative documents,
read through the assigned `document_read` tool. The `settings.thinking` boolean overrides Ollama thinking per agent. Other settings
and parent relationships are retained metadata; automatic memory retrieval or child delegation is not active.
Task history is durable memory, not automatic conversational context.

The registry/API can register more tool definitions, and trusted application plugins
can register their handlers with `ToolExecutor.register`. Agent JSON cannot install
executable handlers. A tool definition alone does not grant a capability.

## Multiple models and explicit fallback

```bash
ollama pull qwen2.5-coder:3b         # optional; only when you want to test this model
.venv/bin/python main.py models add examples/coder-model.json
.venv/bin/python main.py agents update developer --model coder
.venv/bin/python main.py agents update seo --fallback coder
```

Different agents can use different registry IDs; any number can share one model.
Fallback is attempted only after a provider failure and records both attempts. It
does not judge answer quality or repair invalid assessments. Update the agent JSON/API
to clear fallback (`fallback_model_id: null` through `Registry.update_agent`).

For an existing LM Studio/local OpenAI-compatible server, register:

```json
{"id":"studio","name":"LM Studio","provider":"openai_compatible",
 "model_name":"your-loaded-model","base_url":"http://127.0.0.1:1234/v1",
 "context_length":8192}
```

The protocol adapter is fixture-tested; LM Studio itself is not validated here.
Remote HTTPS endpoints require `--allow-remote-models`; that is a deliberate opt-in
that may send documents off-machine. Optional keys are referenced by environment
variable **name** using `api_key_env`; never embed keys in model JSON. `.env` is ignored
but is not automatically loaded. Provider feature support (tools/JSON schema) varies.

## Developer scope and permissions

- Level 1: explicitly assigned reads and read-only Git inspection.
- Level 2: assigned file creation/modification inside the approved workspace.
- Level 3: rejected in V1.

For Git tools, pass a dedicated repository whose root is the approved workspace:

```bash
.venv/bin/python main.py --workspace /path/to/approved/repo run "Inspect src/example.py for bugs" --agent developer
```

There is no agent-accessible arbitrary shell, push, delete or deployment tool. The
user can run fixed pytest against trusted code with an explicit consent flag:

```bash
.venv/bin/python main.py --workspace /path/to/trusted/repo test-workspace --trust-workspace-code
```

This executes code as your user; it is **not a sandbox**. Do not run tests after
unreviewed agent changes on a machine containing sensitive credentials. Agents cannot
set the consent flag themselves. Shell command, exit status and bounded output are
recorded under a task. Agent loops allow at most 8 rounds and 8 calls per response.
A file lock serializes model calls across processes sharing the same data directory;
Ollama is configured for one parallel request/loaded model. Independent data directories
or other clients can still submit requests; keep server concurrency low.

Workspace checks reject traversal, symlinks/junctions, Windows device/stream paths,
`.env`, Git internals, SSH keys and known credential directories. They are application
checks, not an OS isolation boundary. External processes must not mutate workspace
paths concurrently. Keep secrets/personal files out of approved workspaces. Logs
redact sensitive environment values and common bearer/API key formats; arbitrary
unidentified secrets cannot be reliably detected. SQLite has no encryption at rest.

## Scope

V1 delivers the configuration-driven foundation, CLI, persistence, dynamic routing,
document workflow and constrained developer file/Git tooling. It does not include
web UI, email/calendar/browser integrations, scheduling, unrestricted shell, OCR,
vector database, automated hiring decisions, agent self-creation, or multi-agent
collaboration. Provider/factory/tool interfaces leave room to add these deliberately.

## Research and roadmap

- [Published environment review](docs/validation/2026-10-10-published-environment-review.md)
- [Lyzr product and architecture research](docs/research/lyzr/2026-10-10-analysis.md)
- [Evolving platform roadmap](docs/roadmap/2026-10-10-evolving-platform.md)

The roadmap records proposed capabilities; the validation documents record what
has actually been tested. New ideas can extend and reprioritize the roadmap.
