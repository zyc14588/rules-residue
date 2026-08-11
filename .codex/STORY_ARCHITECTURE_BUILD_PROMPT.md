# 《规则残差》M1-CONTENT-ARCHITECTURE 剧情架构构建提示词

> 用途：正式大量写剧情前执行一次。目标是建立 `authoring/` 创作源层、开放世界内容边界和任意 Module 自动验收，不负责替项目所有者编写最终世界真相。

---

你正在《规则残差》独立第一方游戏仓库执行 **M1-CONTENT-ARCHITECTURE**。

## 目标

把当前“Tutorial/Golden 驱动的初始化包”升级为适合长期维护以下内容的剧情架构：

- 无限流；
- 规则怪谈；
- 异世界开放世界；
- 持久 Region；
- 可叠加/嵌套/冲突的 Rule Domain；
- 非线性 Main Mystery Graph；
- 长期“查清真相并回家”Arc；
- 大量 Module / NPC / faction / clue / world event；
- Codex → OpenCode/Grok → Codex 混合施工。

**不要在本任务中替用户决定最终世界真相、无限流来源、规则来源或真正归乡条件。** 这些若仍为 OPEN，只建立容器、索引、模板和泄漏边界。

## Phase 0 — 基线

读取并遵守：

- `AGENTS.md`
- `README.md`
- `governance/decisions.json`
- `governance/scope.json`
- `docs/authority/03_DESIGN_PRINCIPLES.md`
- `docs/authority/04_RULES_AND_STATE_MODEL.md`
- `docs/authority/06_VISIBILITY_MEMORY_CONTRACT.md`
- `docs/authority/07_GAME_PACKAGE_CONTRACT.md`
- `docs/authority/08_TUTORIAL_AND_GOLDEN.md`
- `docs/authority/09_ACCEPTANCE_STANDARD.md`
- `docs/authority/10_OPEN_DECISIONS.md`
- `docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md`
- `docs/design/05_CONTENT_MODEL_DRAFT.md`
- 当前 `game-package/manifest.json`
- 当前 Module Schema / Scenario Schema / validator / tests / build tooling

执行：

```bash
python3 tools/run_acceptance.py
```

记录起始 SHA、branch、工作树和基线结果。

## Phase 1 — 建立 `authoring/` 创作源层

目标结构至少应能表达下列职责；允许根据现有仓库风格做最小调整，但不得混淆层次：

```text
authoring/
├── README.md
├── story/
│   ├── 00_STORY_BIBLE.md
│   ├── 01_TRUTH_BIBLE.md
│   ├── 02_MAIN_MYSTERY_GRAPH.md
│   ├── 03_RETURN_HOME_ARC.md
│   └── 04_REVEAL_POLICY.md
├── world/
│   ├── README.md
│   ├── regions/
│   │   └── _template/
│   └── rule-domains/
│       └── _template/
├── arcs/
│   ├── README.md
│   └── _template/
├── modules/
│   ├── README.md
│   └── _template/
├── characters/
│   ├── README.md
│   ├── npcs/_template/
│   ├── factions/_template/
│   └── entities/_template/
├── mysteries/
│   ├── README.md
│   ├── clues/_template/
│   ├── hypotheses/_template/
│   └── revelations/_template/
└── art/
    ├── README.md
    ├── briefs/
    └── references/
```

### 创作层硬边界

- `authoring/` = 人类/模型共同维护的**创作源、真相图、设计解释与美术 brief**；
- `game-package/` = 经过结构化、可被平台装载的**运行输入**；
- `dist/` = 构建产物；
- `docs/` = 游戏/工程合同；
- `governance/` = 已冻结机器决策与范围。

不得让 `authoring/` 自动进入 `.trpgpkg`、package lock 或运行时可见数据。

## Phase 2 — 为每类剧情对象建立最小模板合同

不要写大段具体剧情，只建立可维护模板和索引规则。

### Story Bible

至少包含：主题、玩家体验承诺、长期目标、不可破坏叙事原则、非目标。不得伪造终极答案。

### Truth Bible

标记为 `AUTHOR / GM ONLY`。至少预留：truth_id、状态（OPEN/PROVISIONAL/ACCEPTED 或项目等价状态）、依赖、可被哪些 reveal 引用、泄漏限制。不要把整个文件直接作为 AI GM 默认上下文。

### Main Mystery Graph

以**真相节点图**而不是章节顺序表达。模板至少包含：truth node、prerequisites、evidence、counter-evidence、false hypothesis、reveal condition、related region/rule domain/NPC/event、consequence。

### Return Home Arc

把“找到回家方法”作为长期调查与选择结构，而不是固定最终任务。若真正条件仍 OPEN，只建立阶段槽位和依赖模型。

### Region

至少表达：region_id、公开概述、持久状态、连接区域、常驻 faction/NPC、Rule Domain 引用、安全/补给、动态事件、进入/离开条件、重访影响。

Region 不是一次性副本。

### Rule Domain

至少为未来结构化运行语义保留：

