# Transfer to another Codex or computer

Use `CURRENT.md` for the latest state and `NEXT-CODEX-PROMPT.md` for a new session.
Git source, cloud setup, credentials and private platform history are separate.

## Preserve source before leaving

Inspect `git status --short`, `git branch --show-current`, and `git log -5 --oneline`
in the existing checkout. Do not reset, clean, force-push or overwrite local changes.
After review and verification, preserve intended source/docs on a branch with the
required author/committer and a normal safe push when authorized. Confirm the pushed
commit; a local commit is not evidence it reached GitHub.

If pushing is blocked, retain the checkout and commits. A Git bundle outside the
repository can preserve committed branches without network, for example:
`git bundle create /workspace/Local-AI-Agent-handoff.bundle --all` followed by
`git bundle verify /workspace/Local-AI-Agent-handoff.bundle`. Use a new filename and
transfer it privately. A bundle does **not** contain uncommitted/untracked files:
commit reviewed source first or separately preserve those files/diffs securely.
Do not put private databases, workspace documents, secrets or model weights in Git.

## Bootstrap a new Codex environment

Connect the same GitHub repository, normally its published `main`, or the explicitly
named handoff branch/commit if the milestone is not on main. Read root `AGENTS.md`,
then `docs/handoff/CURRENT.md`, `TRANSFER.md`, README and deployment instructions.
Inspect Git status/log and the actual manifests/lockfile before touching files.
Historical docs can lag; current code, explicit evidence and the checkpoint decide
what is implemented. Do not assume old chat is available.

Use the existing checkout; don't create a worktree unless the user requests one.
The documented cloud path is `/workspace/Local-AI-Agent`. Read and use
`scripts/install-cloud.sh` for hash-locked dependencies/verified Ollama imports and
`scripts/start-ollama.sh` for restart. Installation may require environment network
access/approval; don't weaken checksums or TLS. Read README for alternate host setup.
Then verify, with actual output:

```bash
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
node --test tests/web-artifacts.test.cjs
.venv/bin/python main.py doctor
```

The Node check needs Node and the delivered test file; report unavailable checks
instead of claiming they ran. Doctor, fixture tests and a running process don't
prove real model quality. Run a representative local inference/file-delivery check
against deliberately owned inputs and report Windows/GPU separately from cloud CPU.
Don't replay old uncertain actions or activate remote models to make checks pass.

Cloud install/startup instructions and environment settings are separate from Git
publication. Git push publishes source; the environment **Publish** UI retains its
configured snapshot/setup. Neither automatically transfers running processes,
authentication, app/plugin availability, credit balance, caches or private state to
a new Codex. Review/save appropriate install/startup configuration in the new
environment and verify its runtime. A saved draft is not execution or publication.

Rebind credentials through secure environment/provider settings, checking names and
presence only. Never print/export secrets or ask for keys in chat. Revalidate provider
cost protection before any permitted live use; this handoff does not authorize paid
fallback or carry prior credential bindings into another environment.

## Preserve and move private local state

For the user's existing Windows installation, stop the workspace service with
Ctrl+C and wait before updating; preserve any Git changes instead of resetting:

```powershell
Set-Location C:\Projects\Local-AI-Agent
git status --short
git pull --ff-only
.\.venv\Scripts\python.exe main.py doctor
.\.venv\Scripts\python.exe main.py serve --open-browser
```

Keep this terminal and Ollama running. In the browser select Developer, ask for
`dedupe.py` and `test_dedupe.py` without executing code, and enter those exact paths
one per line in **Required output files**. Inspect task receipts, verified file
hashes and project files; restart the service and confirm persistence. Review code
separately: successful file delivery does not prove correct deduplication/tests.
If pull refuses local changes/divergence, preserve them and resolve deliberately.

For the latest source on this existing installation, also run
`.\.venv\Scripts\python.exe -m pytest -q` before starting the interface; stop on
any failure and give its output to Codex. Python dependencies have not changed in
the verified-file-delivery milestone. The latest physical Windows feature check is
still pending. The browser URL is `http://127.0.0.1:8765`; the source directory is
not the browser project directory (`workspace\projects\PROJECT_ID`).

For a different Windows computer with Git installed, use a new dedicated directory:

