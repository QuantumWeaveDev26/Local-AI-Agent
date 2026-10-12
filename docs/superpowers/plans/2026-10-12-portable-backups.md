# Portable Backups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> inline, with one fresh-context whole-branch review after verification.

**Goal:** Transfer private platform state to a new path without losing history or
overwriting existing data.

**Architecture:** A bundle-format module validates ZIP paths, bounded checksums and
SQLite compatibility. A backup service stages consistent snapshots and exclusive
restores; the CLI dispatches these offline actions before normal initialization.

**Tech Stack:** Python >=3.11, SQLite, zipfile/hashlib/pathlib, filelock, Pydantic.

**Spec:** docs/superpowers/specs/2026-10-12-portable-backups-design.md

## Global Constraints

- Format version 1; 10,000 payloads, 512 MiB/file, 2 GiB total, 1 MiB manifest.
- No new dependencies, provider calls, paid resources or runtime replacement.
- Output ends `.localagent.zip`; never overwrite an existing output/destination.
- Preserve private approved state; exclude credentials/runtime/model directories.
- Explicit offline create/restore; refuse active service and running snapshots.
- Restored pending jobs become interrupted; remote models require reactivation.
- Existing checkout; Naveen-145119 <naveenreddy91590@gmail.com> commits.

## Review Focus

- A hostile bundle must not write outside staging or execute database triggers.
- Case aliases and Windows names must be rejected on every operating system.
- A failed restore must leave an existing destination and source bytes untouched.
- An imported queue must not execute tools when the restored service starts.
- Snapshot errors must remove only this command's own partial outputs.

### Task 1: Format, offline snapshot and inspection

**Files:** Create app/services/backup_format.py, app/services/backups.py,
tests/test_backups.py; modify .gitignore.

**Interfaces:** `create_bundle(data_dir: Path, workspace: Path, output: Path,
offline: bool = False) -> dict`; `inspect_bundle(bundle: Path) -> dict`.
Format exposes constants, portable-path validation, SQLite validation and staged
bundle validation; actual names are fixed in the implementation brief/ledger.

- [ ] Add real DB/workspace fixtures and failing snapshot/inspection tests: WAL
  rows preserved, hashes/bytes verified, exclusions, immutable output, active lock,
  running tasks, mutated source, path/schema/trigger/corruption/limit rejection.
- [ ] Run `.venv/bin/python -m pytest tests/test_backups.py -q`; expect missing API.
- [ ] Implement format checks and streaming offline creation/inspection.
- [ ] Run `.venv/bin/python -m pytest -q`; expect all tests passing; commit.

### Task 2: Restore with no overwrite or replay

**Files:** Modify app/services/backups.py, tests/test_backups.py.

**Interfaces:** Consumes staged validation from Task 1. Produces
`restore_bundle(bundle: Path, destination: Path, offline: bool = False) -> dict`.

- [ ] Add failing round-trip tests for different destination, context/files,
  interrupted queue, disabled remote model, existing destination, parent links,
  damaged archive and failed publishing cleanup.
- [ ] Run the targeted restore tests; expect missing restore API.
- [ ] Implement validate-first staging, exclusive destination and restore receipt.
- [ ] Run full pytest; expect all tests passing; commit.

### Task 3: CLI, documentation and release evidence

**Files:** Modify app/main.py, tests/test_cli.py, README.md, docs/progress.md,
docs/deployment/portable-windows.md; create deployment backup guide and validation.

**Interfaces:** CLI create/inspect/restore calls Task 1/2 APIs before initialization.

- [ ] Add failing subprocess tests for CLI round-trip, useful errors and no default
  state creation by inspection or invalid restore; run targeted tests RED.
- [ ] Add CLI dispatch and document private offline transfer with Windows commands.
- [ ] Run full pytest, actual create/inspect/restore and restored HTTP service smoke.
- [ ] Fresh whole-branch review; regression-test important fixes; publish source.

Self-review: the three tasks cover the format/snapshot, restore, and user entry
points. Host GPU and actual Windows transfer are intentionally distinct evidence.
