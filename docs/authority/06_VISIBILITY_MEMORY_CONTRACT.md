# 06 — Visibility and Memory Contract

## 数据域

| 数据域 | 权威性 | 典型读者 | 可否直接发给普通 Agent |
|---|---:|---|---:|
| World Truth | 是 | 权威运行时、获授权 GM | 否 |
| Event Log | 是 | 按事件可见性投影 | 仅投影后 |
| Participant Projection | 派生 | 指定参与者 | 是 |
| Agent Memory | 派生 | 指定 Agent | 是，需来源有效 |
| Context Summary | 派生 | 指定 Agent | 是，需版本与来源 |
| Narration | 否 | 指定观众 | 是 |

## 可见性标签

P0 使用：

- `public`
- `gm_only`
- `participant:<id>`
- `team:<id>`
- `agent:<id>`

未知标签必须 fail closed。

## 记忆记录

每条 `MemoryRecord` 至少包含：

- `memory_id`
- `subject_id`
- `statement`
- `source_event_ids`
- `visibility`
- `confidence`：`confirmed` / `reported` / `inferred`
- `created_at_event_index`
- `supersedes`

只有来自正式 Event、裁定、骰子和已确认状态变化的信息可以标记为 `confirmed`。

## 压缩规则

- 不合并不同可见性域；
- 不把 GM-only 信息压入玩家摘要；
- 不删除改变当前决策的重要代价、承诺或未解决威胁；
- 摘要可被重建和作废；
- 存档恢复以状态与事件重建摘要，而不是以摘要重建状态。
