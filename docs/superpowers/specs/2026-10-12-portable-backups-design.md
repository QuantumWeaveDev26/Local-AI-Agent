# Portable private-state backups

The user wants autonomous development and transfers between computers. The old
external disk became unavailable, and the latest Windows cleanup recovered space
but removed Docker. Source cloning cannot recover private conversations or files.
This architectural milestone adds a local, Docker-independent transfer bundle to
the existing platform. The user explicitly delegated implementation and routine
publication; no additional design-approval handoff is needed.

## Approach and boundaries

Use Python's SQLite backup API and a ZIP containing an integrity manifest. A raw
directory copy risks losing WAL writes; a full-machine/runtime export mixes private
state with host-specific executables, credentials and model weights. This bundle
contains platform state and approved workspace files, with model identities rather
than model binaries. No new dependencies, provider calls, paid resources or runtime
replacement. Hermes feasibility remains a separate next experiment.

Commands: `backup create --output PATH --offline`, `backup inspect PATH`, and
`backup restore PATH --destination NEW_DIRECTORY --offline`. The existing global
`--data-dir` and `--workspace` choose the source for create. Inspection and restore
must dispatch before the CLI creates or initializes its default database/workspace.
The explicit offline flag acknowledges that all CLI writers and external editors
must be stopped. The service lock additionally refuses a running browser service.

## Bundle contract

- Python >=3.11; standard library plus the existing filelock/Pydantic dependencies.
- Output filename ends in `.localagent.zip`, ignored by Git. Never overwrite an
  existing output or restore destination, including empty directories.
- Format version 1; `manifest.json`, `data/platform.sqlite`, and `workspace/PATH`
  regular-file members only. Manifest records source package version, creation
  time, file byte lengths and SHA-256 hashes, omitted paths and model requirements.
- Maximum 10,000 payload files; 512 MiB per payload; 2 GiB total uncompressed
  payload; 1 MiB manifest. Limits are enforced while streaming, not solely from
  untrusted ZIP headers. Reject duplicate/case-colliding paths, traversal,
  absolute/Windows paths, links, encrypted entries and unexpected members.
- Preserve approved CLI workspace files and `projects/PROJECT_ID` files. Exclude
  credentials, sensitive names already blocked by Workspace, runtime caches,
  `.venv`, `node_modules`, model storage and links/placeholders; report omissions.
  No excluded directory is traversed. Reject root/ancestor links or reparse paths.
- Use the SQLite backup API, then integrity/schema/foreign-key checks and validated
  registry records. Refuse unknown tables, views, triggers, incompatible columns,
  and nonzero SQLite user_version. Accept current CLI-only or full session schema.
- Refuse snapshots containing running tasks. Queued tasks can be preserved after
  the web service has stopped, but restore marks both queued and running tasks
  interrupted, retaining receipts and forbidding automatic replay.

## Snapshot and restore

Create validates real source roots, takes the workspace-service lock, copies the
database through SQLite's backup API into temporary staging, checks its schema,
and streams eligible files into a bundle. Detect a file changing during a copy
and fail rather than call it a stable snapshot. Offline requirements apply across
database and files; this is not an OS sandbox against another process replacing
paths concurrently. Failed creation removes only its own partial output.

Inspect validates every member, size, hash and the staged database before returning
counts, omissions and required models/credential-binding names. It never initializes
application state or executes code from a bundle. Hashes establish accidental
corruption detection, not authenticity; import only a trusted private bundle.

Restore stages and validates first, then exclusively creates a new destination with
`data/platform.sqlite` and `workspace/`. Existing state cannot be replaced. A failed
restore cleans only directories this operation created. Records are preserved,
except imported pending tasks become interrupted with a restore receipt; remote
provider model configurations are disabled until explicitly reviewed on the new
host. Restoring does not start jobs, contact models, supply credentials, or install
model weights. A restore summary records host-review requirements. The user starts
the application with explicit data/workspace paths after destination checks.

Bundles are private, unencrypted archives. System credential files/environment
values are never collected, but user-authored state/documents may themselves hold
sensitive information. Files excluded as credentials are not recovered by restore.
Large-workspace incrementals, encryption, signing and automatic scheduling are
outside this delivery.

## Acceptance evidence

Round-trip real registry/session/job state and file bytes at a different path; WAL
data survives; pending jobs do not resume; missing model identities remain visible;
remote models are disabled. Corruption, crafted ZIP paths/links/collisions, size
limits, unsupported schemas/triggers, active-service/running-task snapshots,
existing destinations and changing files fail without overwriting state. CLI
inspection/invalid restore do not create default directories. Run the full suite
and a real CLI restore/serve/restart smoke test on Linux. Report Windows transfer
and target-GPU checks as unrun until the user supplies actual host evidence.
