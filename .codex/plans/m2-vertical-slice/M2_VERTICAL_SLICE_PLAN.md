<!-- SECTION-ID: M2-PLAN-FROZEN -->
# M2 Vertical Slice Frozen Construction Plan

生命周期状态：`ACCEPTED_WITH_DOWNSTREAM_BLOCKERS`（`M2-B001=ACCEPTED`；`M2-B002`—`M2-B016=PLANNED`）
下游实现状态：`M2-B002=NOT_STARTED`，`M2-B002_READY=NO`

## M2-B001 生命周期收尾

- 已接受 recovery Candidate A2：`f5964d4c0b02e5969747a628dae64a02f87b8417` / `75ec646592260f764fa1862b20c164e8ecb46f1d`。
- 正式 M2-B001 身份保持：`fdc1f4c9d8bc565888f33b44684cd6ccbe80c127` / `f37e15cdd65e0a39eebcddb21f56a2c58ae6939e`。
- 历史 `R2-INT-010=FAIL` 永久保留；当前有效投影为 `RESOLVED_ADAPTER`。
- `formal_B002=false`、`formal_B009=false`、aggregate M2/external capability 均未通过。
- 剩余 blocker 精确为 `R2-INT-011`、`R2-INT-012`、`DEFER-R2-C14-001`；`active_WIP=0`。

`batches.json` 中 `M2-B001.state=FROZEN` 与顶层 `frozen_batches` 是冻结施工 envelope 的历史语义，按 repository-native validator 保留；当前生命周期权威由 `.codex/state/MILESTONE_PLAN.yaml` 与各控制面文件的 `lifecycle_projection` 表达，不得把两种 state 语义混写成 `INVALID_MIXED_STATE`。

## 身份与路由

- 仓库：`/home/zyc14588/rules-residue`
- 分支：`design/r1-story-architecture`
- source commit：`a571bdfbabd4d4b8b2ba8957be09fc7d65dc5963`
- source tree：`f22f7e2e57f5c0ad88b60c04da1ca75a04fbdccf`
- route scope：`M2-VERTICAL-SLICE`
- route machine batch：`M2-B001`。仓库路由器只接受 `M[0-9]+-B[0-9]{3,}`，因此任务名保留为 route/plan scope，而不冒充合法 `batch_id`。
- binding digest：`099d964a422fbce4f76a4a565d7dcabdcbe09a6afcff8a0c1204be730561e065`
- context：`104032 / 196608 = 52.9134%`，soft `55%`，hard `70%`，状态 `SOFT_REDUCED`

`M2_REFERENCE_WORK_PACKAGES.yaml` 与安装冲突机器证据没有 HTML Section marker。PLAN 未修改源或路由器，而是从固定 tree 生成源哈希锁定的只读路由投影，再由 Reading Map 绑定投影文档 SHA。源/投影 SHA 分别记录在 `controls.json`；投影不构成新权威副本。

## 基线事实

以下命令在开始规划前均以退出码 0 完成：

- `just validate`
- `just test`（98 tests）
- `just acceptance`
- `just codex-check`（freshness PASS；26 个负向路由测试 PASS）
- `python3 tools/run_acceptance.py`
- `python3 tools/validate_r2_install.py`

R2 安装基线为 191 项冻结决策、191/191 机器追溯、10 个 deferred 项、0 个 active truth conflict。外部 TRPG_PLATFORM / Creator Tool probe 本轮均未运行，状态保持 `NOT_RUN`。

## 施工原则

严格顺序为：机器语义 → Schema → fixture → 确定性状态转换 → 负向测试 → Lua → 内容/美术 → 集成 → 独立验收。任何 Lua 批次都依赖已验收 Schema 与 fixture。

每批分别创建 PLAN、IMPLEMENT、ACCEPT、REPAIR Git worktree。ACCEPT 只读验证固定 candidate commit/tree；OpenCode/Grok 返回物必须由 Codex 独立复验。同一外部任务文件只有一个 owner。

每批在 input、generation、editing、semantic/script conversion、asset import、acceptance 重跑内容安全过滤。任何涉及未成年人性侵犯、性剥削、性胁迫、诱骗、交易、性化奴役或性化呈现的内容一律拒绝并删除或整体重设，不能 warning-only 保留。

