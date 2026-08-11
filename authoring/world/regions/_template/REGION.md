# Region 模板

```yaml
region_id: region.<slug>
status: PROVISIONAL
title: ""
public_overview: ""
persistent_state:
  state_keys: []
  initial_values: {}
  mutation_sources: []
connected_regions:
  - region_id: region.<slug>
    traversal_conditions: []
    directionality: bidirectional
resident_factions: []
resident_npcs: []
rule_domain_refs: []
safety_and_supply:
  safe_locations: []
  supply_sources: []
  limitations: []
dynamic_events: []
entry_conditions: []
exit_conditions: []
revisit_effects: []
world_state_dependencies: []
visibility:
  public_fields: [title, public_overview]
  gm_only_fields: []
```

## 检查项

- 离开 Region 不清空 `persistent_state`；
- 每条连接引用稳定 `region_id`，条件不是固定章节编号；
- Rule Domain 通过引用关联，Region 不复制其规则正文；
- 重访时明确哪些变化保留、升级或产生新事件；
- Region 不与单个 Module 一一绑定。
