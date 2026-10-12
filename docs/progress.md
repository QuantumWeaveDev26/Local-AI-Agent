# Implementation ledger — 2026-10-10-local-platform.md
Ruling: implement in existing isolated cloud checkout and proceed without design approval gates — user explicitly authorized autonomous coding and setup. Dell access remains unavailable; no Dell measurement claims.
Ruling: constrained developer commands only, no generic shell — subprocess allowlists cannot sandbox arbitrary Python/test execution. User-initiated test execution requires an explicit flag.
Pre-flight: registry IDs and JSON configurations feed Factory and TaskService unchanged; both providers normalize message/tool formats into the same response type.
Task 1: complete — initial registry/persistence tests RED (missing modules) → 6 passing.
Task 2: complete — document/permissions/provider tests RED → full suite 24 passing. Ollama archive official SHA-256 verified; loopback server started with cloud disabled.
Task 3: complete — execution tests RED → 32 passing. Corrected test fixture to use a read-only agent: starter Marketing legitimately has assigned write permission.
Task 4: implementation complete — CLI tests RED → 36 passing; escaped-secret and protected Git diff regressions RED → 38 passing. Hash-locked install script executed successfully and repeated.
Final review: independent reviewer found Git pathspec expansion, Windows path aliases, dictionary-key redaction, unavailable symlink privileges, and disabled tool routing. Reproductions RED → fixes → 50 passing, no deferred review findings.
Ruling: use official registry layers plus supported GGUF import in cloud — Ollama's direct-DNS redirect validation cannot resolve the CDN here; curl through the platform proxy retains HTTPS validation and every layer matches its authoritative SHA-256. No insecure flags or checksum changes.
Real inference: first routing test misclassified candidate-for-developer-role as Developer. Marketing, Developer, new SEO routes passed; PDF recruitment completed. Added capability-reason response schema and action-oriented routing prompt; rerunning actual routing rather than replacing it with a fixture check.
Real model diagnosis: qwen3:1.7b still misrouted candidate assessment with rationale and thinking mode. This is a model-quality limitation, not registry/configuration failure. Second supported trial qwen3:4b correctly selects Recruitment; final three routes ongoing. Both official models' layers verified. Current config uses 4B Manager plus shared 1.7B specialists; fresh init defaults to one 4B model to avoid shipping known misrouting by default.

All four actual 4B semantic routes passed. 1.7B standalone benchmark completed: 3.88–8.84 tokens/sec, peak server+runner RSS 2.33 GiB, valid JSON/tool calls and correct arithmetic. Manual coding review found adjacent-only deduplication. Assigned Developer to 4B. First 4B native tool run timed out because the official template unconditionally starts thinking even with API think:false. Supported Modelfile override now honors that flag; repeated configuration is idempotent. Native tool/coding checks are being repeated; aborted prior coding validation is explicitly marked cancelled.

Final correction: repeated 4B native tool calls timed out, including parser/template and restarted Go-template trials. Removed the unproven helper and restored official 4B template. Default profile now registers 4B Manager plus shared 1.7B specialists; init preserves existing configuration. No 4B code/tool quality success claimed. Source is consolidated under /workspace/Local-AI-Agent; folder guide and docs/validation evidence directory added.

Final verification: 58 automated tests passed; bash syntax checks passed; hash-locked installation repeated successfully; doctor verified installed 4B router; restarted official-template runtime returned READY through a completed persisted 1.7B Marketing task (4680cf9c6bb5475287a667216d64d3b1). Cloud draft saved with explicit Local-AI-Agent mount path, tested install script and matching startup instructions. Publishing and Dell execution remain separate user-host steps.

2026-10-10 post-publication review: published base configuration has no pending draft; restored files/dependencies/models checked. Ollama restarted, 58 tests passed in 17.46 seconds, pip check passed, real 1.7B inference returned READY and real 4B routing selected Recruitment. Source remains untracked/unborn; snapshot retention verified, GitHub source reproduction not established. Published network is unrestricted and was preserved.
Research: explored public Lyzr product/docs and three repositories; wrote source catalog, analysis and evolving roadmap. User confirmed both conversational/research and autonomous-tool Grok inspiration. Research adds documentation only; no proposed roadmap feature is represented as implemented.

