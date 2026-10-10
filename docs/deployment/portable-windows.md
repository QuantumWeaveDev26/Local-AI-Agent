# Local deployment and moving between computers

## Current target and scope

The user's current personal laptop is the first deployment target. The user reports
an NVIDIA RTX 3050 Laptop GPU with 6 GB VRAM. The original handoff identifies this
machine as an HP Victus with 16 GB system RAM and a 477 GB SSD, previously close to
full. These are reported details; available memory, free disk, driver and GPU
offload must be measured again. The office Dell is unavailable and is a future
destination, not a prerequisite.

The cloud workspace remains available for source development and Linux testing.
It has no access to the personal Windows machine. Running the audit/setup commands
on that machine is the physical step needed to validate deployment there.

The full platform direction remains in the evolving roadmap: persistent chat,
projects, knowledge/research, memory, specialist coordination, resumable workflows,
skills, connectors, schedules, evaluation and optional modalities. It will be built
and verified in useful milestones. A proposed capability is not marked complete
merely because it appears in the roadmap.

## Portability contract

| Layer | What moves | What must be recreated or reviewed on the destination |
| --- | --- | --- |
| Source | The Git repository, pinned dependency lockfile and setup scripts | Python virtual environment and host-specific dependencies |
| Agent/model/tool configuration | Configuration exports or a consistent SQLite backup | Model availability, selected context sizes, host endpoints and tool scopes |
| User state | A consistent database backup and selected approved workspace files | Destination permissions, private-data access and path validity |
| Models | Required model identities; weights may be separately copied using runtime-supported methods | Install/import using supported Ollama procedures and verify availability |
| Credentials | Names of required bindings, without values in exports | Supply bindings securely on each host; no secrets committed to Git |
| Hardware/runtime | A selected host profile | Driver, CPU/GPU offload, concurrency, memory and latency measurements |

Application defaults already resolve `data/` and `workspace/` relative to the
repository rather than the caller's working directory. CLI `--data-dir` and
`--workspace` allow explicit locations. The default Ollama endpoint is loopback.
Cloud installation paths in `scripts/install-cloud.sh` belong to cloud setup;
they are not required by Windows application code.

Do not copy `.venv` between systems: it contains machine-specific executables and
paths. Model weights are separate from source; there is no need to download a
distinct model for each configured agent. Source portability is supported by the
current structure. Automated backup/restore, migration checks and host-profile
selection remain proposed work, not implemented commands.

## First installation on the current laptop

Install Git if necessary, or download the repository ZIP from GitHub and extract
it into a dedicated project directory. With Git available:

```powershell
New-Item -ItemType Directory -Force C:\Projects | Out-Null
Set-Location C:\Projects
git clone https://github.com/QuantumWeaveDev26/Local-AI-Agent.git
Set-Location Local-AI-Agent
New-Item -ItemType Directory -Force data | Out-Null
powershell -NoProfile -File scripts/audit-windows.ps1 |
    Tee-Object -FilePath data\hardware-audit.txt
```

Review current free RAM and disk before downloading models. Closing memory-heavy
applications helps; Windows and security services should remain running. The audit
is read-only and does not terminate processes or print environment variable values.

The current setup pulls the two existing measured baseline models, about 4 GB of
combined model downloads, plus dependencies and runtime overhead. Leave additional
free disk for installation, outputs and updates. Cloud measurements do not establish
GPU memory fit or speed on the laptop.

```powershell
powershell -NoProfile -File scripts/setup-windows.ps1
.\.venv\Scripts\python.exe main.py doctor
.\.venv\Scripts\python.exe main.py doctor --model router
ollama ps
.\.venv\Scripts\python.exe main.py benchmark --model local --output data\benchmark-personal-laptop.json
```

The setup's smoke request and the benchmark are meaningful inference checks.
`ollama ps` can show the loaded model's CPU/GPU allocation, but allocation alone does
not prove correct output. A startup process, installed-model list or open port is
not enough to validate a deployment.

Start with one inference worker and one loaded model. Multiple specialists can
share it; different model identities can load in sequence. Use context sizes and
quantization that pass actual memory/quality checks. CPU offload remains an option
when a model does not fit fully in VRAM, with a measured latency tradeoff. No claim
of unrestricted parallel model execution or frontier-model quality is made.

## Moving the current application and user state

1. Clone the reviewed repository on the new computer, preferably at the same
   version, and install its dependencies/runtime. Use the setup script for a fresh
   destination that has no existing private application state.
2. Stop application jobs before taking a transfer snapshot. Keep the source copy
   intact until destination validation is complete.
3. Create a consistent SQLite backup. Do not copy only an active `.sqlite` file
   while WAL writes may be pending. The example below uses SQLite's backup API:

   ```powershell
   .\.venv\Scripts\python.exe -c "import sqlite3; from pathlib import Path; p=Path('data/transfer'); p.mkdir(parents=True,exist_ok=True); src=sqlite3.connect('data/platform.sqlite'); dst=sqlite3.connect(p/'platform.sqlite'); src.backup(dst); dst.close(); src.close()"
   ```

4. Copy that backup and the selected `workspace/` files through a private transfer
   method. They are not GitHub source files. Keep the source database, transfer
   folder and private documents out of public Git history.
5. Stop destination jobs and back up any destination data before restoring. Restore
   into an unused data directory when possible; do not overwrite another user's
   database or workspace. A transferred registry may contain host-specific model
   endpoints or knowledge paths that need review.
6. Re-establish required model files and credential bindings using supported runtime
   setup. Model configuration IDs alone do not install weights. A trusted local
   model server on another LAN machine needs an explicitly configured authenticated
   transport; the current CLI only permits remote model endpoints via its explicit
   HTTPS opt-in.
7. Run tests, `doctor` for every enabled model, a real inference request and a
   representative document workflow. Verify private state and workspace access.

For a restored database under `data\restored` and the dedicated workspace:

```powershell
.\.venv\Scripts\python.exe main.py --data-dir data\restored --workspace workspace doctor
.\.venv\Scripts\python.exe main.py --data-dir data\restored --workspace workspace run "Reply with exactly READY. Do not use tools." --agent marketing
```

The database filename inside the selected data directory is `platform.sqlite`.
The SQLite backup API was smoke-checked on Linux and preserved the agent, model
and tool registry in a temporary database round trip. Data restoration using this
runbook has not yet been tested between two physical Windows machines. A future automated transfer bundle should include a schema
version, source version, file checksums, required models and a restore preview.

## Required future transfer checks

- Agent/tool/model definitions and user state survive a backup/restore round trip.
- A different checkout path does not silently expand file access or lose artifacts.
- A destination with a missing model reports it and preserves imported configuration.
- Schema incompatibility fails before modifying destination data.
- Credentials, virtual environments and unintended private files stay out of exports.
- Existing destination state remains intact unless a specific overwrite is authorized.
- Desktop sessions and resumable tasks acquire equivalent round-trip checks when
  those planned capabilities exist.

These checks preserve feature behavior across hosts. Performance and available
model quality will still depend on each machine's actual resources.