```powershell
New-Item -ItemType Directory -Force 'C:\Projects' | Out-Null
if (Test-Path -LiteralPath 'C:\Projects\Local-AI-Agent') {
    throw 'Existing checkout found: inspect it instead of cloning over it.'
}
git clone https://github.com/QuantumWeaveDev26/Local-AI-Agent.git 'C:\Projects\Local-AI-Agent'
if ($LASTEXITCODE -ne 0) { throw 'Clone failed.' }
Set-Location -LiteralPath 'C:\Projects\Local-AI-Agent'
git config user.name 'Naveen-145119'
git config user.email 'naveenreddy91590@gmail.com'
powershell -NoProfile -File .\scripts\setup-windows.ps1
if ($LASTEXITCODE -ne 0) { throw 'Setup failed; inspect the output.' }
.\.venv\Scripts\python.exe main.py serve --open-browser
```

Setup installs dependencies and prepares/checks local models; allow disk space and
download time on a new computer. Review the retained hardware/model guidance first.
If Python/Ollama installation asks for a fresh terminal, open one and rerun from
the project directory. No Docker or cloud key is required.

An ordinary clone restores no conversations, generated files, model weights or
virtual environment. Locate the actual source database/workspace first; older D:
state is unverified. Preserve `C:\Gov Proj` and the E: Docker backup unchanged.

Follow `docs/deployment/private-backups.md`: stop the workspace service with Ctrl+C,
wait for its worker and stop other writers; use `backup create --offline`, inspect
the private `.localagent.zip`, transfer privately, then restore **only to a new,
nonexistent destination**. Never overwrite an existing database/workspace. Archives
are unencrypted and can include sensitive user content; keep originals until actual
restoration and representative workflow checks succeed. Credentials, model weights
and `.venv` are separate; reinstall dependencies rather than copying the environment.

Shutdown may wait for an in-flight model call up to timeout. Normal queued jobs can
resume on service restart; crashed running jobs become interrupted. Offline backup
requires no active writers/running tasks. Restore interrupts imported pending/running
jobs and disables remote-provider records. Review receipts and restore-receipt before
explicit resubmission; don't automatically replay file or external actions.

Example on the existing Windows source checkout, after all writers stop:

```powershell
Set-Location -LiteralPath 'C:\Projects\Local-AI-Agent'
$bundle = Join-Path $env:USERPROFILE ('Downloads\Local-AI-Agent-' + [guid]::NewGuid().ToString('N') + '.localagent.zip')
.\.venv\Scripts\python.exe main.py backup create --output $bundle --offline
if ($LASTEXITCODE -ne 0) { throw 'Backup failed.' }
.\.venv\Scripts\python.exe main.py backup inspect $bundle
if ($LASTEXITCODE -ne 0) { throw 'Backup inspection failed.' }
Write-Host "Transfer this private file: $bundle"
```

On the destination computer, after source/dependencies exist, set `$bundle` to the
actual transferred file. Choose a new nonexistent state directory, then:

```powershell
$destination = 'C:\Projects\Local-AI-Agent-Restored-State'
if (Test-Path -LiteralPath $destination) { throw 'Choose a new nonexistent destination.' }
.\.venv\Scripts\python.exe main.py backup inspect $bundle
if ($LASTEXITCODE -ne 0) { throw 'Do not restore an invalid backup.' }
.\.venv\Scripts\python.exe main.py backup restore $bundle --destination $destination --offline
if ($LASTEXITCODE -ne 0) { throw 'Restore failed.' }
.\.venv\Scripts\python.exe main.py --data-dir "$destination\data" --workspace "$destination\workspace" doctor
if ($LASTEXITCODE -ne 0) { throw 'Review missing models/host configuration before startup.' }
.\.venv\Scripts\python.exe main.py --data-dir "$destination\data" --workspace "$destination\workspace" serve --open-browser
```

These paths assume the standard source `data`/`workspace` layout; for another
layout, explicitly pass its actual source paths. Do not infer old D: state from a
new clone or mistake a Docker VHDX for a platform backup. Retain backup originals.

Update `CURRENT.md` after milestones and immediately before transfer with exact Git
publication, verified checks, active job status and remaining host steps. GitHub
history carries maintained knowledge; it cannot recover unavailable private state.
