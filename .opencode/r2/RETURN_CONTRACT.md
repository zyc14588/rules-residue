<!-- SECTION-ID: R2-OPENCODE-RETURN -->
# OpenCode返回合同

返回一个机器可读清单：

```yaml
task_id:
status: RETURNED|BLOCKED_INPUT|BLOCKED_AUTHORITY_CONFLICT|BLOCKED_ENVIRONMENT
input_digest:
changed_paths: []
commands:
  - command:
    exit_code:
    result:
artifacts:
  - path:
    sha256:
tests:
  - id:
    result:
unresolved: []
authority_changes: false
schema_changes: false
```

`authority_changes` 或 `schema_changes` 为true时，Codex必须拒绝该返回物。
