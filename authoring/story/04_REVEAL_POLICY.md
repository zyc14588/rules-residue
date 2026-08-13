<!-- SECTION-ID: M1-AUTHORING-REVEAL-POLICY -->
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

<!-- SECTION-ID: R2-AUTHORING-REVEAL-POLICY -->
# Reveal Policy

## 信息层

| 层 | 内容 | 默认访问者 |
|---|---|---|
| `PUBLIC_WORLD` | 玩家当前可见文本、环境与行为 | 相关玩家 |
| `CHARACTER_PRIVATE` | 私人幻觉、纠缠因果、隐藏状态 | 对应席位 |
| `PARTY_SHARED` | 玩家主动分享和队伍公共档案 | 当前队伍 |
| `HOST_ONLY` | 真实因果、NPC真实认知、种子答案 | 主持人/受限工具 |
| `MECHANICAL_ONLY` | 定义域、权限、效果、结局条件 | 规则引擎 |
| `AUDIT_ONLY` | 来源、安全、候选、验收 | 独立审计 |

## 规则

- 玩家可见文本不得含内部可靠状态、真伪或终局用途标签。
- AI主持只获得当前场景、当前席位和必要机械结果。
- OpenCode只获得脚本任务需要的语义、Schema和fixture，不读取完整Truth Bible。
- Grok只获得美术brief、公开视觉需求和必要秘密遮蔽说明，不读取完整种子。
- 团灭信息提高已存在信息的精度，不生成新真相。
- 结局因果审计只公开与当前结局直接有关的缺口，不揭露未探索内容。
