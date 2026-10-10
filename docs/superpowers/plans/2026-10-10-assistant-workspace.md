# Persistent assistant workspace implementation plan

> **For agentic workers:** Use superpowers:executing-plans task-by-task inline.

**Goal:** Continue project conversations and inspect local agent tasks in a browser.

**Architecture:** Add SQLite session/job storage and a single worker around the
existing TaskService. A loopback HTTP API serves a dependency-free browser client.

**Tech Stack:** Python >=3.11, SQLite, stdlib HTTP, existing Pydantic/filelock, JS/CSS.

**Spec:** docs/superpowers/specs/2026-10-10-assistant-workspace-design.md

## Global constraints

- Existing CLI/database compatibility; 127.0.0.1 only; no new product dependencies.
- 12 messages/12,000 characters of completed history; 5,000,000 bytes per file.
- No automatic replay of running tasks; cooperative cancellation between actions.
- Use the existing checkout; commits by Naveen-145119 <naveenreddy91590@gmail.com>.
- Report Linux tests and actual Windows evidence separately.

## Review focus

- Concurrent duplicate submits must create one job; conflicting payloads fail.
- A queued follow-up sees the preceding completed turn at execution time.
- Crash after a write must not automatically replay that write.
- Cross-site requests and hostile file/model strings cannot gain browser authority.
- A running cancellation must prevent later tools while retaining completed receipts.

### Task 1: Durable sessions and execution

**Files:** Create app/services/sessions.py, app/services/jobs.py, tests/test_sessions.py;
modify app/services/tasks.py.

**Interfaces:** SessionStore(db, workspace) owns create_project(name),
create_session(project_id,title), submit(session_id,key,prompt,agent_id,attachments),
history(session_id), task(task_id), workspace(project_id), cancel(task_id).
JobWorker(store,registry,llm) exposes run_next(), start(), close().
TaskService.run gains optional task_id/history/cancelled arguments.

- [x] Write failing persistence, scope, idempotency, history, restart and cancellation
  tests. Assert real DB states, files and received inference context.
- [x] Run .venv/bin/python -m pytest tests/test_sessions.py -q; expect missing API.
- [x] Implement storage, additive schema, contextual runtime and queue recovery.
- [x] Run entire pytest suite; expect all tests green; commit deliverable.

### Task 2: Local HTTP interface

**Files:** Create app/web/server.py, app/web/__init__.py, tests/test_web.py;
modify app/main.py. Consumes SessionStore and JobWorker from Task 1.

**Interfaces:** create_server(store, registry, port=8765) returns HTTPServer with
token; serve --port --open-browser launches worker and loopback service.

- [x] Write failing live HTTP API and Host/Origin/token guard tests; assert project
  upload/download stays scoped, byte limits and collision errors, refresh returns
  existing job, static allowlist rejects unknown paths.
- [x] Run tests/test_web.py; expect missing server.
- [x] Implement API with strict JSON/body limits, static allowlist, CSP and auth.
- [x] Run entire pytest suite; expect green; commit deliverable.

### Task 3: Browser and release evidence

**Files:** Create app/web/static/index.html, app.js, style.css; modify README.md,
pyproject.toml, docs/progress.md, deployment/roadmap docs; add validation report.
Consumes the authenticated HTTP API; no alternative agent execution path.

- [x] Browser scenario first: create project/session, send, refresh, see status and
  answer, continue, select file and cancel; expect missing UI initially.
- [x] Implement accessible responsive client, stable request keys on retry and
  escaped textual events/results, package the static assets.
- [x] Run pytest, actual browser scenario, build/package asset check and a real
  Ollama HTTP task; expect saved result visible after service restart.
- [x] Independent final review, one regression-tested fix pass; record evidence,
  commit and publish source following prior user authorization.

Self-review: every spec contract maps to the owning storage/API/browser task.
