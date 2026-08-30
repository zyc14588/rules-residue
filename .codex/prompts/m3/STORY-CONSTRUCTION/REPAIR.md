<!-- SECTION-ID: M3-CODEX-STORY-CONSTRUCTION-REPAIR -->
# M3 Story Construction REPAIR

REPAIR consumes only accepted finding IDs and their minimal evidence. It changes only the finding-scoped allowlist, does not re-plan or relax Schema/tests, and produces a new candidate identity. All earlier candidate approvals and acceptance evidence become invalid.

Literary repair remains limited to at most two targeted worker repair passes. Missing Canon returns `BLOCKED_NEEDS_CANON`; REPAIR cannot invent authority or content.
