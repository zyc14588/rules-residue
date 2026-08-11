# Faction 模板

```yaml
faction_id: faction.<slug>
status: PROVISIONAL
name: ""
public_facts: []
true_facts: []
self_beliefs: []
false_beliefs: []
known_rules:
  confirmed: []
  suspected: []
relationships: []
goals: []
region_refs: []
state_and_revisit_changes: []
visibility:
  public_fields: [name, public_facts]
  gm_only_fields: [true_facts]
  conditional_fields: []
```

派系宣传、成员共识和真实事实必须分别标记；不能把“派系声称”自动升级为确认知识。
