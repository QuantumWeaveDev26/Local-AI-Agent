# Persistent assistant workspace

The user wants a general local assistant with conversation continuity and permitted
task execution, initially on their RTX 3050 6 GB Windows laptop, transferable to
other computers. This implements roadmap milestone 1; the wider vision remains open.

Extend the existing runtime rather than adopting a hosted framework or adding a
second agent engine. A local browser client uses a standard-library HTTP service,
SQLite projects/sessions/jobs, and the existing TaskService with bounded history.
One durable queue worker limits resource pressure. No additional product dependency.

## Contract

- Keep all current CLI commands and existing database records working.
- Projects own separate generated workspace directories. Sessions belong to one
  project. Recent completed user/assistant turns are included in routing and task
  execution: at most 12 messages and 12,000 characters, newest first selected,
  chronological in the prompt. History is conversation context, not lasting memory.
- A task submission with the same session/request key and identical payload returns
  the existing task. Reusing a key with different input fails without executing.
- Persist queued work, task receipts, results and errors. Refresh reconnects to job
  IDs. A single service process owns the web queue using a process lock. On restart,
  previously running jobs become interrupted; queued jobs run. Never automatically
  replay an action whose completion is uncertain.
- Cancellation is cooperative: check before/after inference and before each tool.
  It cannot interrupt an in-flight provider request or undo completed file writes.
- Users may upload TXT, MD, PDF and DOCX, maximum 5,000,000 decoded bytes per file.
  Reject traversal, links, sensitive paths and overwrites. Agents retain their
  assigned tool/permission checks. File downloads are scoped to a project.
- Bind to 127.0.0.1 only. Check Host, Origin and a per-start API token, reject
  cross-site API access, never enable CORS. Serve only allowlisted static assets.
  Display user/model/file data with textContent, with a restrictive CSP.
- UI: projects, conversations, specialist selector, attachments, composer, status,
  cancel, result, selected agent/model and expandable audit events, project files.
  Poll persisted progress; token streaming is outside this milestone.
- No external connectors, shell execution, model downloads, automatic retries,
  workflow checkpoints, retrieval memory or paid services in this milestone.

## Evidence

Use real temporary SQLite/filesystems and a test-only scripted inference boundary
to check restart, history isolation, duplicate submission, cancellation and files.
Exercise an actual HTTP listener for request guards and API behavior. Smoke-test
the browser and a real Ollama request separately. Cloud/Linux results are distinct
from the user's Windows baseline (56 passed, 2 skipped); new Windows UI behavior
requires their host check. Preserve source/private state separation on transfer.