```text
rule_domain_id
scope
rules
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
world_changes_after_break
```

Rule Domain 可以相邻、嵌套、叠加和冲突。

### Arc

支持 main / side / character / world-event；必须以条件和世界状态驱动，不得强迫整个 Campaign 线性执行。

### Authoring Module

是一个可转换为 runtime Module 的内容单元设计，不等于 Campaign；至少连接 Region、Rule Domain、scene、NPC、clue、timeline、threat、exits、局部 ending。

### NPC / Faction / Entity

必须区分：公开事实、真实事实、角色自身认知、错误认知、所知规则、关系和可见性。

### Clue / Hypothesis / Revelation

关键线索必须有失败推进或替代信息路径；玩家假设不能自动升级为世界真相。

## Phase 3 — 正式定义“创作源 → 运行内容”转换边界

在合适的 `docs/design/` 或 `docs/operations/` 文件中明确：

```text
authoring source
      ↓
Codex consistency/spec pass
      ↓
structured runtime data / Schema / fixture
      ↓
OpenCode script（需要时）
Grok art（需要时）
      ↓
Codex integration
      ↓
game-package/
      ↓
acceptance
      ↓
.trpgpkg
```

不得声称当前已经存在自动“编译剧情 Markdown → runtime”的成熟编译器，除非本任务真的实现并验收该能力。

## Phase 4 — 消除 Module 验证盲区

当前初始化包主要围绕 tutorial/golden。请把 Module 验证改造成**注册表驱动**，避免正式剧情增加后逃逸验收。

最低要求：

1. `game-package/manifest.json` 的 module 注册列表是运行时模块注册权威之一；
2. validator 遍历所有注册 Module；
3. 每个注册路径必须存在且留在 `game-package/` 内；
4. 每个 Module manifest 必须通过 Schema；
5. Module ID 唯一；
6. 每个 Module 引用的 scenario / expected path / 相关文件存在且通过对应 Schema；
7. 检测 `game-package/modules/**/manifest.json` 中未注册的可执行 Module，并 fail-fast，除非目录被明确标为 template/non-runtime；
8. 检测 manifest 中指向不存在 Module 的条目；
9. tutorial/golden 保留特有 Golden Vector 检查，但不得成为其他 Module 的替代验证；
10. 新增正向与负向自动测试，至少覆盖：
    - 正常第三 Module；
    - 未注册 Module；
    - 注册不存在 Module；
    - 重复 Module ID；
    - 非法 scenario/schema 引用。

实现时保持当前工具“Python 3.11+ 标准库”的约束，除非权威文件已经允许新增依赖。

## Phase 5 — 打包边界测试

增加/确认测试证明：

- `authoring/` 不进入 `.trpgpkg`；
- `authoring/` 不参与 `game-package/package.lock.json`；
- 注册 runtime Module 正常进入包；
- 未注册 executable Module 会被验收阻止，而不是静默存在；
- 两次相同输入构建仍保持字节级确定性。

## Phase 6 — 混合开发入口

不要让 OpenCode 或 Grok 自行设计内容架构。本任务由 Codex 完成规格/工具/模板。

可在需要时补充专用 Task Packet 示例，但不得生成虚假的美术或脚本工作量。

确保后续剧情更新可以由 `.codex/STORY_UPDATE_PROMPT.md` 驱动：

- Codex 修改 authoring / 数据规格 / Task Packet；
- OpenCode 实现明确脚本；
- Grok 生产明确美术；
- Codex 集成并验收。

## Phase 7 — 验收

如果修改 `game-package/`：

```bash
python3 tools/update_lock.py
```

然后至少执行：

```bash
python3 tools/run_acceptance.py
python3 tools/build_package.py
python3 tools/run_acceptance.py
```

并执行新增的 Module 负向测试。

检查：

```bash
git diff --check
git status --short
```

## 禁止事项

- 不编写完整正式主线；
- 不替项目所有者决定终极真相或回家条件；
- 不把开放世界设计成“主神空间 → 固定副本 1 → 返回 → 固定副本 2”的唯一结构；
- 不把 Region 等同 Module；
- 不把 Rule Domain 仅写成自然语言怪谈；
- 不把 `authoring/` 纳入游戏运行包；
- 不修改 TRPG_PLATFORM；
- 不引入第三方受保护规则、设定或素材；
- 不通过只扫描 tutorial/golden 继续保留验证盲区。

## 最终输出

### Result
`PASS_LOCAL / FAIL / BLOCKED_DECISION / BLOCKED_EXTERNAL`

### Architecture delivered
列出新增目录、模板、索引和职责。

### Runtime validation changes
列出 Module 发现/注册/Schema/负向测试变化。

### Decisions preserved
明确哪些终极剧情问题仍保持 OPEN，没有被实现者补全。

### Changed files
逐文件说明原因。

### Verification
逐条列出实际命令、退出码与关键输出。

### Follow-up entry point
给出**下一步仅一项**推荐：通常是创建第一片正式 Region + 3–5 个 Rule Domain 的 authoring 内容，而不是直接扩展整季剧情。
