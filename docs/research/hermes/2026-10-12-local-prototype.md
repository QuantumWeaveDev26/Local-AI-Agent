# Hermes local compatibility prototype — 12 October 2026

Question: can a pinned Hermes runtime satisfy our local inference, restart,
cancellation and project-file scope contract on the existing small-model profile?
The user explicitly delegated autonomous work. This is a throwaway compatibility
experiment, not a runtime replacement or implemented Hermes integration.

## Isolation and reproducibility

Pinned upstream `dce1e9b37581dd62e480a9064dc04a709c2940d3`, separate scratch checkout,
CPython 3.14.7 and `uv sync --frozen --no-default-groups`. Installed 67 locked core
packages in its own environment; our Python 3.12 virtual environment/dependencies
were not changed. Upstream metadata declares >=3.11,<3.15 as an installation bridge;
the lock/runtime targets Python >=3.14, so 3.12 is not a proven Hermes runtime.

Separate `HERMES_HOME`, fictional files/session database, no imported platform or
Windows state. Child environment excluded inherited credentials. Custom loopback
Ollama endpoint only; no fallback providers/MCP servers, memory/background review
disabled for baseline probes, title-generation disabled, auxiliary free_only true.
Python DNS/socket/HTTP guards rejected nonloopback destinations. These are probe
guardrails, not an OS egress sandbox for arbitrary subprocesses. No LLM terminal
tool was enabled and all file checks used explicitly owned fixture paths.

Ollama 0.40.2 and existing verified `qwen3:1.7b` weights; no new weights downloaded.
An explicit-context disposable tag was created from those same weights through
Ollama's local create API. After the probes, only that disposable tag was removed;
the original `qwen3:1.7b` model was verified still present. Raw fixtures, harness
and reports remain outside Git at
`/workspace/runtime/hermes-prototype-2026-10-12`. Source hashes and pinned links are
in [the catalog](2026-10-12-prototype-sources.json). No hosted inference, company
documents, billing changes, external messages or ModelArk keys were used.

## Actual results

| Probe | Observed outcome | What it establishes |
| --- | --- | --- |
| Hermes initialization at 8,192 | Rejected in 4.01 s: minimum 64,000 required; no HTTP calls | Our current 8K profile is rejected by this unmodified custom/Ollama route |
| Hermes initialization at 64,000 | Accepted in 1.82 s, zero enabled tools, no HTTP calls | Construction succeeds; not proof of actual served context |
| Short loopback chat | First response exactly `READY` in 11.43 s; later attempts returned `READY.` | Inference works, but exact-output compliance is inconsistent |
| Process-restart recall | First `STORED`, second process loaded two persisted messages and returned `RIVER42`; four stored messages | Basic SQLite session/replay wiring works with fictional state |
| Stream cancellation | Callback issued hard_interrupt after output began; result interrupted=true, completed=false | Interrupt path works for a no-tool local stream; tool rollback not tested |
| File dispatcher | Read inside cwd, read `../outside-sentinel.txt`, and write an absolute sibling path all succeeded | Local cwd is not equivalent to our approved Workspace root boundary |
| Context allocation, original tag | Hermes displayed/requested 64,000; Ollama `/api/ps` reported 4,096 | The displayed/configured window does not prove runtime allocation |
| Context allocation, explicit tag | Tag parameters contain num_ctx=64,000; request body options.num_ctx=64,000; actual loaded context 40,960 | Explicit model parameters increase allocation but still do not provide the requested 64K on this server/model |
| Existing platform reference | Native API returned `READY` in 2.90 s; requested and loaded context both 8,192 | Our current native path honors the measured small-context setting |

The file checks went through `model_tools.handle_function_call`, including normal
pre-dispatch hooks, with only read/write grants and scratch fixtures. No exploit or
upstream security defect is asserted: general coding tools can intentionally have
broader authority. Our application's project-only permission contract requires a
separate adapter/sandbox rather than treating cwd as a boundary.

Persistence used an actual SessionDB and a separate process on resume, not an
in-memory copy alone. The stream cancellation retained a partial response and
reported zero token counters; it does not establish zero provider consumption.
Client token/cost counters must never be a billing guard. Our absence of hosted
calls follows the explicit local endpoint/credential isolation, not cost_status.

## Resource and context evidence

Explicit-tag call: 10.84 s end-to-end, 562 prompt tokens, three completion tokens.
Ollama reported size 6,437,480,692 bytes (approximately 6.00 GiB), size_vram=0 and
context_length=40,960. Sampled peak Ollama process-tree RSS was 6,211,407,872 bytes
(5.78 GiB), Hermes process RSS 172,179,456 bytes (164 MiB). Earlier sampling omitted
the runner child and is not used as a model-memory estimate.

Native 8K reference allocation was 2,419,306,003 bytes (2.25 GiB), size_vram=0.
These are short CPU probes, not steady-state speed, long-context quality or GPU
measurements. Nothing here proves that a 64K profile fits the laptop's RTX 3050
6 GB, or that every 64K request can be processed accurately by these weights.

The pinned minimum-context check uses configured `_ollama_num_ctx`; its conversation
guard also examines that value, not an authoritative `/api/ps` allocation in these
probes. A robust adapter must verify the actual served context rather than satisfy
the startup guard by configuration alone. We did not patch upstream to bypass it,
rename Ollama as another provider, or raise the platform's default context.

## Decision and next implementation boundary

Keep our tested runtime as the current default. Hermes remains a candidate behind
an adapter, rather than replacing the platform or migrating user state now.
Useful reuse targets include session/FTS, compression, skills and cancellation,
but each must preserve project isolation and visible receipts.

Before production integration, require:

- Delegate file operations through our Workspace/ToolExecutor or a genuine bounded
  host sandbox; reject traversal/absolute/out-of-project paths before execution.
- Pin main and every auxiliary call to permitted local endpoints; no auto hosted
  fallback, inherited cloud secrets, hosted memory or default paid auxiliary lane.
- Validate loaded context and resource budget on the actual Windows/GPU target;
  explicit configuration is insufficient. Keep baseline identities unchanged.
- Map sessions/project IDs, cancellation/receipts and private export semantics;
  avoid two engines independently writing the same database.
- Evaluate real model-driven document tools, routing/coding failures, project-memory
  isolation and cancelled work before claiming parity with our product contract.

Those full tool/quality/project-memory cases remain unrun: the profile and scope
gaps already prevent declaring a compatible production foundation. Installation,
small local inference, restart recall and no-tool cancellation are verified Linux
results. No feature is marked complete merely because upstream documents it.
