# Content Model Draft

《规则残差》的内容单位不是单纯“场景脚本”，而是**持久世界中的规则域内容**。

每个规则域/场景包至少描述：

- `metadata`：身份、版本、人数、主持模式、所属世界区域；
- `keeper_truth`：只有获授权 GM/运行时可见的真实前提；
- `rules`：该区域的真实规则、作用域、触发条件、效果、例外、优先级与可破解状态；
- `rule_evidence`：能够支持或反驳规则假设的观察；
- `scenes`：局部地点、目标、关键路径、出口和可交互目标；
- `npcs`：公开描述、秘密、初始意图、所知规则与可能的错误认知；
- `clues`：事实、来源、是否关键、可见性；
- `timeline`：随事件或时间推进的变化；
- `threats`：有界轨道；
- `exits`：离开当前规则域的方式以及通往世界其他地点的结果；
- `endings`：仅表示当前内容单元的收束，不默认结束 Campaign；
- `safety_notes`：内容提示和可替换元素；
- `visibility`：默认与例外投影规则。

关键线索必须声明 `failure_fallback`。可选线索可以没有备用获取路径。

## 规则对象最小语义

即使 P0 仍用现有 Scenario Schema 承载部分内容，后续正式 Rule Schema 至少必须能够表达：

```text
rule_id
scope
trigger
conditions
effects
exceptions
priority
conflicts_with
visibility
break_conditions
persistence
```

不得仅以一段自然语言文本作为机器执行规则的唯一来源。
