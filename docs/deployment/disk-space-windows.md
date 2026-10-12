# Identify disk usage before cleanup

12 October 2026: the user's Explorer screenshot shows C: with 36.4 GB free of
475 GB, about 92% used. Only C: is visible in that screenshot. This is evidence of
low free space, not evidence about which files consume it. The cloud cannot inspect
the user's Windows filesystem directly.

## Built-in category view

Open **Settings > System > Storage** and let the categories finish calculating.
This helps distinguish installed apps, temporary files, personal files and system
usage. The following only opens that page:

```powershell
Start-Process 'ms-settings:storagesense'
```

## Read-only file/folder report

`scripts/audit-disk.py` is a standalone standard-library Python 3.11+ helper. It
does not require a project checkout, virtual environment, administrator rights,
Docker, models or paid services. It reads directory entries/file metadata and
prints the largest root folders, nested folders (up to depth five), interesting
development/cache folders at any depth, and largest files. It does not read file
contents, delete anything, run cleanup commands or execute code from scanned files.

For an existing checkout:

```powershell
$reportFile = Join-Path $env:TEMP ('disk-audit-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')
python scripts/audit-disk.py --root C:\ --output $reportFile
```

If the previous D: checkout is unavailable, download the helper from a reviewed
commit's raw GitHub URL into TEMP and run it by absolute path. The chat provides
the actual published commit URL; do not use a placeholder SHA. Downloading the
helper does not download models or create cloud resources.

The report filename must be new: the helper refuses to overwrite an existing file.
The report is the only application file it writes. Press Ctrl+C to stop a scan;
it has no cleanup operation to complete or roll back. Progress prints periodically.

## Interpret results correctly

- Root-folder rows partition the accessible directories, but files directly in C:
  appear separately in the largest-files list.
- Nested folder and cache/dependency sizes are inclusive. Do not add parent and
  child rows together.
- Sizes are logical file sizes, **not exact allocated NTFS usage or guaranteed
  reclaimable space**. Compression, sparse VHDX files and filesystem metadata can
  create differences. Hardlinks are counted once, under the first encountered path.
- Symlinks, junctions, Windows reparse points and offline/recall placeholders are
  skipped; OneDrive content may be omitted. No cloud-file hydration is requested.
- Permissions and files changing during a scan can prevent enumeration. The
  report includes error counts and a bounded list of skipped path examples.
  An accessible subset must not be mistaken for an exact total of drive usage.
- No administrator scan or permission change is performed automatically. Use the
  Windows Storage category view when protected/system areas dominate the gap.
- Printed rankings are bounded. The scanner still retains hardlink identities,
  extension aggregates and immediate root-directory sizes; memory use can grow
  with those counts. Use the built-in Storage view if a very large scan is unsuitable.

## Decide by category after inspecting the output

| Large item found | Appropriate next action |
| --- | --- |
| Old installers, archives, duplicate videos/downloads | Inspect personally; move/delete only what is no longer needed |
| Installed apps/games | Uninstall unwanted software through Settings |
| `node_modules`, `.venv`, package caches | Confirm the project is backed up and dependencies can be recreated; do not delete its source, lockfiles or private state |
| Ollama/Hugging Face model files | Identify which models are still used before removing them through supported tools |
| WSL/Docker `.vhdx` disks | Inspect the distributions, images and volumes; do not delete a virtual disk directly |
| `Windows`, `WinSxS`, `Program Files`, pagefile/hiberfile | Use supported Windows cleanup/app management; do not manually delete system files |
| OneDrive/reparse-point gaps | Check Windows Storage and OneDrive's own space controls |

The user's explicit intent is to choose deletions after seeing evidence. The audit
does not mark a cache, virtual environment, model or personal file safe to delete
merely because it is large. No deletion is authorized by this scan.

Linux fixture validation covers size ranking, intact inputs, links/placeholders,
hardlink deduplication, missing roots and exclusive report creation. This is not
an executed Windows/C: audit; the user must run it on the actual laptop.
An additional simulated-Windows regression verifies the fallback to real
`os.stat` identity when `DirEntry.stat` returns zeroed hardlink fields.
