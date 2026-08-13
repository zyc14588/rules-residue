<!-- SECTION-ID: R2-AUTH-CHANGE-CONTROL -->
# R2 变更控制

## 需要变更控制的情况

- 修改任何 `R2-A01—R2-J24`；
- 改变三分支、角色1死亡、关键道具本质；
- 改变循环继承白名单或通用代价所有权；
- 降低逻辑完全异常区约束；
- 删除六区观测最低条件；
- 扩大AI生成机械权限；
- 修改绝对红线；
- 改变战役种子不可变性。

## 变更记录字段

```yaml
change_id:
proposer:
reason:
old_decisions: []
new_statement:
affected_documents: []
affected_schemas: []
affected_authoring: []
affected_runtime: []
affected_tests: []
save_compatibility:
security_and_safety_impact:
reacceptance_scope:
approval_status:
```

## 状态

```text
PROPOSED
→ IMPACT_REVIEWED
→ APPROVED / REJECTED
→ IMPLEMENTED
→ INDEPENDENTLY_ACCEPTED
```

未完成独立验收的变更不得覆盖权威基线。

## Retcon

剧情重写必须保留旧对象ID并标记 `SUPERSEDED`，通过 `replaced_by` 指向新对象。不得删除历史后复用ID。
