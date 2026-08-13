<!-- SECTION-ID: R2-INSTALL-FROZEN-PLAN -->
# R2 Authority Install — Frozen Plan

状态：`FROZEN`
角色：`PLAN`
业务里程碑：`R2-AUTHORITY-INSTALL`
仓库原生 route 映射：`milestone=M1`、`batch_id=M1-B002`
实现含义：安装 R2 权威与 M2 输入；`M2_IMPLEMENTATION_STARTED=NO`

## 固定基线与包证据

- source branch：`design/r1-story-architecture`
- source commit：`e8e536fe5c96c389736ffcf8d4855fa146a2b9c2`
- source tree：`d06c3e1e4f1984447caef3b3e9012f8adc7ae20c`
- R2 package：`/home/zyc14588/RULE_RESIDUAL_R2_AUTHORITY_AND_PROGRESSIVE_DELIVERY_v1.0.0`
- package version/status：`1.0.0 / INTEGRATION_CANDIDATE`
- manifest SHA-256：`a5adb9fad5439926e0c8d46f23f3e3e107812bdd9ce13097acea04b8cc0a7ba1`
- `SHA256SUMS` SHA-256：`2d65a2ea9fefffc4f8e785fe2e55a0bdc83b7a54559afbb51162daedc0ab8e72`
- package file count：`124`
- decisions/group counts：`191 / 10,14,16,18,20,21,22,22,24,24`
- package integrity：`sha256sum -c SHA256SUMS` exit `0`
- package input policy：只读；安装前后复算 `SHA256SUMS` 文件哈希并再次执行完整校验。

安装基线的五个正式入口均在 source commit 上 exit `0`：`just validate`、`just test`、`just acceptance`、`just codex-check`、`python3 tools/run_acceptance.py`。`just codex-check` 是本仓库冻结的 `CODEX_ROUTE_FRESH` 等价入口；禁止新增 Go 工程。

## Reading Map 冻结

- request source：`.codex/routes/r2-authority-install-plan-request.json`
- ephemeral map：`/tmp/r2-authority-install-plan-reading-map.json`（不入库）
- route identity：`R2-AUTHORITY-INSTALL-PLAN / PLAN / M1 / M1-B002`
- external allow-root：R2 package 的精确绝对路径
- planned context：`103147 / 196608 = 0.5246327718098959`
- soft/hard：`0.55 / 0.70`
- generated status：`OK`
- canonical binding digest：`d6bbdced99464e6aad9216278cafa7bed2f42df54f3af9134853e81a53d36ff4`
- freshness result：`CHECK: PASS / CODEX_ROUTE_FRESH=PASS`

PLAN map 绑定 source commit，PLAN commit 产生后必然过期；IMPLEMENT、ACCEPT、REPAIR 必须在各自固定 HEAD/worktree 以仓库原生 `tools/codex_route.py generate` 重新生成 ephemeral map，再以角色、route、milestone、batch 和同一 allow-root 执行 `check`。不得复制本 map、不得手写 map、不得把 map 纳入 commit。

## TaskEnvelope 与全包处置

- 可执行 TaskEnvelope / 标准 Task Packet：`workflow/queue/RR-TASK-0004.json`
- 全包逐文件唯一处置矩阵：`.codex/plans/r2-authority-install/package-disposition.yaml`
- 分类计数：`INSTALL_CANONICAL=108`、`MERGE_INTO_EXISTING=9`、`REFERENCE_ONLY=0`、`PACKAGE_PROVENANCE_ONLY=5`、`DUPLICATE_OF_CANONICAL=2`、`NOT_APPLICABLE_FIRST_RELEASE=0`、`UNCLASSIFIED=0`。
- `reading-map-v1.schema.json` 与当前 `.codex/schemas/reading-map-v1.schema.json` 字节相同，只保留当前 route 机器权威源。
- acceptance packet 的 `acceptance-result-v1.schema.json` 与 overlay schema 字节相同，只在 `schemas/r2/` 安装一份。
- 两个包内 Task Packet YAML 是概念候选，不符合现行 `workflow/task-packet.schema.json` 字面 schema；必须无损转换成合法 JSON examples，不能放宽现行 schema。

## IMPLEMENT 冻结范围

IMPLEMENT 只能修改 TaskEnvelope 的 `allowed_paths`。其中以下既有文件只允许作明确的语义合并或入口更新：

- `AGENTS.md`、`README.md`；
- `docs/authority/00_PROJECT_CHARTER.md`、`docs/authority/10_OPEN_DECISIONS.md`；
- `governance/decisions.json`、`governance/scope.json`；
- `authoring/README.md` 与 `authoring/story/00_STORY_BIBLE.md`—`04_REVEAL_POLICY.md`；
- `.codex/SESSION_START.md`、`.opencode/SCRIPT_TASK_PROMPT.md`、`.grok/ART_TASK_PROMPT.md`、`workflow/README.md`；
- `justfile`、`tools/validate_project.py`，以及新建的 R2 validator/tests。

