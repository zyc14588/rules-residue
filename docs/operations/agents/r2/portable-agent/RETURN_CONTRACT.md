<!-- SECTION-ID: R2-PORTABLE-RETURN -->
# Portable Agent返回合同

```json
{
  "schema_version": "1.0",
  "role": "PLANNER|BUILDER|VERIFIER|REPAIR|SCRIPT_WORKER|ART_WORKER",
  "result": "PASS|FAIL|BLOCKED_EXTERNAL|BLOCKED_ENVIRONMENT|BLOCKED_DESIGN_CONFLICT",
  "source_commit": "<40hex>",
  "candidate_commit": "<40hex-or-null>",
  "route_binding": "<sha256>",
  "changed_paths": [],
  "commands": [],
  "evidence": [],
  "findings": [],
  "next_allowed_action": ""
}
```

不要包含私密思维链。
