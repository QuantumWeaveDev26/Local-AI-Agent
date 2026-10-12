# File delivery verification — 13 October 2026

## Trigger and scope

On Windows, the Developer replied that `dedupe.py` and `test_dedupe.py` were
created, but the user found neither under the configured workspace. Visible task
activity showed the final model claim; complete raw host events were not supplied.
We do not claim the exact host inference cause is proven. The existing service
accepted any nonempty final answer as completed, with no required-artifact check.
A deterministic protocol fixture reproduces that gap independently of the model.

The bounded fix adds explicit, optional file requirements to the existing task
flow rather than guessing action intent from natural language. Required files
must have successful writes in this task, and their current bytes must match the
latest write. Filename syntax follows portable backup validation; at most eight
paths, 1024 characters each. Names changed by redaction are rejected, never silently
renamed. Empty requirements preserve legacy submission digests and queued payloads.

The browser and CLI accept requirements. Jobs retain them across restarts and
retries; failed requirements do not enter conversation context. Partial actions
are retained in receipts and never automatically undone or replayed. No schema or
agent/model configuration migration is needed. Ordinary task completion still
means response completion; its tool-action count is displayed separately.

## Evidence

Final Linux suite: **173 passed in 18.66 seconds**. JavaScript DOM harness:
**six passed**, using `node --test tests/web-artifacts.test.cjs`. Required local
HTTP tests and Node child-process tests ran with permission outside the sandbox;
assertions were not disabled. Independent review rechecked both fixes and found
no additional issues. This does not replace a physical Windows rerun.

- New service regression cases initially failed due to the missing API, then
  passed. They cover unsupported claims, existing files, missing/partial writes,
  changed/deleted bytes, false handler receipts, normalized paths and no code
  execution. Session/CLI/API regression cases failed before their integration.
- UI tests execute the shipped JavaScript in a DOM harness: submission, uncertain
  retry preserving agent/files, response-only evidence, file verification label,
  failed delivery and actual agent versus message role. Five failed against the
  previous JavaScript; six passed with the change. This is not a rendered-browser
  or physical Windows check.
- Review found two Important issues: redaction could rename a required filename,
  and Windows canonical filesystem casing could mismatch receipt keys. Added
  failing regressions, rejected altered names and resolved lookup keys through
  the same workspace path function. Casing is emulated on Linux, not measured on
  Windows. UTF-8 writes preserve LF bytes on all hosts without text-mode newline
  translation.
- A real isolated local Ollama `qwen3:1.7b` queued job wrote both requested files,
  verified their bytes/hashes and preserved requirements/results after reopening
  the database. Owned evidence remains outside Git at
  `/workspace/runtime/validation/file-delivery-2026-10-13/run-zbn5xj9o/evidence.json`.
  No company documents, hosted requests, credentials or paid resources were used.

## Limits and next validation

The real model's delivered dedupe code still only removed consecutive duplicates,
and its test module lacked an import. Delivery verification correctly proves file
bytes, not code correctness, requested test coverage or that the model performed
every action described in the prompt. Generated code was inspected but not run.
The explicit trusted-code test runner remains a separate user-controlled step.

Verification is at completion time and assumes no external concurrent workspace
mutation. Subsequent edits can invalidate the delivered contents. This is not an
OS sandbox, a complete semantic hallucination detector or an automatic repair loop.
The user must opt into required paths; historical ordinary tasks are not relabeled
as verified. Physical Windows rerun and a new UI delivery task remain pending.
