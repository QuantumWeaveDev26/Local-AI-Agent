# Published environment review — 10 October 2026

The published cloud environment restored successfully. The codebase remains at
`/workspace/Local-AI-Agent`, with Ollama and model files under `/workspace/runtime`.
This review was performed after publication, rather than inferred from the earlier
configuration draft.

## Evidence

| Check | Observed result |
| --- | --- |
| Configuration | A new base version is present; `draft_id` and `revision` are null |
| Repository mount | `Local-AI-Agent`, matching the actual checkout |
| Retained files | Application, documentation, Python environment, SQLite records and model files present |
| Service restoration | Ollama was initially absent and started using the saved startup helper |
| Runtime | Ollama 0.40.2; Python 3.12.14; Linux CPU host, no NVIDIA GPU |
| Model readiness | `local` = qwen3:1.7b; `router` = qwen3:4b; both installed |
| Automated suite | 58 passed, zero failed/skipped, 17.46 seconds |
| Dependencies | `pip check`: no broken requirements found |
| Real specialist inference | Marketing returned exactly `READY`; persisted task completed |
| Real Manager routing | Candidate evaluation for a developer role selected Recruitment |

The real inference task is `1ce6d6d297614006a76ecc41b88ee2fc`. The routing-only task
is `70a96fa94eda4e2d81a68b9234fb504a`; that check exercised the actual restored 4B
model and production routing function, without running a full recruitment assessment.
Machine-readable evidence is in [published-environment.json](published-environment.json).

## Review observations

1. **The published snapshot works.** Models and dependencies survived; processes
   still require startup. A functional response and a semantic routing result were
   verified after restarting the runtime.
2. **Source retention and Git retention are different.** Source files are still
   untracked in a valid unborn Git checkout. The snapshot preserved them, but the
   GitHub remote cannot yet reproduce this source tree. A future source-control
   milestone should commit the reviewed application and documentation, then publish
   remotely when that action is requested. This review did not commit or push.
3. **The published network policy is unrestricted.** The previous draft used exact
   model-download domains. The current published configuration is the authority;
   this review preserved it. Application-level remote model calls still require
   `--allow-remote-models`, and Ollama binds to loopback. This environment is online,
   not air-gapped.
4. **Known model limitations remain.** 4B native tools previously exceeded the
   300-second CPU timeout. The 1.7B coding probe failed manual quality review.
   Defaults therefore use 4B for routing and 1.7B for specialist execution. The
   successful restoration checks do not establish general coding reliability.
5. **The Dell remains a separate host.** No Windows execution, GPU performance,
   power/thermal measurements, or physical Dell installation was verified here.

No product code, dependency declarations, lockfiles, or published environment
settings were changed during this review. The additions are research and validation
documentation plus ignored runtime check outputs.
