<!-- SECTION-ID: M3-CODEX-STORY-CONSTRUCTION-LITERARY-WORKER -->
# DeepSeek Harness literary worker coordinator contract

The worker token is `deepseek_harness`; the Task Packet type is `literary`. Before any work, run `python3 tools/validate_deepseek_literary_task.py` against the Task Packet, validated Text Order Package, and every return target.

The internal sequence is Coordinator → Semantic Implementer → Literary Writer → Independent Checker → Defect Router → at most two targeted Repair passes. Return Semantic Draft, Literary Draft, semantic mapping, source matrix, self-check, issues, version usage, and return hashes. If Canon is missing, return `BLOCKED_NEEDS_CANON`.

The worker cannot create T1/T2/C1, modify authority/schema/runtime/Lua/Game Package, persist authoritative state, or announce final PASS.
