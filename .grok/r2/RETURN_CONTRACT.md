<!-- SECTION-ID: R2-GROK-RETURN -->
# Grok返回合同

```yaml
task_id:
asset_id:
status: RETURNED|BLOCKED_INPUT|BLOCKED_AUTHORITY_CONFLICT|BLOCKED_ENVIRONMENT
brief_digest:
files:
  - path:
    role: SOURCE|EXPORT|METADATA
    sha256:
    dimensions:
rights:
  original: true
  third_party_assets: []
safety:
  policy_id: R2-CONTENT-SAFETY-001
  result: PASS|FAIL
accessibility_notes: []
self_review_findings: []
authority_changed: false
```

`authority_changed=true` 或 `safety.result=FAIL` 时必须拒绝集成。
