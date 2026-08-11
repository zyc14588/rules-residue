# Authoring Module 模板

```yaml
module_id: module.<slug>
status: PROVISIONAL
title: ""
region_refs: []
rule_domain_refs: []
arc_refs: []
entry_conditions: []
scenes:
  - scene_id: scene.<slug>
    critical_path: false
    exits: []
npc_refs: []
clue_refs: []
timeline: []
threats: []
exits:
  - destination_region_id: region.<slug>
    conditions: []
local_endings: []
critical_path_fallbacks: []
safety_notes: []
visibility:
  default: public
  gm_only_fields: []
runtime_mapping:
  target_path: null
  schema_version: null
  script_task_ids: []
  art_task_ids: []
```

每条关键 Clue 或关键出口必须有代价、替代信息或备用路线。`local_endings` 只收束本内容单元，不默认表示回家或 Campaign 结束。
