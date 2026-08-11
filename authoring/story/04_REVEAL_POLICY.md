# Reveal Policy

## 原则

真相不是因为作者写下、Agent 推断或玩家猜中就自动公开。揭示必须由结构化条件、已提交 Event 和参与者可见性共同决定。

```text
AUTHOR / GM ONLY truth
        ↓ 引用最小必要片段
Revelation 条件校验
        ↓
权威 Event / reveal_fact Effect
        ↓
Participant Projection
        ↓
叙事与可溯源 MemoryRecord
```

## 揭示等级

- `signal`：可观察异常，不声明原因；
- `reported`：某角色或资料的说法，可能错误；
- `inferred`：参与者根据证据形成的推断；
- `confirmed`：由正式 Event 或已确认状态支持的知识。

只有最后一类可作为 `confirmed` 记忆来源。玩家 Hypothesis 即使与真相相同，也必须经过验证和提交才能升级。

## 每次 Revelation 必须声明

- `reveal_id` 与被引用的最小 `truth_id`；
- 前置证据和可机器判断条件；
- 生成的公开/定向事实 ID；
- 可见性标签与允许受众；
- 失败推进或延后后果；
- 来源 Event 与可审计的状态变化。

禁止把整个 Truth Bible、其他参与者私密信息、内部提示词或未提交推理发送给普通 Agent。
