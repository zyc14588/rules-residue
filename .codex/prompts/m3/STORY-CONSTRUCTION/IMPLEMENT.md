<!-- SECTION-ID: M3-CODEX-STORY-CONSTRUCTION-IMPLEMENT -->
# M3 Story Construction IMPLEMENT

IMPLEMENT consumes one frozen Task Envelope in a dedicated worktree. It modifies only the printed allowlist, preserves R2/M2, validates orders before dispatch, and treats every worker return as an untrusted candidate.

Literary work requires `owner=deepseek_harness`, `task_type=literary`, a validated Text Order Package, exact input/order hashes, and the controlled return namespace. Visual work requires a validated Visual Order Package; raw art requests are rejected. OpenCode remains `owner=opencode`, `task_type=script`, within its existing Lua/fixture default-deny boundary.

IMPLEMENT may assemble one candidate after all builder-side gates pass. It cannot self-ACCEPT, activate governance, bind its future commit/tree inside tracked artifacts, or push/merge/open a PR without separate authorization.
