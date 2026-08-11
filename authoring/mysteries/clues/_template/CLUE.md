# Clue 模板

```yaml
clue_id: clue.<slug>
status: PROVISIONAL
statement: ""
source:
  region_id: null
  module_id: null
  scene_id: null
supports_truth_refs: []
supports_hypotheses: []
challenges_hypotheses: []
critical: false
acquisition_conditions: []
failure_fallback: null # critical=true 时必须填写代价、替代信息或备用路径
alternate_sources: []
visibility: public
confirmation_level: reported
```

Clue 可以支持或反驳 Hypothesis，但不能单独把 Hypothesis 改写成 WorldTruth。
