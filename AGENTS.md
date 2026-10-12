# Project working instructions

- Use the existing checkout. Do not create a worktree unless the user asks.
- Git commits must use `Naveen-145119 <naveenreddy91590@gmail.com>` for author and
  committer. Verify the repository-local identity before committing; never rewrite
  published history just to change attribution without an explicit request.
- The user's current RTX 3050 6 GB laptop is the first local deployment target.
  The office Dell is unavailable and must not block development. Hardware details
  in the original handoff are reported specifications, not live measurements.
- Keep the general-purpose feature roadmap open. Recruitment, marketing,
  development and SEO are examples, not the complete agent catalog.
- Preserve host portability: separate application source, private user data,
  credentials, model artifacts and host-specific runtime settings.
- Read `docs/deployment/portable-windows.md` for the current deployment contract and
  `docs/roadmap/2026-10-10-evolving-platform.md` for proposed capabilities.
- Report Linux/cloud checks separately from actual Windows/GPU execution. Do not
  claim a proposed feature or unrun hardware check works.
- ModelArk must introduce no paid usage. The user reported account-level Free
  Tokens Only mode On on 12 October 2026; this is user-host evidence, not a live
  account query. Keep the candidate disabled during preparation. Before any live
  use, verify protection belongs to the intended account/project and supported
  model; use plain online inference only. Do not disable free-only protection,
  enroll in data-reward campaigns that require disabling it, purchase Coding Plans,
  enable paid plugins/managed agents/knowledge bases/storage/model units, or use
  media generation. Do not treat displayed credits, rate limits or client counters
  as a guarantee against charges. Never ask for secret API keys in chat.
- The user connected an HDD as E: and reports 93.84 GiB free on C: after manual
  cleanup. Original D: checkout/private-state availability remains unverified.
  Preserve C:\Gov Proj and the E: Docker backup. The user removed Docker; the core
  Python/Ollama platform does not require it. Check paths/free space read-only before
  restoring or installing. A Git clone recovers source, not private conversations,
  files, model weights or virtual environments. Preserve any existing state.
