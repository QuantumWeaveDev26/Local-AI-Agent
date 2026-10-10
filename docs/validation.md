# Validation evidence — 2026-10-10

This platform was built and exercised in the supplied **Linux cloud workspace**.
No connection to the Dell or HP was available. Windows installation scripts were
reviewed but not executed; Windows/NVIDIA performance is not established.

## What was executed

- Python 3.12.14, Git 2.52.0, Ollama 0.40.2; approximately 33.29 GiB host RAM.
- Official Ollama Linux archive verified against its release SHA-256:
  `726bee78706c281b0eeef00746efe51a044d71c592c3f0b195820707f31fdf04`.
- Official Qwen3 1.7B and 4B layers downloaded over HTTPS through the platform proxy;
  every GGUF/template/license/parameter digest matched the authoritative manifest.
- Ollama native pull initially failed because its redirect validation uses direct DNS.
  The supported `ollama create` import uses the verified official components instead.
  No TLS, signature, checksum or redirect verification was disabled.
- `bash scripts/install-cloud.sh` succeeded, including a repeat installation from the
  hash-locked requirements without changing manifests or lockfiles.
- Automated suite: **58 passed**, zero failed/skipped on Linux. Real SQLite,
  TXT/Markdown/PDF/DOCX, permission and filesystem behavior, subprocess CLI, and local
  HTTP protocol fixtures are exercised. The scripted provider is confined to tests.
- The independent review found and fixed Git wildcard expansion, Windows trailing
  dot/space aliases, dictionary-key secret redaction, Windows symlink privilege
  handling, and routing of agents with disabled tools. Regression failures were
  observed before fixes. The suite remained green afterward.

## Real local inference

[Initial workflow evidence](validation/local-workflows.json) preserves the first run with 1.7B.
PDF recruitment, native document-tool execution, developer file inspection and
marketing generation completed. Recruitment validated every assessment field and
saved a fictional candidate's report in the approved workspace.

The initial 1.7B Manager misrouted candidate evaluation to Developer. Adding a
capability rationale and enabling thinking did not resolve that sample. Those failed
attempts remain recorded in SQLite. This is a measured model-quality limitation,
not a passing check. No keyword fallback was used to conceal it.

The second model, **qwen3:4b**, passed all four dynamic routing probes:

| Request | Expected and observed |
| --- | --- |
| Evaluate this candidate for our developer role | Recruitment |
| Create a Meta Ads campaign strategy for a restaurant | Marketing |
| Inspect this codebase and explain the bug | Developer |
| Prepare a technical SEO audit and keyword plan | Newly registered SEO |

[Final routing evidence](validation/routing-cloud.json) records actual model runs, timing,
selected IDs and task IDs. The new SEO configuration was registered through the
normal API; no core orchestration branch was added. Disabled agents/tools and
explicit fallback are tested separately with deterministic fixtures. No failure
was induced in a real cloud provider because V1 needs no cloud credentials.

The final registry and fresh initialization assign 4B to Manager, while all
specialists share 1.7B. Native 4B tool execution repeatedly timed out at 300 seconds,
including trials of template/parser settings and a restarted backend. Those trials
did not establish a fix; the helper was removed and the official template restored.
No successful 4B tool execution or coding-quality improvement is claimed. OpenAI-compatible wire normalization is fixture-tested; an actual LM Studio,
vLLM or cloud endpoint was not tested.

## CPU benchmark

[Benchmark results and generated answers](validation/benchmark-cloud.json) retain the raw output
and manual quality annotations. This is one run per probe, not a reliability study.
There is no NVIDIA GPU; GPU/VRAM measurements are unavailable.

| 1.7B probe | Generation rate | Result |
| --- | ---: | --- |
| Arithmetic reasoning | 3.88 tokens/s | Correct: 90 km / 1.5 h = 60 km/h |
| Structured output | 8.84 tokens/s | Exactly the requested JSON values |
| Coding | 3.98 tokens/s | Manual review failed: only adjacent duplicates removed |
| Tool calling | 5.29 tokens/s | Correct document_read call and filename |

First-probe model load: approximately 4.54 seconds. Peak measured Ollama plus runner
RSS: approximately **2.33 GiB**. Host RAM/CPU sampling is included in the JSON; these
are shared-host observations, not dedicated-process CPU or precise device memory.
The original coding answer was not executed; it plainly retains a non-adjacent
repeat. A stronger Developer model was tried, but its native tool execution timed out.
Developer retains the verified 1.7B tool pipeline with this coding-quality limitation.

4B routing generated approximately 1.52–2.77 tokens/s in these probes, with a cold
load of 11.48 seconds and elapsed requests of 25.88–78.25 seconds. Correctness improved,
but CPU latency is high. These numbers cannot predict the Dell's GPU speed.

## Startup, persistence and next host

Ollama was stopped and restarted using `scripts/start-ollama.sh`. A real Marketing
request returned exactly `READY` with a completed persisted task, and the 4B model's
readiness check succeeded after restart. This verifies current-instance startup;
it does not prove restoration in a newly published cloud task.

`install_script`, `start_skill` and the two exact model-download domains were saved
in the environment configuration draft. Review and save these settings, then publish
the environment through the product. No publication was performed by this task.

On the Dell, run the README Windows audit/setup commands and save a hardware benchmark.
Until that physical step is complete, **Dell-hosted V1 is not validated**. Review every
business result and generated code; a functional pipeline does not establish model
reliability across unseen tasks. No web UI, scheduling, OCR, child-agent delegation,
unrestricted shell or external integrations are claimed.
