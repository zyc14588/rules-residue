<!-- SECTION-ID: M1-AUTHORING-README -->
# Authoring 创作源层

`authoring/` 保存人类与模型共同维护的创作源、真相图、内容设计和美术 brief。它不是权威运行状态，也不是 Game Package 输入。

## 分层边界

| 层 | 职责 | 是否进入 `.trpgpkg` |
|---|---|---:|
| `authoring/` | 创作意图、GM-only 真相设计、对象模板、关联索引 | 否 |
| `docs/` | 游戏与工程合同 | 否 |
| `governance/` | 已冻结决策、范围与门禁 | 否 |
| `game-package/` | 经结构化和验收的运行输入 | 是 |
| `dist/` | 确定性构建产物 | 不适用 |

仓库当前没有“Markdown 自动编译为运行内容”的成熟编译器。把创作源提升到 `game-package/` 必须经过人工可审计的规格化、Schema 校验、必要的脚本/素材任务、Codex 集成和仓库验收。

## 目录索引

- `story/`：故事圣经、真相圣经、主谜题图、归乡 Arc 与揭示策略；
- `world/`：持久 Region 与可叠加 Rule Domain；
- `arcs/`：由条件和世界状态驱动的长期/支线结构；
- `modules/`：可转换为 runtime Module 的局部内容单元；
- `characters/`：NPC、Faction 与 Entity；
- `mysteries/`：Clue、Hypothesis 与 Revelation；
- `art/`：原创美术 brief 和经权利审查的参考资料记录。

各分类的 `README.md` 是该分类的人工索引；`_template/` 只存模板，不是已登记内容。

## ID 与登记规则

1. 使用稳定、小写、点分隔 ID，例如 `region.<slug>`、`domain.<slug>`、`arc.<slug>`、`module.<slug>`、`npc.<slug>`、`faction.<slug>`、`entity.<slug>`、`clue.<slug>`、`hypothesis.<slug>`、`reveal.<slug>`、`truth.<slug>`。
2. 一个 ID 只表示一个对象；改名时保留迁移说明，不复用旧 ID 表示新对象。
3. 新对象从对应 `_template/` 复制到非模板目录，并加入该分类索引。
4. 引用必须使用 ID，不以文件名或自然语言昵称代替。
5. `OPEN` 只表示待项目所有者决定，不能因填写模板而升级为 `PROVISIONAL` 或 `ACCEPTED`。

## 可见性纪律

- `story/01_TRUTH_BIBLE.md` 及标为 `AUTHOR / GM ONLY` 的字段不得作为普通 Agent 或玩家的默认上下文；
- 创作层的“真实事实”、角色认知、玩家假设和已确认运行知识必须分别维护；
- 任何可揭示内容都要通过 Revelation 条件转化为允许投影的运行事实；
- Agent 记忆与摘要只能从已提交 Event 派生，不能从本目录直接成为 `confirmed` 事实。

转换和验收流程见 `docs/operations/CONTENT_AUTHORING_PIPELINE.md`。

<!-- SECTION-ID: R2-AUTHORING-README -->
# M1 authoring层的R2扩展说明

本目录候选用于合并到M1既有 `authoring/`，不创建平行创作源。

## 核心边界

```text
authoring source
→ Codex一致性/规格化
→ structured runtime data / Schema / fixture
→ OpenCode脚本 + Grok美术
→ Codex集成
→ game-package
→ acceptance
→ .trpgpkg
```

`authoring/` 自身不得进入运行包、锁文件或普通玩家/AI上下文。

## R2新增对象

- 大区三阶段状态；
- 逻辑完全异常区；
- 规则三层表达；
- 纠缠因果；
- 规则装备；
- 大区独特规则；
- 因果校准图；
- 关键道具两相；
- 循环、锚点、永久异常与通用代价；
- 最终Boss人格/维护层；
- 三分支终局；
- 纯2D艺术方向与多声部文本。

M1既有模板若已覆盖这些对象，应扩展原模板，不应保留两套冲突模板。
