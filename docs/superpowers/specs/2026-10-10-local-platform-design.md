# Local AI agent platform V1

Build a local-first, Windows-compatible Python CLI. Agents, models and assigned tools
are records in SQLite, not specialist branches in application code. Starter agents
use the same registration API as future agents. No remote calls or deployments are
required. The current cloud machine is Linux without a GPU; its measurements cannot
establish Dell or HP performance.

## Architecture
A Registry validates model, agent and tool configurations. AgentFactory resolves
an enabled agent and its assigned capabilities. TaskService uses the selected model
through a provider-independent HTTP interface, runs a bounded tool loop, and records
messages, model runs, outputs, errors and tool calls. Manager routing requests a
validated agent ID from the currently enabled descriptions on each request. It never
routes by hard-coded specialist names. An optional fallback is explicitly configured
per agent and records each attempted model. Inference uses a cross-process file lock.

Use Ollama first, with OpenAI-compatible local endpoints as a second adapter.
Remote model URLs require an explicit opt-in. Secrets come from environment bindings;
never store their values in registries. Level 1 can read only; Level 2 can prepare
workspace files. Level 3 is rejected in V1. Tools require both assignment and level.

## Tools and workflow
TXT/Markdown/PDF/DOCX extraction runs inside an approved workspace. Resolve paths
and reject traversal, symlink escape and sensitive paths. PDF image OCR is outside V1;
empty extraction is an actionable error. Recruitment explicitly reads attached CV
and job description through the assigned document tool and validates an assessment
schema before saving a report. This avoids depending on a small model discovering
which attachments it must read. Generic agents also receive a bounded tool loop.
Developer tools include workspace reads/writes and read-only Git status/diff.
Arbitrary shell execution is outside V1. A test runner uses fixed, user-initiated
commands with explicit consent because repository tests execute arbitrary code.
No remote push, delete, deployment, email or financial tool is exposed.

## Delivery and evidence
CLI: initialize, models list/add, agents list/add/show/enable/disable,
tools list, run, recruit, task inspect, doctor and benchmark. Data lives under an
ignored data directory and documents under workspace. Schema and permission failures
are tested against real SQLite and filesystem state. HTTP adapters are tested with
a local protocol fixture; real Ollama inference, routing, tool calls and recruitment
are checked separately and their evidence is saved without calling fixtures models.
Benchmark one qwen3:1.7b model on the available CPU; offer qwen3:4b as an unbenchmarked
Dell candidate rather than downloading multiple models. Record load time, tokens/sec,
RAM, CPU and GPU metrics when present. Windows instructions audit the Dell and preserve
working installations. No Windows validation is claimed from Linux tests.
