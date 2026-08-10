# 04 — Rules and State Model

## 1. 权威对象

- `CampaignState`：跨 Session 持久状态；
- `SessionState`：当前场景、阶段、顺序和临时效果；
- `CharacterState`：方法值、熟练、资源、状态与归属；
- `WorldTruth`：场景秘密、NPC 真相、未公开线索和威胁；
- `Event`：每次已提交变化的不可变记录；
- `Projection`：面向某一参与者的可见状态；
- `MemoryRecord`：从已确认事件派生的 Agent 记忆。

## 2. 结构化动作

动作最少包含：动作 ID、Actor、动作类型、目标、目标描述、采用方法、风险声明、参数、客户端可见性与幂等键。自由文本只作为解释字段，不能直接表达任意状态补丁。

## 3. 两阶段解析

1. `plan_action` 校验动作，并返回随机请求或资源消耗请求；
2. 宿主产生并记录权威随机或批准资源消耗；
3. `resolve_action` 只根据不可变输入生成 Typed Effects；
4. 宿主验证 Effects，原子提交状态、事件和 Outbox；
5. 提交成功后才能生成叙事。

## 4. Typed Effects 最小集合

- `append_event`
- `adjust_resource`
- `set_status`
- `clear_status`
- `reveal_fact`
- `advance_track`
- `set_flag`
- `grant_reroll_token`

所有 Effect 必须带原因、来源动作和可见性；宿主可以拒绝越权、越界或引用无效对象的 Effect。`intent_shifted` 可以在规则判定成功后替代目标角色的部分行动，但 P0 最多替代下一次单一行动，且必须把替代动作和期限写入状态。

## 5. 随机与回放

Lua 不调用随机 API。宿主记录骰面、修正、难度、总值、规则版本和结果档位。相同状态、动作和随机输入必须产生语义等价的 Effects。

## 6. 草案检定

`2d6 + 方法值 + 熟练 + 情境修正` 对比难度：

- `>= 难度 + 3`：强成功；
- `>= 难度`：成功；
- `>= 难度 - 2`：付出代价的成功；
- 其他：带后果的失败。

该数值属于 `PROVISIONAL`，但四档结果和失败推进属于 P0 验收合同。
