# Back up and transfer private platform state

The Python/Ollama platform does not require Docker. These commands preserve its
SQLite registry, task receipts, projects, conversations and approved workspace
files. They **do not restore Docker images, PostgreSQL volumes or VHDX backups**.
Keep the user's separate Docker backup on E: intact.

## Create and inspect

Use the actual Local-AI-Agent checkout and virtual environment. Stop `main.py serve`
with Ctrl+C and wait for its worker to finish. Stop other platform CLI writers and
workspace editors. `--offline` acknowledges this condition; it does not terminate
processes. An active service lock or a task still marked running prevents creation.
Review uncertain task receipts before resolving them; backup does not change source
task statuses or automatically decide that a task is safe to replay.

For default `data/` and `workspace/` directories on Windows:

```powershell
New-Item -ItemType Directory -Force E:\Backups\Local-AI-Agent | Out-Null
$platformBackup = 'E:\Backups\Local-AI-Agent\platform-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.localagent.zip'
.\.venv\Scripts\python.exe main.py backup create --output $platformBackup --offline
.\.venv\Scripts\python.exe main.py backup inspect $platformBackup
```

Global `--data-dir SOURCE_DATA --workspace SOURCE_WORKSPACE` before `backup` selects
nondefault source state. Output parent must exist; filename ends `.localagent.zip`;
existing outputs are never replaced. Data/workspace roots cannot overlap, and the
output cannot be inside the workspace. Linked/reparse source ancestors are refused.

Creation uses SQLite's backup API, including committed WAL rows. Inspection checks
every payload's SHA-256 and byte length, portable paths, bounded sizes, SQLite
integrity, known schema/index constraints, foreign keys and registry definitions.
It does not initialize unrelated application state or contact any model provider.

Review `omitted`: credential files, `.env*`, `.ssh`, `.git`, `.venv`, `node_modules`,
runtime/model directories, private-key suffixes, links/reparse paths and cloud
placeholders are excluded. Empty directories are not preserved. File bytes are
unchanged; arbitrary user-provided state/documents may themselves contain secrets.

Limits are 10,000 payloads, 512 MiB per file, 2 GiB total and a 1 MiB manifest.
Oversized snapshots fail explicitly rather than silently dropping eligible files.
Incremental/larger bundles are a future extension.

## Restore to a new directory

Install the reviewed source and dependencies on the destination. Recreate `.venv`;
do not copy it between hosts. Choose a directory that **does not exist**, even as
an empty directory:

```powershell
.\.venv\Scripts\python.exe main.py backup restore $platformBackup --destination C:\LocalAI-State\restored-20261012 --offline
.\.venv\Scripts\python.exe main.py --data-dir C:\LocalAI-State\restored-20261012\data --workspace C:\LocalAI-State\restored-20261012\workspace models list
.\.venv\Scripts\python.exe main.py --data-dir C:\LocalAI-State\restored-20261012\data --workspace C:\LocalAI-State\restored-20261012\workspace doctor
```

Archive/database validation happens in staging before destination creation.
Existing state is never overwritten. Failed restore removes only directories this
operation created. Source and bundle remain intact. Other processes must not
mutate paths concurrently; this is not an OS sandbox against hostile file changes.

Restored state contains `data/platform.sqlite`, `data/restore-receipt.json`, and
`workspace/`. The receipt reports interrupted task IDs, disabled model IDs, model
requirements and host review. Imported queued/running work becomes interrupted
with an error receipt; no restored job starts automatically. Review receipts before
explicitly submitting work again.

Model weights are not included. Review endpoints, installed models, agent knowledge
paths and credential-binding names. OpenAI-compatible model configurations are
disabled on restore, including loopback adapters, until explicit host review.
Restore does not activate ModelArk or authorize paid usage; its Free Tokens Only
policy and disabled candidate's compatibility limits still apply.

After `doctor`, actual inference and a representative file workflow succeed:

```powershell
.\.venv\Scripts\python.exe main.py --data-dir C:\LocalAI-State\restored-20261012\data --workspace C:\LocalAI-State\restored-20261012\workspace serve --open-browser
```

On Linux use `.venv/bin/python` and host paths. Cloud tests have no direct access
to the Windows laptop's disks.

## Privacy and recovery limits

Bundles are **unencrypted private archives**, Git-ignored. Transfer privately and
retain originals until actual restoration is verified. Checksums detect corruption,
not authenticity: import only trusted bundles. Environment values and external
credential files are not collected, but arbitrary sensitive user-authored content
is not guaranteed to be detected/redacted. Automatic encryption, signing and
scheduling are outside this delivery.

Linux automated round trips and live local HTTP checks are delivery evidence.
Physical Windows-to-Windows transfer and GPU performance remain host checks. A Git
clone or Docker backup cannot restore an unavailable platform database/workspace.
Locate original private state before claiming that previous conversations survived.
