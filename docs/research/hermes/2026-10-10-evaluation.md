# Hermes as a runtime foundation — 10 October 2026

The user asked whether we are building Hermes Agent and suggested it as an idea.
We currently own a small configurable runtime. We have not installed, forked,
embedded or replaced it with Hermes. Qwen is our current inference model family;
Hermes Agent is a runtime that can use local or hosted models. Those are separate
choices. The project is NousResearch/hermes-agent, not the Hermes model family.

12 October update: an isolated pinned Hermes installation and local prototype are
now executed in the cloud; our product runtime remains unchanged. See the
[actual results](2026-10-12-local-prototype.md): small chat/restart recall/cancellation
worked, but the 8K profile is rejected, actual allocated context differs from the
64K setting, and default local file scope exceeds our project boundary.

## Recommendation

Evaluate Hermes as a foundation before independently implementing the larger
memory/skills/scheduling/messaging roadmap. Keep our project/workspace experience,
configurable specialist definitions, evidence and permission requirements as the
product contract. If a pinned Hermes version satisfies that contract, reuse its
runtime through an explicit adapter or deliberate migration. Do not maintain two
uncoordinated execution engines writing the same state.

| Area | Our delivered platform | Hermes documented capabilities / relevance |
| --- | --- | --- |
| Conversation | Project-scoped SQLite sessions, bounded recent turns | SQLite/FTS5 sessions, conversation recall and context compression |
| Memory | Recent completed context only | Agent-curated persistent memory/user profile; optional memory providers |
| Skills | Configurable specialist instructions/tools | Reusable procedural skills and experience-driven updates |
| Automation | Single local durable task queue | Cron and messaging gateway delivery |
| Tools | Scoped document/files and read-only Git | Larger tool catalog, MCP and multiple execution backends |
| Execution | Ollama native API or OpenAI-compatible | Custom endpoints including local Ollama `/v1` |
| User surface | First local browser workspace and CLI | CLI/TUI, messaging and desktop application |
| Licensing | Our repository source | Upstream reports MIT; preserve applicable notices if redistributing code |

This table compares our test evidence with upstream documentation, not an executed
Hermes benchmark. Upstream's “self-improving” description includes memory/skills
updates; it does not establish automatic retraining of the local model's weights.

## Laptop compatibility questions

The user's working baseline is Windows/Python 3.12.10, 16 GB RAM, RTX 3050 6 GB,
Ollama 0.35.1 and qwen3:1.7b plus a 4B router. Upstream currently documents native
Windows support, but its installer manages a separate Python 3.14 toolchain. At the
reviewed revision, pyproject declares >=3.11,<3.15 for update compatibility while
comments and dependency markers target 3.14. Do not install it into our existing
3.12 virtual environment or assume the declared range proves runtime support.

The Ollama guide describes a custom endpoint at `http://localhost:11434/v1`.
It also recommends large models and a 64,000-token agentic context. Those settings
are not a validated profile for this 6 GB GPU. Its model table's tool-support claims
must not replace actual tests: our Qwen 1.7B tool probes already work, while its
reasoning/code quality and the 4B tool timeout remain known limitations.

Large system prompts/tool schemas consume prefill time and KV-cache memory even
when the framework itself is lightweight. Evaluate a small enabled toolset and
measured context budget first. Feature availability and model competence are
different: adding Hermes cannot make a small model reliably solve every task.

Local inference does not make every connector local. Web requests, messaging,
optional hosted memory and paid provider/tool backends require explicit choices
and credentials. Start without them. Terminal/file permissions and project memory
isolation need review at actual call sites; do not assume our scoped ToolExecutor
rules automatically apply to Hermes tools.

## Next concrete prototype

1. Pin a reviewed upstream version and install in a separate scratch environment,
   with isolated Hermes home/state and its supported Python. Preserve this repo,
   Windows baseline, model files and user database.
2. Configure only the existing loopback Ollama endpoint, no hosted fallback or
   auxiliary provider. Verify all model/summary/memory calls remain local.
3. Run the same small cases: exact READY, follow-up recall after restart, one file
   read/write with receipts, attempted path escape, cancelled task, and our known
   misrouting/coding cases. Measure actual latency, RAM/VRAM and prompt size.
4. Check project/session memory boundaries, enabled tools, cancellation semantics,
   state exports and migration. Compare a Hermes adapter with keeping our runtime.
5. Decide from that evidence. Reusing Hermes may save substantial development, but
   no compatibility/performance result or integration is claimed yet.

## Sources inspected

Official GitHub repository metadata, README and six source/document files fetched
over verified HTTPS. No downloaded installer or upstream source was executed.
Revision: `dce1e9b37581dd62e480a9064dc04a709c2940d3`.

- [Official project](https://github.com/NousResearch/hermes-agent)
- [Pinned Ollama guide](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/website/docs/guides/local-ollama-setup.md)
- [Pinned architecture](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/website/docs/developer-guide/architecture.md)
- [Pinned memory](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/website/docs/user-guide/features/memory.md)
- [Pinned skills](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/website/docs/user-guide/features/skills.md)
- [Pinned security](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/website/docs/user-guide/security.md)
- [Pinned package/runtime requirements](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/pyproject.toml)
