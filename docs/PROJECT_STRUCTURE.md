# Codebase location and folder map

The cloud checkout is **`/workspace/Local-AI-Agent`**. All application source and
project-owned setup scripts are inside this Git repository. Nothing was created
on the Dell or HP by this cloud session. A suitable Windows checkout destination
is `C:\Projects\Local-AI-Agent`.

| Location | Responsibility |
| --- | --- |
| `main.py` | Run the CLI from the repository root |
| `app/main.py` | CLI commands, readiness checks and benchmarking |
| `app/config.py` | Default project data/workspace locations |
| `app/database.py` | SQLite schema, durable task events and secret redaction |
| `app/core/schemas.py` | Validated agent, model, tool and assessment definitions |
| `app/core/registry.py` | Generic agent/model/tool configuration registration |
| `app/core/agent_factory.py` | Resolve enabled agents and capabilities |
| `app/core/llm.py` | Ollama/OpenAI-compatible HTTP adapters and inference lock |
| `app/agents/defaults.py` | Starter agents registered as normal configurations |
| `app/tools/workspace.py` | Approved file/document/Git tools and permission checks |
| `app/services/tasks.py` | Dynamic Manager routing, tool loop, recruitment workflow |
| `tests/` | Automated tests with temporary databases/workspaces and HTTP fixtures |
| `scripts/` | Installation, startup, Windows audit and actual inference validation |
| `examples/` | Configurable specialist/model examples and fictional inputs |
| `docs/superpowers/` | Design specification and implementation plan |
| `docs/validation.md` | Human-readable validation results and known limitations |
| `docs/validation/` | Benchmark/workflow evidence and publication review |
| `docs/research/` | Source-linked external product and architecture research |
| `docs/roadmap/` | Evolving product direction and proposed milestones |
| `data/` | Generated SQLite/audit/benchmark files; ignored by Git |
| `workspace/` | Explicitly approved input/output files; ignored by Git |
| `.venv/` | Project Python dependencies; ignored by Git |

Ollama binaries, model weights and download caches live separately at
`/workspace/runtime`. They are environment dependencies, not application source.
The original pasted request remains under `/workspace/attachments` as an uploaded
attachment, not inside the codebase. Source files are not spread across these
runtime/attachment folders.

Run project commands from `/workspace/Local-AI-Agent`, using `.venv/bin/python` in
cloud or `.venv\Scripts\python.exe` on Windows. Read the root README for setup and
workflow commands. The app defaults to project-relative data paths even if launched
from another directory.