2026-10-10 source publication preparation: verified the empty connected GitHub remote, retained all source and research files, reran 58 tests (all passed), checked shell syntax, reviewed 50 source/config/documentation files for credential patterns and large/binary artifacts, and added clone instructions. Initial source commit is being prepared for main; models, databases, virtual environment and private workspace files remain ignored.

2026-10-10 hardware/portability steering: personal RTX 3050 6 GB laptop is now first target; office Dell access is unavailable and does not block development. Original handoff reports 16 GB RAM and nearly full SSD; fresh local audit remains necessary. Updated current setup/roadmap and added transfer contract/runbook distinguishing source, SQLite backup, private workspace, credentials, models and host dependencies. Full feature roadmap preserved; new desktop/session/transfer automation remains proposed, with no physical Windows execution claim. Persisted requested Git identity in AGENTS.md.
Portability documentation verification: relative links resolve, Git whitespace checks passed, and the SQLite backup API preserved complete agent/model/tool configurations in a temporary Linux database round trip. Windows host-to-host transfer remains unverified.

2026-10-10 Windows host setup: user-provided output confirms initialization at
D:\Projects\Local-AI-Agent, Python3.12.10/Ollama0.35.1/qwen3:1.7b, 56 passing tests,
2 Windows filesystem skips and completed inference smoke. Actual GPU allocation,
latency and quality benchmark remain pending. No cloud-to-Windows access claimed.

Persistent assistant workspace delivered on a feature branch: shared runtime with
bounded session history, scoped projects/files, durable single-worker queue,
cooperative cancellation and interrupted-job protection; guarded loopback HTTP
and browser workspace. Initial tests RED, task suites GREEN (67, then75). Real
Chromium/Ollama scenario passed, as did stop/restart with READY follow-up recall.
Wheel includes the three browser assets. No new product dependency/model download.

Independent review identified four important findings; reproductions RED then fixes
GREEN: rejected composer, stale project/session controls, disabled-agent duplicate
retry and redacted-payload identity collision. Added lost-reply reconciliation
checked in Chromium. Final suite77 passing; no deferred minor findings.

Rulings: user autonomous coding authorization takes precedence over skill approval
gates; existing checkout/feature branch follows AGENTS.md; unavailable skill helper
references use a manual ledger. Added general Assistant without overwriting configs.
Shutdown waits for the in-flight inference call. Fixed an existing stale-bytecode
test runner with a fresh per-run cache. Costs: editable scope choices, less automated
bookkeeping, one extra optional agent, timeout-bounded shutdown latency and cold
imports for explicit workspace tests. Earlier redacted-only request identities are
migrated conservatively; their original secrets cannot be reconstructed.

Hermes steering: user suggested Hermes Agent. Inspected official source/docs at
dce1e9b37581dd62e480a9064dc04a709c2940d3, recorded comparison and proposed isolated
prototype before independently building later memory/skills/scheduler/messaging.
No Hermes installation, integration, migration or performance claim made. Upstream
installer targets Python3.14; preserve the user's working3.12 environment.

2026-10-12 ModelArk research/preparation: user is an AI full-stack developer and
requires no paid usage after a reported Seedance auto-debit. Public documentation
inventory529 entries,157URL variants retrieved with136body extractions including
two finance documents. Core billing/quota/API/campaign/integration material read;
not a claim of reading all529entries fully. User explicitly reports Free Tokens
Only mode On. Mode protects supported online token inference, not auxiliary
services. Daily-token data campaign requires turning it off; excluded from use.
No paid-plan purchase, account change, service/resource activation or inference
request performed; no key requested/used. Hosted agents/tools/KB/storage/media
and unprotected fallback remain excluded. Saved findings/source catalog and a
disabled GLM5.2 model example, preserving local defaults.

