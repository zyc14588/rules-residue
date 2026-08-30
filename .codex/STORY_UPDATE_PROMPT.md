> SUPERSEDED — LITERARY_TASK_ISSUANCE=FORBIDDEN
>
> 当前入口：`.codex/prompts/m3/STORY-CONSTRUCTION/README.md`。本文件仅为历史证据，不得签发文学任务或承担现行治理权威。

# 《规则残差》剧情更新与一致性传播提示词

> 用途：剧情架构建立后，每次新增、修改、删除或重构剧情时使用。它不是“帮我续写”的自由创作提示词，而是把项目所有者给出的剧情决定安全、可追溯地写入开放世界内容体系，并判断是否需要运行时/脚本/美术跟进。

---

你正在《规则残差》仓库处理一次**剧情变更**。保持“无限流 × 规则怪谈 × 异世界开放世界”的产品定位，以及“破解规则、努力活着、查清真相、寻找回家方法”的长期主题。

## 本次剧情变更

`<在这里粘贴我的新增/修改/删除剧情要求。可以是自然语言、设定片段、NPC、区域、规则怪谈、线索、真相、支线或重写要求。>`

可选约束：

- 必须保留：`<可空>`
- 必须删除/废弃：`<可空>`
- 仅影响范围：`<可空>`
- 是否允许改变运行时规则：`<默认：只有明确必要时>`
- 是否需要美术：`<默认：由 Codex 判断并生成 Grok Task Packet，不直接生成素材>`

## Phase 0 — 先读事实，不按聊天记忆续写

读取：

1. `AGENTS.md`、`README.md`；
2. governance 中相关 `ACCEPTED / PROVISIONAL / OPEN` 决策；
3. `authoring/story/` 中相关 Story Bible、Truth Bible、Mystery Graph、Return Home Arc、Reveal Policy；
4. 受影响 Region / Rule Domain / Arc / Module / NPC / faction / clue；
5. 若已有 runtime 实现，再读对应 `game-package/` Module、rules、Schema、Lua、assets、tests；
6. 相关 Task Packet 与已有 provenance。

先运行：

```bash
python3 tools/run_acceptance.py
```

若基线失败，保留失败证据，不把无关故障悄悄混入剧情变更。

## Phase 1 — 对变更分类

将用户输入拆成下列一个或多个类型：

- `WORLD_TRUTH`：世界真实事实/终极设定；
- `STORY_BIBLE`：主题、体验承诺、长期方向；
- `MYSTERY_GRAPH`：真相节点、证据、错误假设、揭示条件；
- `RETURN_HOME_ARC`：归乡调查链与选择；
- `REGION`：持久开放世界区域；
- `RULE_DOMAIN`：规则域及规则破解；
- `ARC`：主线/支线/角色/世界事件；
- `MODULE`：可运行内容单元；
- `NPC_FACTION_ENTITY`；
- `CLUE_HYPOTHESIS_REVELATION`；
- `ART_BRIEF`；
- `RUNTIME_RULE`：需要 Schema/Lua/状态语义变化；
- `RETCON`：会否定或替换既有事实的追溯性改写。

输出影响图：**直接变更 → 引用者 → runtime → tests → art → save compatibility**。

## Phase 2 — 冲突与决策门禁

对每个变更先判断：

1. 是否与 `ACCEPTED` 决策冲突；
2. 是否会把 `OPEN` 事项静默决定；
3. 是否与既有 Truth Bible / Region / NPC / clue 矛盾；
4. 是否改变已经发布或可能存在存档的 runtime state；
5. 是否会导致玩家/AI 提前获得 GM-only 真相。

### 处理规则

- 用户本次明确给出的事实可以作为本次设计输入，但若它改变现有 `ACCEPTED` 机器决策，必须先走 `governance/CHANGE_CONTROL.md`，不得偷偷覆盖；
- 用户没有明确决定的终极世界真相、规则来源、无限流来源、真正回家条件继续保持 OPEN；
- 若存在矛盾，先生成 **Conflict Table**：旧事实、新事实、引用位置、影响、推荐的最小一致化方式；
- 不得把模糊新设定自动扩写成大量不可逆 lore；
- 若为 RETCON，旧内容应明确 superseded/deprecated，而不是让两个版本同时作为真相存在。

## Phase 3 — 先更新 authoring 创作源

按对象写到正确位置，不把所有剧情塞进一个 Module：

- 世界主题 → `authoring/story/00_STORY_BIBLE.md`
- GM-only / 真相 → `authoring/story/01_TRUTH_BIBLE.md`
- 真相节点与证据关系 → `authoring/story/02_MAIN_MYSTERY_GRAPH.md`
- 归乡结构 → `authoring/story/03_RETURN_HOME_ARC.md`
- 揭示/泄漏边界 → `authoring/story/04_REVEAL_POLICY.md`
- 区域 → `authoring/world/regions/...`
- 规则域 → `authoring/world/rule-domains/...`
- Arc → `authoring/arcs/...`
- Module 设计 → `authoring/modules/...`
- NPC/faction/entity → `authoring/characters/...`
- clue/hypothesis/revelation → `authoring/mysteries/...`
- 美术需求 → `authoring/art/briefs/...`

保持引用 ID 稳定。能修改内容就不要无必要重命名 ID；删除对象前先检查所有引用。

## Phase 4 — 保持开放世界与规则怪谈特性

剧情更新必须通过以下检查：