新增文件仅限矩阵目标和 R2 route/validation 支撑。PLAN 的 `.codex/state/MILESTONE_PLAN.yaml`、本计划、处置矩阵和 TaskEnvelope 在 IMPLEMENT 中只读。

绝对禁止：`game-package/**`、`dist/**`、package lock、任何 Lua/runtime、正式六大区运行内容、循环/关键道具/亡者视角/Boss 实现、TRPG_PLATFORM、远程 push/PR。

## 安装与生成规则

IMPLEMENT 按矩阵逐文件处理，禁止 `cp -r` 或 `rsync` overlay。无 `generated`/`DO NOT EDIT` 标记的当前入口可作最小语义合并；现仓库未提供 README、`.codex/SESSION_START.md`、authority index 或 milestone 的正文生成器。唯一生成产物是 ephemeral Reading Map，机器源是 `.codex/routes/*.json`，生成后不得入库。

安装顺序冻结为：自然语言权威 → 191 决策/术语/追踪/延期/安全 → schemas → authoring merge/supersession → 唯一 README authority 导航 → Codex route/prompt → M2 inputs（只安装）→ OpenCode/Grok/portable-agent → independent acceptance → operations/provenance → Task Packet examples → validator/tests。

## M1 OPEN → R2 supersession

以下旧容器必须保留来源但不再以 ACTIVE `OPEN` 与 R2 真相并存：

| M1 来源 | 旧含义 | 冻结处理 |
|---|---|---|
| `governance/decisions.json:RR-O003` | 完整异世界与最终真相 OPEN | 状态改为 `SUPERSEDED_BY_R2`；引用 `R2-E01..E20`、相关 C/G 决策与十项 R2 deferred register |
| `AGENTS.md` 边界 13 | 最终世界真相与回家条件仍 OPEN | 改为 R2 冻结真相优先；实现者仍不得补全 deferred 内容 |
| `docs/authority/00_PROJECT_CHARTER.md` | M0 不冻结答案 | 保留为历史 M0 说明并明确 `SUPERSEDED_BY_R2` |
| `docs/authority/10_OPEN_DECISIONS.md` | 正式世界观/长期结构全部 OPEN | 拆分为已被 R2 supersede 与仍 OPEN/deferred，不改变许可证/平台等真实 OPEN |
| `governance/scope.json` | 真相仍在 P1/non-goal | 更新为“R2 已冻结、M2 尚未实现”，保留 M0 历史边界 |
| `authoring/story/00_STORY_BIBLE.md` | 长期真相槽位 OPEN | 语义合并 R2 frozen story，保留历史标记 |
| `authoring/story/01_TRUTH_BIBLE.md` | 五类真相 OPEN、无条目 | 标记旧容器 `SUPERSEDED_BY_R2`，安装唯一 ACTIVE `TRUTH-R2-001..012`，继续 GM-only |
| `authoring/story/02_MAIN_MYSTERY_GRAPH.md` | 终极图为空/OPEN | 标记旧空图 superseded，安装 R2 因果图 |
| `authoring/story/03_RETURN_HOME_ARC.md` | 唯一归乡条件 OPEN | 标记旧阶段槽位 superseded，安装 R2 最低资格/三分支 |
| `authoring/story/04_REVEAL_POLICY.md` | M1 揭示层 | 保留并扩展为 R2 玩家/私人/队伍/主持/机械/审计六层，不覆写原则 |

唯一 ACTIVE 主真相至少包括：高维坍缩维度残片；多世界因果纠缠；角色1为高维幸存文明因果律武器表现载体；Boss 为失败主角团、历代牺牲者、高维维护者与扭曲因果聚合；关键道具为外部悖论奇点加工的因果炸弹；错误引爆灭世；正确引爆解除纠缠；共同梦境回归。具体六区主题、Boss人格名单、数值与算法仍由 `governance/r2/deferred-items.r2.yaml` 保持 deferred。

## R2-INT-001—012 冻结分类

