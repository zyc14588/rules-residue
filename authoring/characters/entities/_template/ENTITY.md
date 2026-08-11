# Entity 模板

```yaml
entity_id: entity.<slug>
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
rule_domain_refs: []
state_and_revisit_changes: []
visibility:
  public_fields: [name, public_facts]
  gm_only_fields: [true_facts]
  conditional_fields: []
```

Entity 的能力仍须通过 Rule Domain、结构化动作和 Typed Effects 表达，不能只由叙事宣告。
