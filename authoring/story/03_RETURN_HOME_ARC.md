# Return Home Arc — AUTHOR / GM ONLY

“回家”是长期调查、验证与选择结构，不是默认的固定最终任务。真正归乡条件仍为 `OPEN`。

## 阶段槽位

这些槽位描述依赖类型，不规定唯一顺序、地点或答案：

1. `orientation`：确认“离开局部 Rule Domain”与“返回原世界”不同；
2. `cross_domain_evidence`：从多个持久 Region 获得可互证信息；
3. `candidate_models`：形成一个或多个可反驳的归乡假设；
4. `route_validation`：验证候选路线的条件、代价、例外和冲突；
5. `commitment`：在已确认信息允许时作出选择并承担持久后果；
6. `aftermath`：记录结果对世界、角色和未完成谜题的影响。

阶段可以并行、回退或被世界状态重新打开，不构成固定章节链。

## 阶段条目合同

```yaml
stage_id: return-stage.<slug>
status: OPEN
entry_conditions: []
truth_dependencies: []
evidence_requirements: []
candidate_hypotheses: []
available_choices: []
costs_and_risks: []
world_state_changes: []
failure_forward: []
next_stage_conditions: []
```

不得在所有者关闭相关 `OPEN` 决策前填写唯一归乡条件、唯一正确路线或终局世界解释。
