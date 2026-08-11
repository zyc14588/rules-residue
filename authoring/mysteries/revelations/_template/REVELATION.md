# Revelation 模板

```yaml
reveal_id: reveal.<slug>
status: PROVISIONAL
truth_ref: truth.<slug>
minimum_truth_fragment: ""
prerequisite_clues: []
conditions: []
projected_fact_ids: []
visibility: public
allowed_audiences: []
effect_contract:
  effect_type: reveal_fact
  event_type: ""
failure_forward: []
consequences: []
memory_source_required: true
```

`minimum_truth_fragment` 只描述本次允许公开的片段；不得用 Revelation 把整个 Truth Bible 注入 Agent 上下文。
