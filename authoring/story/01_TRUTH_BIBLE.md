<!-- SECTION-ID: M1-AUTHORING-TRUTH-BIBLE -->
# Truth Bible — AUTHOR / GM ONLY

本文件是终极与跨域真相的创作登记容器。它不得整体进入 Game Package、玩家投影或 AI GM 默认上下文。运行时 `WorldTruth` 仍必须经过结构化、最小化和按参与者投影。

## 当前决定状态

以下 M1 问题容器的历史状态为 `SUPERSEDED_BY_R2`，不再是 ACTIVE `OPEN`：

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

本节保留 M1 历史来源。当前唯一 ACTIVE 主真相为后续 `TRUTH-R2-001..012`；未冻结细节仅由 `governance/r2/deferred-items.r2.yaml` 继续登记。

<!-- SECTION-ID: R2-AUTHORING-TRUTH-BIBLE -->
# Truth Bible

> `AUTHOR / GM / MECHANICAL ONLY`
> 禁止整体进入玩家包、普通NPC Agent或无关施工代理上下文。

## 固定真相节点

| Truth ID | 真相 | 依赖 | 可揭示阶段 |
|---|---|---|---|
| `TRUTH-R2-001` | 大陆是高维世界坍缩后的维度残片 | 无 | 建模期 |
| `TRUTH-R2-002` | 大陆正在与现实及其他世界发生异常纠缠 | 001 | 求生后期/建模 |
| `TRUTH-R2-003` | 主角团只是被碰撞扫中的普通人 | 002 | 早期 |
| `TRUTH-R2-004` | 纠缠因果来自穿越碰撞 | 002,003 | 早期至中期 |
| `TRUTH-R2-005` | 角色1是因果律武器表现载体 | 001 | 建模后期 |
| `TRUTH-R2-006` | 角色1以文明延续为最高使命，会牺牲主角团 | 005 | 干预期 |
| `TRUTH-R2-007` | Boss是失败主角团、牺牲者、维护者与扭曲因果聚合体 | 001,002 | 干预/终局 |
| `TRUTH-R2-008` | Boss既制造灾难又维持稳定 | 007 | 干预期 |
| `TRUTH-R2-009` | 关键道具是外部悖论奇点制成的因果炸弹 | 003,004,005 | 建模后期 |
| `TRUTH-R2-010` | 错误引爆会将整个大陆判定为悖论并摧毁 | 008,009 | 终局前可重建 |
| `TRUTH-R2-011` | 真结局要求六区观测、道具完整、角色1存活与Boss正确分离 | 005,007,009 | 终局诊断 |
| `TRUTH-R2-012` | 正确引爆可切断纠缠，回归现实只能被接纳为共同梦境 | 011 | 结局 |

## 泄漏限制

- 单一文档不得一次完整给出001—012。
- 角色1不会主动完整解释005、006、009、010。
- Boss不同人格可以分别持有互相冲突但局部真实的信息。
- 六区观测必须各自提供最终校准必要维度的一部分。
- 外部攻略不能改变真相，但种子可改变证据载体、身份映射、来源组合和操作排列。