Compatibility diagnosis: existing OpenAI branch changed /api/v3 into the invalid
/api/v3/v1/chat/completions path. Local HTTP regression RED, minimal versioned-path
fix GREEN; full Linux suite79 passed. Prepared JSON validates as disabled. This
does not validate ModelArk quality/billing, native schema support, reasoning
passback, context enforcement, or Windows execution. Those limitations are explicit.

Current disk availability is unknown: user lacks the inserted disk and is unsure
whether D:\Projects\Local-AI-Agent/private state exists. Supplied read-only drive/
path checks. Cloud/Git source survives; private state cannot be recovered from Git.

Ruling: Apply the small offline URL fix and disabled example within prior
autonomous coding authorization, without another design gate — no remote service
is enabled and changes are reversible. Cost if wrong: some explicit versioned
custom endpoints may require provider-specific adaptation. Existing unversioned
and /v1 behavior remain covered by tests. Quota-mode status is user-host evidence,
not a live account verification or implemented billing-policy gate.

Independent ModelArk preparation review: no Critical, Important or Minor findings.
Reviewer checked URL compatibility, disabled example, cost guidance, links and
catalog hashes against cached official bodies. Full suite79passed in13.81seconds;
Windows and live provider/account behavior remain untested. Publication uses the
requested Naveen-145119 author/committer identity; no credentials/private data
or retrieved raw documentation bodies enter Git.

2026-10-12 disk inspection: screenshot shows C:36.4GBfree of475GB,92%used and no
D:drive visible. Prepared a standalone Python standard-library metadata audit
without requiring the missing project drive. No deletion, contents reading, model
downloads, shell cleanup or paid service use. Local filesystem regressions RED
(missing script) ->5passing; helper ranks root/nested directories, development
dependencies/caches and files, bounds rankings, skips links/cloud placeholders,
deduplicates hardlinks and refuses to overwrite a report. Logical sizes and
permission/reparse gaps are explicitly distinguished from allocated disk usage.
Actual Windows scan/output remains the physical user-host step; no large-item
diagnosis or cleanup recommendation for a specific file is claimed yet.

Disk-audit review: Windows DirEntry.stat zeros hardlink identity fields. Reproduction
with simulated Windows metadata RED (double-counted link) ->os.stat identity fallback
GREEN. Minor deferred: internal root-directory/extension/hardlink accumulators are
not bounded by --top; rankings are bounded and memory caveat is documented. No
actual Windows metadata scan or user deletion performed.

2026-10-12 later user-host disk evidence: the standalone Windows scan completed
with 1,925,693 accessible files and 392.77 GiB logical payload. The user attached
an NTFS HDD as E:, backed up the Docker data disk and performed requested cleanup.
Docker startup logs showed ERROR_SHARING_VIOLATION; Get-DiskImage showed the C:
data disk attached. Targeted termination/detachment cleared startup; the user
reported their creative-ai containers/volumes visible again. They subsequently
explicitly chose complete Docker removal, then removed the identified recording
and older user temporary files. Latest user-reported C: free space: 93.84 GiB.
Preserve C:\Gov Proj and E: backups. Docker backup restoration and the original
platform-state location are not verified; these are user-host reports, not remote
Windows execution by the cloud agent.

2026-10-12 autonomous continuation: user asked to close the laptop and continue all
platform work without stopping. Cloud baseline 85 tests passed; no Windows remote
access or perpetual post-task execution is implied. Selected the portable-state
milestone because it directly protects transfers and unavailable-disk recovery.
Spec/plan committed; user-delegated autonomous scope overrides additional skill
approval handoffs. Inline implementation, existing checkout/feature branch and
one final fresh-context review preserve repository instructions.

Portable snapshots and validated fresh-directory restore: SQLite backup API,
approved file bytes, bounded manifest/hashes, portable paths, schema/constraint
checks, offline service lock and no overwrite. Credential/runtime/model files
excluded with an omissions report. Imported queued/running tasks are interrupted
with receipts; remote model configurations disabled. No provider requests or new
dependencies. All 128 Linux tests passed in 16.09s before final review. Actual CLI
create/inspect/restore and two restored-service start/restart HTTP cycles preserved
fixture project/history/artifact bytes and never replayed a queued job. See
docs/validation/2026-10-12-portable-backups.md. Physical Windows transfer/GPU checks
remain separate. Bundles/private-fixture databases stay outside public Git.

