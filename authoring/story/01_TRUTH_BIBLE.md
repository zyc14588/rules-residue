# Truth Bible — AUTHOR / GM ONLY

本文件是终极与跨域真相的创作登记容器。它不得整体进入 Game Package、玩家投影或 AI GM 默认上下文。运行时 `WorldTruth` 仍必须经过结构化、最小化和按参与者投影。

## 当前决定状态

以下问题保持 `OPEN`，本任务未填写答案：

- 异世界为何存在；
- 规则由谁或什么产生；
- 无限流结构的来源；
- 完整世界地理、组织和跨域历史；
- 真正归乡条件及其代价。

## 条目合同

```yaml
truth_id: truth.<slug>
status: OPEN # OPEN | PROVISIONAL | ACCEPTED
statement: null # OPEN 时保持 null 或只写待决定问题，不填写答案
owner_decision_refs: []
dependencies: [] # truth_id 列表
referenced_by_reveals: [] # reveal_id 列表
related_regions: []
related_rule_domains: []
leakage_restrictions:
  default_visibility: gm_only
  include_in_default_ai_gm_context: false
  allowed_projection_conditions: []
  forbidden_audiences: [player, ai_player, summary_agent]
notes: ""
```

## 状态规则

- `OPEN`：只有问题容器，不得被实现者补全；
- `PROVISIONAL`：必须有明确授权来源，可供垂直切片试用但不得冒充冻结事实；
- `ACCEPTED`：必须引用已完成的变更控制或所有者决定；
- 修改状态时同步检查 Mystery Graph、Revelation、运行数据和泄漏边界。

## 已登记真相

当前无终极真相条目。局部 Module 的 keeper truth 留在各自内容设计中，不自动成为跨世界终极答案。
