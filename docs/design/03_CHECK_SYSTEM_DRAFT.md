# Check System Draft

## 公式

```text
Total = 2d6 + Approach + Proficiency + Situational Modifier
```

建议难度：

- 7：常规但存在压力；
- 9：困难；
- 11：非常困难；
- 13：极端，仅用于明确高风险场面。

## 四档结果

| 条件 | 结果 | 规则要求 |
|---|---|---|
| `Total >= Difficulty + 3` | strong_success | 完成目标并获得额外优势 |
| `Total >= Difficulty` | success | 完成声明目标 |
| `Total >= Difficulty - 2` | success_with_cost | 完成目标，同时提交明确代价 |
| 其他 | failure_with_consequence | 目标未按计划完成，局面推进并产生后果 |

## 失败推进

关键路径上的 `failure_with_consequence` 必须至少执行一项：

- 公开不完整但足以继续的事实；
- 开启备用路线；
- 推进威胁或时间；
- 增加负荷、暴露或关系代价；
- 改变场景，使新的行动成为可能。

不得把“再投一次直到成功”作为默认失败处理。

## 洞见

`spend_insight` 是自动解析动作：

- `reroll`：消耗 1 点，授予与指定动作绑定的一次重投令牌；
- `extra_information`：消耗 1 点，公开由场景预先定义、对该参与者可见的额外事实。

Agent 不能自行选择任意秘密作为额外信息；事实 ID 由宿主根据场景规则提供。
