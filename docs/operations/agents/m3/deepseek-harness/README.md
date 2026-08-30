<!-- SECTION-ID: M3-DEEPSEEK-LITERARY-README -->
# DeepSeek Harness literary worker

This worker consumes only a validated Text Order Package and a compatible `owner=deepseek_harness`, `task_type=literary` Task Packet. It returns candidates under `workflow/returns/literary/`; it never writes Canon, authority, Schema, runtime, Lua, Game Package, or persistent state.

Entry sequence: `SESSION_START.md` → `LITERARY_PRODUCE.md` or finding-scoped `LITERARY_REPAIR.md` → `RETURN_CONTRACT.md`. Worker self-check is never final PASS.
