# Rule Domain 模板

核心规则不得只写成自然语言怪谈。以下字段在提升为 runtime 数据时必须映射到可校验结构。

```yaml
rule_domain_id: domain.<slug>
status: PROVISIONAL
title: ""
scope:
  region_refs: []
  included_targets: []
  excluded_targets: []
trigger: []
conditions: []
rules:
  - rule_id: rule.<slug>
    scope: {}
    trigger: []
    conditions: []
    effects: []
    exceptions: []
    priority: 0
    conflicts: []
    visibility: gm_only
    break_conditions: []
    persistence: persistent
effects: []
exceptions: []
priority: 0
conflicts:
  - other_rule_or_domain_id: ""
    resolution: ""
visibility:
  default: gm_only
  observable_signals: []
break_conditions: []
persistence:
  mode: persistent
  state_keys: []
rule_evidence: []
false_signals: []
world_changes_after_break: []
```

## 检查项

- `scope` 能表达相邻、嵌套、重叠或迁移后的生效范围；
- `priority` 与 `conflicts` 给出确定性裁定依据，不能留给 Agent 任意选择；
- `rule_evidence` 支持验证与反证，`false_signals` 不得伪装成 confirmed fact；
- 破解必须有条件、代价和持久世界变化；
- 随机请求由宿主权威产生，规则设计不得要求 Lua 自行随机。