## 依赖 DAG

```text
M2-B001 probes
  → B002 schemas
    → B003 seed/state/visibility fixtures
      → B004 rule runtime
        → B005 loop/permanence/anchors
          → B006 character/2--6/death
            → B007 structured test region
              → B008 region/anomaly runtime
                → B009 equipment/key item
      B003 + B006 + B008 → B010 host/AI/visibility
      B005 + B008 + B009 + B010 → B011 Boss/ending specs
      B004 + B005 + B006 + B009 + B010 + B011 → B012 Boss/ending runtime
      B007 + B008 + B009 + B012 → B013 2D placeholder pipeline
      B013 → B014 minimal final-slice art
      B012 + B014 → B015 Host/Creator/E2E candidate
      B015 → B016 independent acceptance
```

机器 DAG 见 `batches.json`。当前不冻结并行组；未来只有在各自 PLAN 重新证明路径互斥、依赖独立且 `parallel_safe` 后才可并行。

## 批次摘要

| Batch | 状态 | 目标 | 主要执行者 |
|---|---|---|---|
| `M2-B001` | `ACCEPTED` | R2-INT-001—012 能力探针、recovery evidence 与 lifecycle closeout | Codex |
| `M2-B002` | `PLANNED` | 完整机器语义与 Schema | Codex |
| `M2-B003` | `PLANNED` | seed/state/visibility/audit fixture 与 reference transitions | Codex |
| `M2-B004` | `PLANNED` | 确定性规则执行与 Typed Effects | Codex + OpenCode |
| `M2-B005` | `PLANNED` | 循环、反相、永久状态、代价、锚点、破产 | Codex + OpenCode |
| `M2-B006` | `PLANNED` | 2—6人、纠缠因果、死亡、亡者、授权 | Codex + OpenCode |
| `M2-B007` | `PLANNED` | 一个 `M2_TEST_REGION` 的结构化内容 | Codex |
| `M2-B008` | `PLANNED` | 教程/大区/异常区/稳定化运行逻辑 | Codex + OpenCode |
| `M2-B009` | `PLANNED` | 长短规则装备、大区规则、关键道具两相 | Codex + OpenCode |
| `M2-B010` | `PLANNED` | 主持动作、AI最小权限、秘密隔离 | Codex |
| `M2-B011` | `PLANNED` | 代理 Boss 与三分支 fixture/spec | Codex |
| `M2-B012` | `PLANNED` | 代理 Boss、维护缺口与三分支运行逻辑 | Codex + OpenCode |
| `M2-B013` | `PLANNED` | `TECHNICAL_PLACEHOLDER` 纯2D/地图/可访问性管线 | Codex + Grok |
| `M2-B014` | `PLANNED` | 最小 `VERTICAL_SLICE_FINAL_ART` 替换集 | Codex + Grok |
| `M2-B015` | `PLANNED` | 标准 Game Package、Host、Creator、E2E、确定性候选 | Codex |
| `M2-B016` | `PLANNED` | 固定候选的只读独立验收 | Independent Codex |

每批完整字段（authority/decision、allowed/forbidden paths、职责、probe、Schema、fixture、正负测试、验收、停止、恢复、commit boundary、Reading Map blueprint）见 `batches.json`。

## R2-INT 结论

安装阶段分类字段作为冻结历史保持不变：

- `PLATFORM_CAPABILITY_PROBE`：001、002、005、006、008、011。
- `R2_COMPATIBILITY_ADAPTER`：003、004、010、012。
- `PACKAGE_DECLARABLE`：007、009。
- `current_status=DEFERRED_WITH_NON_BLOCKING_PROOF` 是安装分类投影，不覆盖后续执行证据。

M2-B001 已按固定 formal identity 接受。历史 `R2-INT-010=FAIL` 与 M2-B001-EXT-001 根因证据保持 byte-identical；post-platform exact Rules/Platform pair 将当前有效投影推进为 `R2-INT-010=RESOLVED_ADAPTER`。这不解决 `R2-INT-011`、`R2-INT-012` 或 `DEFER-R2-C14-001`，也不使 B002 ready。

