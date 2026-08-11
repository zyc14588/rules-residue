# Arc 模板

```yaml
arc_id: arc.<slug>
type: side # main | side | character | world-event
status: PROVISIONAL
public_premise: ""
truth_refs: []
entry_conditions: []
world_state_dependencies: []
nodes:
  - node_id: arc-node.<slug>
    conditions: []
    module_refs: []
    choices: []
    state_changes: []
    failure_forward: []
branches: []
completion_conditions: []
abandonment_or_expiry_conditions: []
consequences: []
visibility:
  default: public
  gm_only_fields: [truth_refs]
```

节点连接必须由条件表达；文件顺序不等于游玩顺序。局部完成不自动结束 Campaign。