Portable backup final review: one Important Windows reserved-device-name defect,
12 regressions RED→GREEN, final suite 140 passed in16.35s after approved loopback
socket access. No other Critical/Important findings. Reviewer ran49 backup/CLI
checks. Initial restricted-sandbox run had125passes/15socket-setup errors; resolved
by approved execution, without test suppression or product workarounds.

Rulings for this milestone:
- Honor explicit autonomous implementation/publication rather than skill approval
  handoffs; cost if wrong: milestone priorities may need revision.
- Use the existing checkout/feature branch under AGENTS.md; cost if wrong: branch
  isolation may be less convenient than a worktree, without modifying other files.
- Keep a manual ledger because provider helper resources were unavailable; cost if
  wrong: bookkeeping requires manual verification rather than helper automation.
- Physical Windows recovery/GPU execution were outside reviewer evidence; keep
  them unverified. Cost if wrong: host-specific issues await actual host checks.
- Provider availability/billing were not exercised; restore disables non-Ollama
  provider records and makes no requests. Cost if wrong: explicit later activation
  without host/billing review could fail or incur charges.
- Adversarial concurrent path replacement is outside the offline contract, not an
  OS sandbox guarantee. Cost if wrong: external mutation could invalidate scope or
  snapshot stability. No such behavior is claimed protected by this delivery.

2026-10-12 Hermes compatibility spike: isolated reviewed revision, Python3.14.7,
frozen core lock installation. Actual 8K initialization rejected (64K minimum),
64K initialization accepted but original Ollama tag loaded4K; an explicit num_ctx
64K clone loaded40960 with approximately6GiB allocation, CPUonly. Native platform
reference loaded the requested8192 and returnedREADY. First Hermes short chat
returnedREADY, repeatsaddedperiod; SQLite recall across process restart and stream
hard cancellation worked. Normal file dispatcher allowed owned fixture reads/writes
outside cwd, which does not satisfy our project-root contract. No user files or
existing platform state imported, weights downloaded, hosted model requests, paid
resource activation or external messages. Runtime remains ours; scope adapter and
actual Windows/GPU profiling are required before production Hermes integration.
Detailed source hashes/report in docs/research/hermes/2026-10-12-local-prototype.md.

Publication status at this point: local main2864440 includes the reviewed 140-test
portable-state milestone. First GitHub push approval was aborted; no successful
push is claimed. Independent runtime/dependency downloads and local-only probes
received execution approval and continued. Preserve local commits until publication
is completed; do not reset or force-push around an unresolved approval.

2026-10-12 publication completed: approved normal Git push advanced GitHub main
from 67f41d8 to 54b9095, containing the reviewed portable backup/restore milestone
and measured Hermes report. No force push or private runtime fixture publication.
The disposable Hermes probe tag was removed and original Qwen3 weights preserved.
Environment configuration already contains installation and restart/readiness
instructions; no configuration change or new snapshot publication is claimed.

2026-10-13 Windows setup regression: user clone at C:\Projects\Local-AI-Agent
installed dependencies and initialized state, then reported 138 passed, 1 skipped,
1 failed (test_cli_backup_restore_round_trip): WinError32 deleting the temporary
schema database. SQLite transaction context managers do not close connections;
Database and SessionStore constructors left handles awaiting garbage collection.
All application Database connection scopes now explicitly close after the existing
transaction commit/rollback. Two regression tests retain real handles and verify
they are closed, including schema construction, registry errors and durable jobs.
Both tests failed before the fix. Full Linux suite: 142 passed in 16.30 seconds
with permission for local HTTP fixtures; initial sandbox run had 127 passed and
15 socket-permission errors. Actual Windows rerun and inference remain pending.