| ID | 分类 | 本批结果与 M2 后续 |
|---|---|---|
| R2-INT-001 | `PLATFORM_CAPABILITY_PROBE` | 安装 2—6 席位权威；M2 探测 schema/server 上限，失败才提平台变更 |
| R2-INT-002 | `PLATFORM_CAPABILITY_PROBE` | 安装亡者视图/白名单/系绳契约；M2 探测宿主能力 |
| R2-INT-003 | `R2_COMPATIBILITY_ADAPTER` | 冻结世界内多步骤且明确意图，不做末端 UI 确认；M2 包侧适配 |
| R2-INT-004 | `R2_COMPATIBILITY_ADAPTER` | 区分平台安全警告与谜题信息信号；异常区/战役终止仍明显警告 |
| R2-INT-005 | `PLATFORM_CAPABILITY_PROBE` | 安装 35—60/约100小时权威；M2 探测 Campaign/存档/版本锁 |
| R2-INT-006 | `PLATFORM_CAPABILITY_PROBE` | 安装谱系级解锁边界；M2 探测账号/跨战役声明，不继承答案状态 |
| R2-INT-007 | `PACKAGE_DECLARABLE` | 安装六区资格与 M2 单区切片限制；M2 不声称完整首发内容 |
| R2-INT-008 | `PLATFORM_CAPABILITY_PROBE` | 安装灭世终止事件语义；M2 只在候选包模拟，不改平台历史 |
| R2-INT-009 | `PACKAGE_DECLARABLE` | 安装玩家记忆主张/证据/Agent Memory/权威状态四层隔离 |
| R2-INT-010 | `R2_COMPATIBILITY_ADAPTER` | 使用 `schemas/r2` 与包命名空间扩展，不破坏平台通用 item |
| R2-INT-011 | `PLATFORM_CAPABILITY_PROBE` | 安装 18 阶段重复过滤；M2 探测运行时/恢复/热更新能力 |
| R2-INT-012 | `R2_COMPATIBILITY_ADAPTER` | 逻辑异常的机械执行仍确定性；不随机改答案 |

全部 12 项当前为 `DEFERRED_WITH_NON_BLOCKING_PROOF`：本批不依赖未知宿主能力来持久化权威、Schema 草案、M2 probe 输入或验收合同；没有已识别的 `BLOCKED_DESIGN_CONFLICT`。不得把 deferred 写成平台能力 PASS。

## 安全、语言与层隔离

必须安装机器安全策略，包含 18 个重复过滤阶段及未成年人性侵犯/剥削/胁迫/诱骗/交易/性化奴役/性化呈现绝对红线。命中只能删除或整体重设，不能用 warning、隐藏或 GM-only 保留。

首发 `zh-CN only`；完整多语言内容验收为 `NOT_APPLICABLE_FIRST_RELEASE` 的验收维度，不是包文件处置分类。稳定语义 ID、机械/表现分离、Unicode、外置语言资源、字幕/语音映射及未来语言/谜题适配接口仍必须持久化；不得用中文显示字符串驱动机械。

Truth Bible 保持 `AUTHOR / GM / MECHANICAL ONLY`。OpenCode 只得脚本接口、Schema、机械语义、fixture/tests；Grok 只得 brief/风格/视觉要求；portable-agent 必须返回 candidate artifact、evidence、limitations，且全部由 Codex 重新集成。

## IMPLEMENT 自检与候选固定

IMPLEMENT 必须新增仓库原生 R2 静态 validator，并从 `justfile`/`tools/validate_project.py` 接入；不得仅靠 package 自带 integrity report。至少验证 191 数量、精确组计数、唯一 ID/Section ID、YAML/JSON/meta-schema、authority map 路径、191/191 traceability、deferred 唯一、supersession、层隔离、安全 18 阶段、route/prompt/handoff/M2 input/acceptance packet、处置矩阵完整性及 runtime unchanged。

候选提交前执行：

```text
just validate
just test
just acceptance
just codex-check
just r2-validate
python3 tools/run_acceptance.py
git diff --check
```

并比较 source..candidate：`game-package/**`、`dist/**`、package lock、Lua 均无 diff。候选必须提交，记录 commit/tree，状态只到 `VERIFYING`；Builder 不得正式 ACCEPT。

## 独立 ACCEPT 冻结上下文

父级必须从固定 candidate commit 显式创建新的 worktree，并使用新的 ACCEPT 上下文。Verifier 只读，固定 source/candidate commit/tree；在 candidate HEAD 生成并 check ACCEPT Reading Map，读取安装后的 `.codex/prompts/r2/R2-AUTHORITY-INSTALL/ACCEPT.md` 与 `docs/acceptance/r2/*` 必要 Section，不读取 Builder 结论作为证据。

ACCEPT 前后记录 HEAD/tree/status/diff，tracked tree 必须不变。除重复运行完整自检外，Verifier 必须在临时副本独立解析 191/组计数/追踪/Section ID，并执行负向探针：删除决策、重复 decision、重复 Section ID、破坏 schema、删除 traceability、安全阶段、Truth Bible 加入 package、stale map、超过 70% map，全部必须 REJECT。

FAIL 时从 finding 固定 candidate 创建独立 REPAIR worktree；只修 finding，产生新 candidate 后旧证据失效，再创建全新 ACCEPT。若 finding 指向冻结计划错误，返回 `REPLAN_REQUIRED`。

## 集成条件

只有独立 ACCEPT `PASS` 后，父级重新核对目标 `design/r1-story-architecture` 仍处于 expected lineage 且 clean，才允许 fast-forward-only；分支移动则 `BLOCKED_BASE_MOVED`。禁止 push/PR。最终目标分支再次运行全部门禁，工作树 clean；下一步只能是 `M2_PLAN`。
