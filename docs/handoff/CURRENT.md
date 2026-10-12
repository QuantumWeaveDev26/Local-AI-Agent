# Current handoff — maintained checkpoint

Updated 13 October 2026 during the verified-file-delivery milestone. Read this with
root `AGENTS.md`; it is a checkpoint, not an exhaustive chat transcript. Verify
`git status` and `git log` before relying on its branch/publication details.

## Owner, direction and constraints

- Owner is an AI full-stack developer building a serious, portable, general-purpose
  local agent platform, inspired by Grok, Lyzr and Hermes. Recruitment, marketing,
  development and SEO are examples; keep the evolving vision open.
- Repository: `https://github.com/QuantumWeaveDev26/Local-AI-Agent`.
  Cloud checkout: `/workspace/Local-AI-Agent`; current Windows checkout:
  `C:\Projects\Local-AI-Agent`. Earlier D: private state remains unverified.
- Use the existing checkout. Author and committer must be
  `Naveen-145119 <naveenreddy91590@gmail.com>`. Preserve local changes and private state.
- No paid usage, hosted fallback or credentials in chat. ModelArk Free Tokens Only
  On is user-reported account evidence, not a live query or a universal billing
  guarantee. Its candidate stays disabled; paid tools/storage/data-reward enrollment
  and media generation are excluded. No remote inference was used for this milestone.
- User reports Windows 11, Python 3.12.10, Ryzen 7 7445HS, 15.23 GiB RAM,
  RTX 3050 6 GB and latest doctor C: free 97.24 GiB. These are host reports.
  Preserve `C:\Gov Proj` and
  `E:\Backups\Docker-20261012-140123\docker_data.vhdx`. User removed Docker;
  core Python/Ollama operation does not depend on it.

## Source and current milestone

Published implementation on `main`: `10edb5f` (verified file delivery). Normal
GitHub push confirmed advancement from `fe4a321`, the SQLite Windows-lock fix.
Earlier portable-backup and measured Hermes work is published; `1b90153` records
its publication. The delivery branch was fast-forward merged into local main.
These handoff files form the subsequent documentation checkpoint. Obtain its full
commit with `git rev-parse HEAD` and confirm against `git ls-remote origin
refs/heads/main`; never infer publication from successful local tests.

The Windows baseline rerun passed **141 tests, 1 skipped, 55.25 s** and local
inference returned `READY`; Linux baseline passed **142 tests**. Browser chat/recall
and a `hello.py` write/read produced receipts. A later dedupe request claimed files
were created without files being found or visible write receipts. The exact host
model response/cause is unconfirmed. The established product gap was that a nonempty
answer could complete without delivering requested files.

Current implementation adds optional `required_files` (up to eight portable relative
paths): browser **Required output files**, durable payload/history, `TaskService`,
and repeated CLI `--require-file`. Completion requires a fresh successful write in
this task and matching current UTF-8 bytes/SHA-256 for every requirement. Missing,
partial, changed, fake-write or previously-existing-only delivery fails. Partial
writes stay available with receipts; failed turns do not enter conversation context;
there is no automatic replay or code execution. Without requirements, completion
can mean response only, and the UI identifies recorded actions. Inspector separates
selected agent from AI response labels.

Initial verification: **169 Python tests + 6 Node DOM tests passed**. Review then
found required filenames silently changed by secret redaction and a Windows path-case
mismatch; both received fixes/regressions. Final full suite: **173 Python tests
passed in 18.66 s + 6 Node DOM tests passed**. Both Important findings were rechecked
and resolved, with no additional findings reported. Actual Windows validation of
this new feature is pending.

Real cloud 1.7B job wrote both required files and verified hashes plus restart
persistence. Private evidence, if retained in this environment:
`/workspace/runtime/validation/file-delivery-2026-10-13/run-zbn5xj9o/evidence.json`.
**Delivery is not code correctness:** generated dedupe still mishandled nonconsecutive
duplicates and the generated test lacked an import. Code was never executed. The
private evidence path is not a portable Git artifact.

## Models and architectural decisions

- Preserve current configuration: 4B Manager/router and shared 1.7B specialists;
  `init` preserves existing records. No model defaults were changed in this milestone.
- User GPU benchmarks: 1.7B ~86–90 tokens/s, 1,895 MiB, 100% GPU, 8K context;
  Qwen3 4B thinking ~42–43 tokens/s, 3,318 MiB, ignored `think:false` and produced
  excessive thinking at output length 1,200. Template-clone prefill attempt failed;
  user confirmed the clone deleted.
- Official `qwen3:4b-instruct-2507-q4_K_M`, registry ID `instruct4b`, was installed
  and measured by user: ~43–45 tokens/s, 3,249 MiB, 100% GPU; JSON/tool-call probes
  passed without excessive thinking. It still produced incorrect nonconsecutive
  dedupe. Candidate is not assigned to agents; quality/routing checks precede changes.
- Keep native runtime. Pinned Hermes prototype found 64K startup guard/context
  allocation mismatch and file dispatcher access outside cwd. Basic Linux chat,
  persisted recall and no-tool cancellation worked; production compatibility did not.
  See `docs/research/hermes/2026-10-12-local-prototype.md`.
- Implemented: registry/providers/scoped tools, durable tasks, local browser
  projects/conversations/queue, bounded completed-turn context, private offline
  backups. Lasting memory/retrieval, durable multi-step coordination, connectors,
  scheduling, sandboxed code execution and full roadmap remain proposed.

## Exact next work and source map

1. Read this handoff and confirm a clean checkout plus the published source commit.
   Preserve any changes if a new environment or user checkout differs.
2. On the actual Windows checkout, inspect Git changes, safely update source, refresh
   setup as needed and repeat tests. See `TRANSFER.md` for exact startup. Run a
   Developer task requiring `dedupe.py` and
   `test_dedupe.py`; inspect files/receipts/status and restart persistence. Keep code
   execution explicit and only after review; do not assume delivered code is correct.
3. Compare 1.7B and `instruct4b` against fixed routing/tool/code-quality cases before
   assigning the candidate. Then select one coherent roadmap milestone with the owner.

Key files: `app/services/tasks.py` (execution), `artifacts.py` (delivery contract),
`jobs.py`/`sessions.py` (queue/context), `app/tools/workspace.py` (scoped files),
`app/web/` (HTTP/UI), `app/core/llm.py` (providers), `app/database.py` (persistence),
`app/services/backups.py`/`backup_format.py` (private transfer), `tests/` (regressions).
Read `docs/PROJECT_STRUCTURE.md`, `docs/progress.md`, `docs/validation.md`,
`docs/deployment/` and `docs/roadmap/2026-10-10-evolving-platform.md` as needed.

Maintainer: update this file after every milestone and **before every handoff**:
source commit/branch/push, exact passed/skipped/unrun checks, host evidence, remaining
bugs, decisions and next task. Update `TRANSFER.md` if transfer procedures change and
`NEXT-CODEX-PROMPT.md` if bootstrap constraints change. Work does not continue after a
Codex task ends unless another task/process is actually running.