### 开放世界

- Region 是可重访的持久空间，不是一次性副本；
- Module 只是内容单元，不等于 Region 或 Campaign；
- 新剧情不要无必要强制唯一章节顺序；
- 允许不同路线到达相同 Truth Node；
- 世界事件可以改变 Region / Rule Domain 状态，并在重访时体现。

### 无限流

- 无限流是世界结构/迁移/规则空间关系，不默认退化成菜单式副本列表；
- Rule Domain 可以展开、重叠、嵌套、迁移、融合或被破解后永久改变；
- “通过当前规则域”不等于 Campaign 通关或回家。

### 规则怪谈

新增正式规则时至少定义：

```text
scope
trigger
conditions
effects
exceptions
priority
conflicts
visibility
break_conditions
persistence
rule_evidence
false_signals
```

玩家应有机会通过观察、假设、低风险验证、反证、利用和破解来理解规则，而不是只接受 GM 公布答案。

### 失败推进

- 关键路径失败必须改变代价/威胁/信息质量/路线，而不是卡死；
- 可选秘密、奖励和支线允许永久错过；
- 不用无限重复同一检定伪装“失败也能推进”。

## Phase 5 — 决定是否传播到 runtime

不是所有剧情文字变化都需要立刻修改 `game-package/`。

### 仅 authoring

如果是未进入可玩内容的未来设定、真相规划、远期 Arc，只更新创作源和索引/引用，不制造无意义 runtime 占位。

### 需要 runtime 数据

如果内容已进入或马上进入可玩 Module：

- Codex 更新/规划结构化 scenario/rules/manifest/schema/fixture；
- 确保 visibility、failure fallback、exits、local endings 和 world-state effects 可执行；
- 保持 `authoring` 与 runtime 之间有可追踪 ID，不复制成互相无法判断谁新的两套故事。

### 需要 Lua

若需要新的脚本行为：

1. Codex 先固定 Schema、输入输出、fixture、验收向量；
2. 生成 `owner=opencode` 的合法 Task Packet；
3. `allowed_paths` 只给真正需要的脚本/test/fixture；
4. OpenCode 不得修改 Truth Bible、governance 或产品决策；
5. Codex 在返回后独立复验。

### 需要美术

若需要视觉资产：

1. 在 `authoring/art/briefs/` 形成明确 brief；
2. 生成 `owner=grok` 的 Task Packet；
3. 写明用途、主体、环境、构图、尺寸/比例/格式、禁止内容、文件名、输出目录、provenance；
4. 不要求模仿在世艺术家的具体风格；
5. Codex 验证技术规格和 provenance，最终审美采用由项目所有者决定。

## Phase 6 — RETCON 与存档兼容

如果变更会推翻已有运行事实：

- 列出受影响的 Module / event / state field / save；
- 判断属于：`AUTHORING_ONLY`、`NEW_CAMPAIGNS_ONLY`、`BACKWARD_COMPATIBLE`、`REQUIRES_MIGRATION`、`BREAKING`；
- 没有已批准的存档迁移接口时，不得擅自实现不可逆迁移；
- 不得为新剧情悄悄重解释旧事件日志；
- 若只能影响新 Campaign，明确记录版本边界。

## Phase 7 — 一致性传播检查

至少检查并按需要同步：

- Story Bible；
- Truth Bible；
- Mystery Graph；
- Reveal Policy；
- Region index / connections；
- Rule Domain references / conflicts；
- Arc prerequisites；
- Module source；
- NPC knowledge / false beliefs；
- clue / hypothesis / revelation；
- runtime Module；
- localization；
- art brief / provenance；
- tests / Golden vectors；
- governance / traceability（仅在确有已批准决策变化时）。

禁止“只改一个文档，留下所有引用继续指向旧事实”。

## Phase 8 — 验收

如果修改了运行输入：

```bash
python3 tools/update_lock.py
```

然后：

```bash
python3 tools/run_acceptance.py
python3 tools/build_package.py
python3 tools/run_acceptance.py
```

如果只修改 authoring，也至少运行仓库 acceptance，确保 authoring 结构/引用检查仍通过。

检查：

```bash
git diff --check
git status --short
```

对剧情变化增加任务特有检查，例如：

- 新关键 clue 的 fallback；
- 新 Truth Node 的 reveal prerequisite；
- 新 Rule Domain 冲突优先级；
- 玩家投影不泄漏新 GM-only truth；
- 新 Module 已注册且被通用 validator 覆盖；
- RETCON 不留下双重真相引用。

## 最终输出格式

### Result
`PASS_LOCAL / FAIL / BLOCKED_DECISION / BLOCKED_EXTERNAL`

### Change classification
列出本次变更类型。

### Conflict table
若无冲突写 `None`；若有，逐项列旧事实、新事实、影响和处理。

### Authoring changes
逐文件说明改变了什么剧情事实。

### Runtime propagation
- 不需要 / 已完成 / 待 OpenCode / 被外部接口阻塞。

### OpenCode tasks
列 Task ID、目标、允许路径、验收；没有则写 `None`。

### Grok tasks
列 Task ID、brief、输出路径、provenance 要求；没有则写 `None`。

### Save compatibility
给出分类和理由。

### Verification
列实际命令、退出码和关键结果。

### Remaining OPEN
明确哪些世界真相/规则来源/无限流来源/归乡条件仍未决定，防止后续模型误以为已经冻结。
