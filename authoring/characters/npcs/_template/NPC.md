# NPC 模板

```yaml
npc_id: npc.<slug>
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
state_and_revisit_changes: []
visibility:
  public_fields: [name, public_facts]
  gm_only_fields: [true_facts]
  conditional_fields: []
```

`self_beliefs` 和 `false_beliefs` 是角色认知，不得写成 WorldTruth 或玩家 confirmed knowledge。
