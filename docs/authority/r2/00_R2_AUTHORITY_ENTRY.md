<!-- SECTION-ID: R2-AUTH-ENTRY -->
# 《规则残差》R2 权威设计入口

状态：`FROZEN`
权威语言：简体中文
冻结决策范围：`R2-A01`—`R2-J24`
决策数量：`191`

## 权威顺序

```text
governance/r2/decisions.r2.yaml
    >
本目录规范术语与系统级权威文档
    >
authoring中的Truth/Story/Region源
    >
runtime Schema、数据与Lua
    >
玩家可见表现文本、音频与美术
    >
示例与创作参考
```

任何低层实现与高层决策冲突时，低层内容无效。

## 阅读地图

| 主题 | 文档 |
|---|---|
| 玩家体验与公平契约 | `01_GAME_VISION_AND_PLAYER_CONTRACT.md` |
| 高维残片、角色1、Boss、共同梦境 | `02_WORLD_AND_MAIN_TRUTH.md` |
| 规则、残差、循环、死亡、代价 | `03_RULE_CAUSALITY_LOOP_AND_COST.md` |
| 主角团、能力、装备、成长、信息 | `04_CHARACTER_EQUIPMENT_AND_GROWTH.md` |
| 六大区、阵营、地图、逃课与锚点 | `05_CONTINENT_REGIONS_AND_FACTIONS.md` |
| Boss战、三分支、终局判定与回归 | `06_FINAL_BOSS_ENDINGS_AND_RETURN.md` |
| 战役节奏、主持权威、AI与多人 | `07_CAMPAIGN_HOSTING_AND_RUNTIME.md` |
| 2D视听、文本声部、地图与可访问性 | `08_VISUAL_AUDIO_AND_TEXT_STYLE.md` |
| 内容边界与绝对红线 | `09_CONTENT_SAFETY_AND_ABSOLUTE_RED_LINES.md` |
| 全内容交叉验证与发布门禁 | `10_CONTENT_VALIDATION_AND_RELEASE_GATES.md` |
| M2垂直切片输入 | `11_M2_IMPLEMENTATION_INPUT_CONTRACT.md` |
| 延期事项 | `12_DEFERRED_DECISIONS_REGISTER.md` |
| 变更控制 | `13_CHANGE_CONTROL_POLICY.md` |
| M1工程基础适配 | `14_M1_INTEGRATION_CONTRACT.md` |
| 全部冻结决策 | `R2_DECISION_INDEX.md` |
| 规范术语 | `R2_TERMINOLOGY.md` |
| 决策到文档/Schema/验收追踪 | `R2_TRACEABILITY.md` |

## 玩家/主持/机械层

- **玩家层**：只能看到其角色可确认的世界内信息、规则文本、可观察结果和已授权辅助界面。
- **主持层**：可读取完整地图、隐藏因果、NPC真实认知、种子答案和审计解释，但不得改变开局已固定真相。
- **机械层**：保存规范语义、状态机、规则冲突、权限、种子、事件和验收事实。
- **审计层**：记录来源、版本、执行证据、安全过滤、候选SHA与验收结论。

## 不可推导原则

以下内容不得被实现者用常见做法自行补全：

- 通用代价精确数值；
- 记忆主张可信度与UI；
- 自建锚点成本算法；
- 2—6人精确缩放公式；
- 真结局后高资源开局数值；
- 六个正式大区的具体主题和剧情；
- 逻辑完全异常区的最终谜题；
- 角色1外观、名字与具体台词；
- 最终Boss各人格的正式身份清单。

这些进入延期登记或后续内容设计，不改变已经冻结的边界。
