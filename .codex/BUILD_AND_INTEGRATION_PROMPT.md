# 《规则残差》Codex 构建与集成提示词

> 用途：对一个已经明确目标的施工批次进行任务规划、跨模型委派、集成、构建与本地验证。
> 
> 角色约束：Codex 是规划者、规格/数据整合者和最终验证协调者；Lua/游戏脚本默认交由 OpenCode；文学正文默认交由 DeepSeek Harness；美术默认交由 Grok。不得让执行者批准自身产物。

> M3 Story Construction：所有文学与视觉工作必须从 `.codex/prompts/m3/STORY-CONSTRUCTION/README.md` 进入，并通过对应结构化订单和输入哈希门禁。

---

你正在《规则残差》独立第一方游戏仓库中完成一次**严格受控的构建与集成任务**。不要修改 TRPG_PLATFORM 平台仓库，不要把平台实现假设硬编码进本游戏。

## 本次任务输入

- 任务目标：`<粘贴本批次目标>`
- 用户已冻结的新决策：`<没有则写“无”>`
- 允许范围：`<没有明确给出时，根据目标推导最小范围并在施工前列出>`
- 禁止范围：`<没有明确给出时，至少继承 AGENTS.md 与本提示词的禁止项>`
- 目标提交/分支（如有）：`<可空>`

如果用户没有填写某一项，不要为无关细节追问；先从仓库权威文件中解析。只有缺失信息会导致产品语义不可逆地被猜测时，才把该部分标记为 `BLOCKED_DECISION`，继续完成其余不依赖部分。

## Phase 0 — 建立不可伪造的基线

只读执行并记录结果：

1. `git status --short`
2. `git branch --show-current`
3. `git rev-parse HEAD`
4. 按 `README.md` 的权威读取顺序读取文件，至少包括：
   - `AGENTS.md`
   - `governance/decisions.json`
   - `governance/scope.json`
   - `docs/authority/01_PLATFORM_BOUNDARY.md`
   - `docs/authority/03_DESIGN_PRINCIPLES.md`
   - `docs/authority/04_RULES_AND_STATE_MODEL.md`
   - `docs/authority/05_AI_AGENT_CONTRACT.md`
   - `docs/authority/06_VISIBILITY_MEMORY_CONTRACT.md`
   - `docs/authority/07_GAME_PACKAGE_CONTRACT.md`
   - `docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md`
   - `docs/authority/09_ACCEPTANCE_STANDARD.md`
   - `docs/authority/10_OPEN_DECISIONS.md`
5. 读取与本任务直接相关的 `authoring/`、`docs/design/`、Schema、Module、Lua、测试和 Task Packet。
6. 运行：

```bash
python3 tools/run_acceptance.py
```

如果基线失败：记录**原始失败证据**。除非本任务明确覆盖该问题，不得把无关基线故障混入施工。

## Phase 1 — 做任务图，不先写代码

输出一份最小任务图，逐项列出：

- authoritative semantics：本任务实际改变什么游戏语义；
- 依赖的 `ACCEPTED / PROVISIONAL / OPEN` 决策；
- 修改文件；
- 不修改文件；
- 数据/Schema/API 影响；
- 存档兼容性影响；
- 可见性和 GM-only 信息影响；
- 测试与验收向量；
- 是否需要 OpenCode / DeepSeek Harness / Grok。

严格路由：

- Lua、游戏脚本、脚本侧 fixture/test → `owner=opencode`、`task_type=script`；
- 文学正文 → `owner=deepseek_harness`、`task_type=literary`，且必须携带经过验证的文学订单；
- 原创角色、环境、物件、地图、UI 等美术 → `owner=grok`、`task_type=art`，且必须携带经过验证的视觉订单；
- 规格、Schema、内容数据结构、索引、Task Packet、集成和验收 → Codex；
- 不得把同一文件交给两个并行任务；
- 不得为了“充分利用模型”拆分没有独立输入输出边界的小任务。

若需要委派，必须根据 `workflow/task-packet.schema.json` 在 `workflow/queue/` 生成合法 Task Packet。每个 Task Packet 必须有：authority、inputs、allowed_paths、forbidden_paths、open_decisions、acceptance、expected_outputs。

## Phase 2 — 规格优先施工

先固定机器可验证的输入输出，再实施：

