# Local AI platform implementation plan

> Implement inline with superpowers:executing-plans and test-driven-development.

**Goal:** deliver a working configurable local agent CLI and recruitment vertical slice.
**Architecture:** SQLite Registry → AgentFactory → provider → bounded assigned tools.
**Tech Stack:** Python 3.11+, SQLite, httpx, Pydantic, pypdf, python-docx, filelock.
**Spec:** ../specs/2026-10-10-local-platform-design.md

## Global constraints
- Portable Windows/Linux; no cloud dependency or unrestricted execution.
- Level 1 read, Level 2 prepare; reject Level 3.
- Concurrency 1 across CLI processes; no hard-coded specialist routing.
- Never store API keys. Use an approved workspace, explicit capabilities, finite loops.

## Review focus
- Disabled/deleted agents and models must fail before invocation.
- Malicious document instructions cannot acquire tools or escape the workspace.
- Provider timeouts and malformed structured output must produce failed persisted tasks.
- Traversal, symlinks and sensitive files must fail even for Level 2.
- Fallback must be explicit, log attempts and never enable cloud implicitly.

## Task 1 — Registry and persistence
Files: app/config.py, app/core/schemas.py, app/core/registry.py, app/database.py,
tests/test_registry.py. Registry(db_path) exposes add_model(Model), add_tool(Tool),
add_agent(Agent), get/list/update operations. IDs are slug strings.
- [ ] Write tests: arbitrary agent/model registration, restart persistence, enable/disable,
      unknown tool/model, permission 3 and duplicate rejection.
- [ ] Run pytest tests/test_registry.py; expected missing module failure before implementation.
- [ ] Implement validated SQLite records with foreign references and timestamps.
- [ ] Run registry tests; expected all pass.

## Task 2 — Tools and providers
Files: app/tools/workspace.py, app/core/llm.py, tests/test_tools.py, tests/test_llm.py.
Workspace(root) exposes read(path), write(path,content), git_status(), git_diff().
LLM.chat(model,messages,tools=None,schema=None) returns normalized response and metrics.
- [ ] Write traversal, symlink, secret path, PDF/DOCX, permission and provider fixture tests.
- [ ] Watch them fail, implement scoped tool dispatch and HTTP adapters, rerun.
- [ ] Verify Ollama installation checksum, launch loopback service, pull one model.

## Task 3 — Execution and routing
Files: app/core/agent_factory.py, app/services/tasks.py, app/agents/defaults.py,
tests/test_tasks.py. Factory.load(id) resolves enabled config. TaskService.run(request,
agent_id=None,attachments=None,schema=None) returns persisted task; recruit(cv,jd) validates
assessment; route(request) uses live available descriptions.
- [ ] Write tests for dynamic agent discovery, bounded tools, persistence, errors, fallback,
      disabled capabilities and document workflow using scripted protocol fixtures.
- [ ] Run failing tests then implement and run the entire suite.
- [ ] Run actual inference, three routing probes, new specialist routing, document assessment.

## Task 4 — CLI, benchmark and reproducible setup
Files: app/main.py, main.py, scripts/, tests/test_cli.py, README.md, pyproject.toml,
requirements.lock, .env.example, examples/, docs/validation.md.
- [ ] Write CLI subprocess tests for init repeatability, registration, doctor, task inspection.
- [ ] Watch failures, implement commands and Windows audit/setup scripts.
- [ ] Benchmark the actual service; report CPU/GPU evidence with truthful limitations.
- [ ] Install from locked dependencies, run full suite and CLI smoke workflows.
- [ ] Save tested install_script/start_skill and required network domains in draft.
