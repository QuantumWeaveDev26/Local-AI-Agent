# Persistent workspace validation — 10 October 2026

## User-host evidence

The user supplied Windows setup output from `D:\Projects\Local-AI-Agent`:
56 passed, 2 skipped in 22.31 seconds, initialized SQLite/workspace, Python 3.12.10,
Windows 11 build 26300, 15.23 GiB RAM, 793.21 GiB disk free, Ollama 0.35.1,
installed qwen3:1.7b. The script reached its final message after its READY inference
smoke check. This is user-provided evidence; cloud tools did not execute on Windows.

The skips cover unavailable symlink privileges and a literal `*` filename, which
Windows forbids. Hardware audit separately reported RTX 3050 Laptop GPU 6144 MiB,
driver 610.62. Benchmark quality/latency and actual GPU allocation remain pending
the user's `main.py benchmark` and `ollama ps` output. Setup success is not evidence
of general agent reasoning/code quality or guaranteed model fit.

## New milestone: cloud/Linux evidence

- Automated suite: 77 tests passed, including real SQLite persistence, concurrent
  idempotent submissions, scoped context/files, interrupted-job recovery,
  cancellation, live HTTP authority checks, upload/download and malformed inputs.
- An existing workspace test-runner defect reproduced with a same-size edit and
  unchanged timestamp: pytest reused stale passing bytecode. A fresh per-run
  cache fixes it without deleting user files. Regression now verifies failure.
- Optional Playwright/installed Chromium browser scenario passed against the actual
  loopback service and real qwen3:1.7b inference: project creation, READY answer,
  refresh without duplicate, follow-up remembering READY, upload/attachment,
  cancellation, activity view, session switching and 390 px viewport width.
- Browser automation dependencies were installed outside the repository under
  `/workspace/runtime/browser-tools`. They are not product dependencies.
- JavaScript syntax check passed. Wheel build succeeded and included all three
  static assets. No new product dependency or model download was required.
- A real service stop/restart preserved the three browser tasks and qwen3:1.7b
  returned READY when asked to recall the preceding answer after restart.
- Independent review found four important defects: rejected submissions locked
  editing; stale project responses mixed session controls; registry changes blocked
  accepted-key retries; redaction collapsed distinct payloads. Each reproduction
  failed first, then passed after the fix. An additional lost-response browser
  reproduction now reconciles the accepted key from persisted history without
  submitting another task. Chromium exercised all three recovery scenarios.

Deduplication stores SHA-256 identities of validated original payloads and opaque
request keys while retaining only redacted payload content. This avoids storing
credentials in queue content merely to compare requests. For databases from an
earlier workspace build that retained only redacted input, migration preserves
jobs and hashes the retained input; an original input that included redacted secrets
cannot be reconstructed and may conservatively reject a retry. Inspect existing
history before submitting again. Normal generated browser keys are unaffected.

The browser check uses an isolated validation data/workspace directory under
`/workspace/runtime/ui-validation`. Generated screenshots and databases are not
published with source. New Windows UI execution and transfer to another physical
computer remain unverified. Cancellation is cooperative and progress polling is
not token streaming. Cross-session retrieval/skills/workflow checkpoints remain
future capabilities; Hermes is a candidate to evaluate for those.