1. 内容/规则语义；
2. Schema 或数据契约；
3. fixture / acceptance vector；
4. OpenCode 脚本任务；
5. DeepSeek Harness 文学任务；
6. Grok 美术任务；
7. Codex 集成。

不可违反：

- 最终世界真相、规则来源、无限流来源、真正归乡条件若仍是 `OPEN`，不得擅自补全；
- “规则”必须能机器表达作用域、触发、条件、效果、例外/冲突、优先级、破解条件与持久性，不能只存在于叙述文本；
- 世界事实、玩家已知信息、规则假设、确认知识、Agent Memory、Context Summary 必须分离；
- AI 只能产生结构化动作/草稿，不能直接写权威状态；
- 关键路径失败必须继续推进；可选秘密、奖励和支线允许错过；
- `authoring/` 是创作源，不得因为方便而直接当作运行时权威；
- `game-package/` 是可执行输入；运行内容变化必须有 Schema/测试/锁文件同步；
- 不加入第三方受保护规则、设定、模组文本、商标或素材。

## Phase 3 — 接收 OpenCode / DeepSeek Harness / Grok 返回物

对于每个 `RETURNED` 任务：

### OpenCode

独立检查：

- diff 是否完全位于 `allowed_paths`；
- 是否擅改规则语义、Schema 或治理文件；
- 是否引入随机、网络、文件系统、时钟、环境变量、进程、动态库或 debug API；
- 自测结果只作为线索，Codex 必须重跑。

### DeepSeek Harness

独立检查文学订单、权威输入哈希、双层审读（T1/T2）与约束审读（C1）证据；DeepSeek Harness 只能返回文学候选稿，不能写权威、Schema、治理或运行时路径，也不能批准自身产物。

### Grok

独立检查：

- 文件名、格式、尺寸/比例、透明通道（如要求）；
- 是否位于批准的资产路径；
- provenance 是否完整；
- 是否出现任务禁止的第三方 IP、商标或明显不匹配内容；
- 审美最终采用权属于项目所有者，Codex 只验证技术与来源门禁。

发现越权时：不要顺手扩范围修正，先将对应任务标为 `FAIL` 或 `BLOCKED_SCOPE`，只在当前授权可覆盖时做最小集成修复。

## Phase 4 — 构建与仓库级验收

如果修改了 `game-package/` 运行输入：

```bash
python3 tools/update_lock.py
```

然后依次执行：

```bash
python3 tools/run_acceptance.py
python3 tools/build_package.py
```

再次执行：

```bash
python3 tools/run_acceptance.py
```

同时检查：

- `git status --short`
- `git diff --check`
- `git diff --stat`
- `git diff -- <本任务涉及路径>`

若本次涉及内容架构或 Module：额外确认 manifest 注册、Schema、引用、visibility、关键线索 fallback、规则域引用和自动验证不存在盲区。

若本次涉及剧情：必须使用 `.codex/prompts/m3/STORY-CONSTRUCTION/README.md` 的 M3 Story Construction 路由进行交叉检查，must not invoke `.codex/STORY_UPDATE_PROMPT.md`；旧文件仅是被 superseded 的历史证据。

## Phase 5 — 最终报告

严格按以下格式输出：

### Result
`PASS_LOCAL` / `FAIL` / `BLOCKED_DECISION` / `BLOCKED_EXTERNAL`

### Baseline
- branch：
- start SHA：
- baseline acceptance：

### Scope
- 完成目标：
- 未完成目标：
- 明确未触碰范围：

### Task graph
- Codex：
- OpenCode：
- DeepSeek Harness：
- Grok：

### Changed files
逐文件列出“路径 — 原因 — 对应需求/决策/验收”。

### Verification
逐条列出**实际执行命令、退出码、关键结果**，不得只写“测试通过”。

### Runtime/package
- 是否更新 package lock：
- 是否生成 `.trpgpkg`：
- 产物路径：
- SHA-256（如生成）：

### Risks / blockers
列出所有仍未关闭的 OPEN、平台外部门禁、存档迁移问题或素材审美待确认项。

### Git state
- end SHA（若未提交则写 unchanged）：
- working tree：

只有本地门禁全部通过才能给 `PASS_LOCAL`。没有真实执行 TRPG_PLATFORM / Creator / 正式 Lua Host 外部门禁时，不得声称“正式可玩”“平台兼容已认证”或“可发布”。