001、002、003/004、005、008、009、010、011、012 原有 checkpoint 语义继续保留。006（真结局谱系级高资源解锁）仅做接口 probe，在 production release 前阻塞，不阻塞 M2 强制成功定义。12 项的目标仓库、证据、成功/失败、平台提案与 adapter 充分性见 `capability-probes.json`。

B001 的每项结果必须持久化 `probe_id`、R2 requirement、classification、target system、existing capability、probe procedure、实际执行的 commands/actions、evidence paths、observed/expected result、execution status、root cause、adapter feasibility、platform-change necessity 与 downstream blocked batches。单项 `execution_status` 只允许 `PASS`、`FAIL`、`NOT_RUN`、`BLOCKED_EXTERNAL`、`BLOCKED_ENVIRONMENT`；它与批次最终五态分开。没有实际执行和候选绑定证据时必须是 `NOT_RUN` 或相应 blocker，不能写成 `PASS`。

## 跨执行者路由

- Codex 保留架构、Schema、结构化内容、fixture、Task Packet、集成、验证和验收编排。
- OpenCode 仅接收 B004、B005、B006、B008、B009、B012 的 `owner=opencode/task_type=script` 最小包。
- Grok 仅接收 B013、B014 的 `owner=grok/task_type=art` 公开 brief；不接触规则定义域、完整 seed、Truth Bible 或结局答案。
- 所有 packet 状态均为 `PLANNED_NOT_ISSUED`，没有执行者产物，也没有自验 PASS。

## 外部门禁

本仓库可完整验证：Schema/fixture、状态分层、seed reference parity、Lua 静态策略与本地 reference replay、M2 structured content、秘密投影、包锁与确定性构建。

TRPG_PLATFORM 必须外部验证：2—6席位、亡者私有视图/动作白名单、长战役保存与版本锁、exact-intent UI/Host 行为、终止事件、AI context isolation、运行时重复过滤。

Creator Tool 必须外部验证：namespaced Schema、Module、脚本、资产、provenance 的标准导入—编辑—导出—重导入无损往返。任何仍必要的外部门禁 `NOT_RUN` 或 FAIL 时，对应 batch 或 M2 acceptance 必须 `BLOCKED_EXTERNAL`；不得靠官方游戏特权格式绕过。`controls.json` 的外部门禁矩阵继续保存冻结计划/aggregate M2 的 `NOT_RUN` 历史，不能用已解决的单项 R2-INT-010 投影冒充 aggregate external capability PASS。

## Deferred 消耗

10 项 deferred 全部有 checkpoint：C14 在 B002 前；F12 在 B005 前；D12 在 B010 前。C13、H16、I18 只允许明确可替换的 `TEST_ONLY_PLACEHOLDER`，不能成为生产数值。E18、H20、正式六区主题与正式 Boss 人格不在 M2 消耗。完整表见 `controls.json`。

## 验收

`M2-ACC-001—031` 的 aggregate M2 矩阵仍为 `PLANNED_NOT_RUN`；这不否定已独立接受的 formal B001 与 recovery Candidate A2，也不得把它们提升为 aggregate M2 PASS。B016 必须覆盖严格验收中的 20 个对抗场景与全部 E2E 路线，并同时重跑现有基线。候选有任何修改，全部旧 evidence 失效。

## 冻结自审

- 没有修改 R2 冻结设计或真结局条件。
- DAG 无循环；没有 Lua 早于 Schema/fixture。
- 未知外部能力均先有 probe 与 blocker。
- deferred 没有被静默默认。
- 2—6人、死亡/亡者、永久异常、通用代价、三锚点、代理 Boss、三分支、seed 不可变、秘密隔离、重复安全过滤均有实现批次和验收 ID。
- 没有无验收绑定的实现包。
- `M2-B001` 生命周期已接受；冻结施工 envelope 作为历史保留。
- `M2-B002` 仍为 `PLANNED / NOT_STARTED / READY=NO`，不得开始实现或冻结 B002。
- M2 aggregate 与 aggregate external capability 均未通过。

下一允许动作：`PLAN_REMAINING_M2_B002_BLOCKERS_R2_INT_011_R2_INT_012_DEFER_R2_C14_001`。
