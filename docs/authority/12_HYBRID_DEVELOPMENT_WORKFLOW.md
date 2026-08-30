<!-- SECTION-ID: M1-HYBRID-DEVELOPMENT-WORKFLOW -->
# 12 — Hybrid Development Workflow

## 1. 目的

《规则残差》的 Game Package 允许多个模型并行施工，但必须防止“谁生成谁验收”、上下文漂移、资产来源不明和脚本越权。本文件定义唯一认可的交付链。

## 2. 职责矩阵

| 角色 | 主要职责 | 可以修改 | 不得自行宣布 |
|---|---|---|---|
| Codex | 读取权威设计、任务拆分、依赖排序、签发 Task Packet、代码/数据任务规划、集成、验证、独立验收 | 任务授权范围内任意仓库文件 | 未执行验收时不得宣布 PASS |
| OpenCode | Lua/游戏脚本编码、脚本局部测试、按任务包返回 diff/文件 | Task Packet 明确列出的脚本/fixture/test 范围 | 不得修改产品决策、扩大范围、批准自身实现 |
| DeepSeek Harness | 按已验证 Literary Order Package 生产 Semantic Draft 与 Literary Draft，并返回映射、自检、问题与哈希 | Task Packet 明确列出的 `workflow/returns/literary/**` | 不得创建/批准 T1、T2、C1，不得修改权威、Schema、运行时、Lua、Game Package 或批准自身文本 |
| Grok | 按已验证 Visual Order Package 生产原创概念图、角色/场景/UI 等视觉候选物 | Task Packet 明确列出的 `workflow/returns/visual/**` 及 provenance 草稿 | 不得从原始请求开工，不得定义规则、故事真相、谜题答案、机械数值、地图拓扑或批准自身素材 |
| Owner（批准平面） | T1、T2、C1 Reveal 和精确候选 commit/tree/哈希批准 | 不作为 worker Task Packet owner | 批准必须候选专属、单次、不可转移；身份或哈希改变即失效 |

## 3. 单一权威链

```text
权威设计 / 决策
      ↓
Codex 生成结构化 Task Packet / Order Package
      ↓
┌──────────────┬──────────────────┬──────────────┐
│ OpenCode     │ DeepSeek Harness │ Grok         │
│ script task  │ literary order   │ visual order │
└──────────────┴──────────────────┴──────────────┘
      ↓                 ↓                ↓
返回产物 + 自测/来源记录
      └─────────────┬────────────────────┘
                    ↓
Codex 独立检查 diff / provenance / tests
                    ↓
仓库级 acceptance
                    ↓
PASS / FAIL / BLOCKED
```

Codex 也可以执行普通代码任务，但如果任务明确分配给 worker，Codex 应优先承担规划、接口定义、fixture/验收准备和返回产物验证。执行者自检只是证据，不能形成最终 PASS。

## 4. Task Packet

所有跨模型任务必须使用 `workflow/task-packet.schema.json`。任务包至少包含：

- 唯一 `task_id`；
- `owner`：`codex` / `opencode` / `deepseek_harness` / `grok`；
- `task_type`；
- 目标与权威来源；
- 输入文件；
- 允许/禁止路径；
- 不得擅自决定的 OPEN 项；
- 可执行验收；
- 返回产物清单。

任务包一经签发，执行者不得扩大允许范围。需要新增文件或决策时返回 `BLOCKED_SCOPE` 给 Codex 重新规划。

## 5. OpenCode 脚本任务

OpenCode 的默认授权是：

- `game-package/scripts/**`；
- 任务显式列出的 `game-package/tests/**`；
- 任务显式列出的 Lua 相关 fixture。

默认禁止：

- `governance/**`；
- `docs/authority/**`；
- `game-package/manifest.json`；
- 许可证、发布门禁；
- TRPG_PLATFORM 平台源码。

每个脚本任务至少返回：修改文件、关键逻辑、自测命令与输出、未解决风险。Codex 必须重新运行测试，不能直接相信返回文本。

## 6. DeepSeek Harness 文学任务

DeepSeek Harness 只执行 `owner=deepseek_harness`、`task_type=literary`，且输入必须是通过输入哈希与订单哈希验证的 Literary Order Package。受控流程为 Coordinator → Semantic Implementer → Literary Writer → Independent Checker → Defect Router，最多两次 targeted repair。缺少 Canon 必须返回 `BLOCKED_NEEDS_CANON`。

返回包必须包含 Semantic Draft、Literary Draft、semantic mapping、source matrix、self-check、issues、version usage 与 return hashes。目标只允许在受控 return 路径；authoring、authority、governance、Schema、runtime、Lua 和 Game Package 均不可写。

## 7. Grok 美术任务

Visual Order Package 是 Grok 唯一正式订单权威；raw art request 不构成 production authority。每个视觉订单必须规定：

- asset 类型和用途；
- 视觉需求，而不是要求模仿某位在世艺术家的具体风格；
- 输出尺寸/比例/透明通道/格式；
- 禁止内容和不能出现的第三方商标/IP；
- 文件命名与放置路径；
- provenance 信息。

订单还必须携带 semantic composition proof、Canon/Dossier/Reveal refs、must/forbidden objects、空间关系、显著性、遮挡、状态连续性、无障碍等价表达、权利来源与 capability declaration。

Grok 输出进入 `game-package/assets/` 前必须由 Codex 检查文件存在、格式/尺寸（可自动检查时）、命名、任务 ID 和 provenance 完整性。素材审美是否采用最终仍由项目所有者决定。

## 8. Codex 最终验收

Codex 是流程中的**验证协调者**而不是法律或审美事实的替代者。最终验收至少检查：

- diff 严格在任务范围内；
- 需求/决策/Schema/脚本/测试一致；
- OpenCode 未越权决定产品语义；
- DeepSeek Harness 的文学稿具有有效订单/输入哈希、完整返回包，且未写入权威或运行时；
- Grok 资产具有完整 provenance，且未明显引入禁止 IP；
- 修改运行输入后 `package.lock.json` 已更新；
- `python3 tools/run_acceptance.py` 通过；
- 涉及平台或 Creator 的外部门禁没有被误报为 PASS。

## 9. 并行施工规则

Codex 可以把一个 Feature 切成：

1. `spec`：Codex 固定接口、Schema、验收 fixture；
2. `script`：OpenCode 实现 Lua；
3. `literary`：DeepSeek Harness 生产文学候选稿；
4. `art`：Grok 生产视觉候选物；
5. `integration`：Codex 合并并处理路径/manifest/lock；
6. `acceptance`：Codex 使用独立提示词验收。

边界独立且输入冻结的任务可以并行；不得让 Grok 输出决定规则参数，不得让 DeepSeek 文学稿覆盖 Canon Registry，也不得让 OpenCode 根据占位内容擅自修改规格。

## 10. 失败状态

标准状态：`PLANNED`、`IN_PROGRESS`、`RETURNED`、`PASS`、`FAIL`、`BLOCKED_SCOPE`、`BLOCKED_EXTERNAL`。

只有 Codex 验收阶段可以把跨模型 Task Packet 从 `RETURNED` 转为最终 `PASS`。
