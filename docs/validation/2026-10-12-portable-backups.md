# Portable private-state backup validation — 12 October 2026

Linux cloud evidence; no physical Windows transfer/GPU execution is claimed.

## Automated evidence

Baseline: 85 passing tests. Backup/inspection missing API first produced 22 expected
failures. Restore missing API produced 11 expected failures; CLI missing subcommand
produced three expected failures. Final pre-review full suite: **128 passed in
16.09 seconds**, including 40 backup tests and three CLI backup tests.

Regressions also went RED→GREEN for explicit SQLite-handle release (important for
Windows file cleanup), missing request-key uniqueness, hidden generated columns,
case-alias directory prefixes and cleanup of a parent created by another process.
Other exercised cases include committed WAL rows, private-state/file round trip,
credentials/runtime/link omission, source mutation, schema/triggers with recomputed
hashes, payload corruption/limits, existing destinations, failed-copy cleanup,
queued/running import interruption and disabled remote models.

Fresh independent review found one Important Windows portability issue: Win32
device aliases with superscript digits, spaces before extensions, and console
device names passed the initial regex. Twelve parameterized path/crafted-archive
regressions failed first, then passed after the cross-platform reserved-name fix.
Final full suite: **140 passed in 16.35 seconds**. No other Critical/Important
findings were reported. The reviewer independently ran 49 backup/CLI checks.

The sandbox switched to restricted networking during final verification; the
initial full run had 125 passes and 15 loopback-socket permission setup errors.
Rerunning through the approved local-socket execution path passed all 140 tests.
No assertions were disabled and no network-dependent fixture was skipped.

## Actual CLI and service checks

Created a fictional project/conversation with one completed answer, one queued
job and an uploaded file. The real CLI created a two-payload, 118,807-byte bundle,
inspected it without initializing the supplied unrelated directories, then restored
into a new host-layout directory.

Started the actual CLI `serve` subprocess against restored state twice, with a full
stop/restart between cycles. Loopback HTTP requests verified the original project
ID, completed answer, interrupted queued job and exact downloadable file bytes.
A concurrent CLI backup while the service held its lock failed and created no
partial output. Both service shutdowns completed successfully. No provider/model
calls, secrets or paid resources were used in this scenario.

Detailed fictional-fixture evidence is outside Git under cloud runtime validation
storage. Public source contains no user databases, workspaces or bundle contents.

## Limits and outstanding checks

- Checksums detect corruption, not signer authenticity; only trusted private input.
- Archives are unencrypted; user-authored content may contain sensitive data.
- 10,000 payloads, 512 MiB/file, 2 GiB total, 1 MiB manifest; no incrementals.
- Offline source/destination requirements are not an OS sandbox against concurrent
  external path replacement. Existing destinations cannot be intentionally replaced.
- Imported pending jobs do not resume automatically. Remote-provider configurations
  require explicit reactivation/host review. Model files/credentials are separate.
- Physical Windows transfer, target-GPU speed/quality and unavailable D: private
  state recovery remain unverified.
