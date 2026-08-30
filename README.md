<!-- SECTION-ID: M1-README-ENTRY -->
# 《规则残差》 / Rules Residue

> 独立第一方原创 TRPG 项目；TRPG_PLATFORM 的标准 Game Package、AI Agent、多人与 Creator Tool 参考实现。
>
> **核心定位：无限流 × 规则怪谈 × 异世界开放世界跑团。玩家必须在相互叠加、冲突和变化的规则中寻找生路，验证并破解规则，跨越开放世界中的规则域，逐步查清世界真相与回家的方法。**

## 当前状态

- **项目阶段**：M1 基线 + R2 权威已安装；M2-B001 已验收但后续仍受阻；M3 Story Construction Governance 仅有待 Owner 哈希批准的安装候选
- **版本**：`0.1.0-dev.1`
- **发行通道**：仅内部开发与集成验证
- **机器标识**：`org.trpgplatform.rules-residue`
- **平台接口**：`trpg.game-package/0.1-draft`
- **Lua 合同**：Lua 5.5、确定性沙箱、无网络、无文件系统、仅返回 Typed Effects
- **公开发行**：阻塞；第一方内容许可证与平台接口版本尚未最终批准

本仓库已经完成独立项目初始化，并冻结**游戏类型、核心主题、长期目标和混合开发职责边界**。当前交付仍不是完整游戏成品，而是：权威边界、P0 范围、机器决策登记、规则破解玩法骨架、Tutorial/Golden 场景、Game Package 骨架、混合开发 Task Packet、Lua 合同、静态验证与可重复打包工具。

## 游戏核心

《规则残差》不是“按规则完成副本”的线性无限流。它要求把规则本身当作游戏对象：

```text
进入未知区域 / 自由探索
        ↓
发现异常现象与明示规则
        ↓
提出规则假设
        ↓
低风险验证 / 交叉验证 / 付费试错
        ↓
确认触发条件、作用域、例外与优先级
        ↓
遵守 / 利用 / 绕过 / 破解规则
        ↓
生存、取得资源与真相残片
        ↓
改变世界状态并继续开放探索
        ↓
逐步理解异世界、无限流结构与归乡条件
```

世界由持续存在、彼此连接的区域构成。不同**规则域（Rule Domain）**可以相邻、嵌套或叠加；规则冲突时必须由机器可执行的作用域、条件和优先级解决，而不是仅靠 GM 临场解释。

## 项目边界

《规则残差》拥有并维护：

- 原创异世界、规则域、异常规则、角色模型、场景、NPC、线索、素材和本地化；
- Game Package 内的 Lua 规则逻辑与数据 Schema；
- 规则发现、假设、验证、利用与破解的游戏级语义；
- AI GM / AI 玩家所需的结构化动作、可见性和记忆投影合同；
- Tutorial Scenario、Golden Scenario 与游戏级验收向量。

TRPG_PLATFORM 拥有并维护：

- 用户、房间、Session、多人网络、权限、日志和持久化基础设施；
- Lua 沙箱、权威事务、随机数、事件提交、数据库和 AI Runtime；
- Game Package 加载、版本管理、Creator Tool 与部署能力。

**禁止将《规则残差》的规则或内容硬编码进平台核心。** 官方游戏与第三方游戏必须走相同的 Game Package 接口。

## 混合开发模型

仓库采用四角色施工平面与独立 Owner 批准平面：

- **Codex**：任务规划、拆解、依赖排序、代码/数据变更规划、最终验证与验收；
- **OpenCode**：领取由 Codex 签发的 `script` Task Packet，负责 Lua/游戏脚本编码及脚本侧自测；
- **DeepSeek Harness**：只领取 `owner=deepseek_harness`、`task_type=literary` 的已验证文学订单并返回文学候选稿；
- **Grok**：只领取由 Codex 签发且通过验证的 Visual Order Package，负责原创美术候选物及素材交付信息；
- **Owner**：独占 T1、T2、C1 Reveal 与候选精确哈希批准；
- **Codex 最终验收**：任何 worker 产物都必须重新进入独立验收，不得直接成为受信任运行输入，worker 自审不构成 PASS。

权威合同见 `docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md`；机器任务格式见 `workflow/task-packet.schema.json`。

R2 的 Codex / OpenCode / Grok / portable-agent 渐进式披露合同分别从 `.codex/prompts/r2/README.md`、`.opencode/r2/README.md`、`.grok/r2/README.md` 和 `docs/operations/agents/r2/portable-agent/README.md` 发现。

M3 Story Construction 的候选入口位于 `.codex/prompts/m3/STORY-CONSTRUCTION/README.md`；其治理作用域仅为 `CONSTRUCTION_GOVERNANCE_ONLY`，且在 Owner 批准候选精确 commit/tree 与治理哈希前不处于 ACTIVE 状态。

## 最快使用方式

需要 Python 3.11+；项目工具仅使用标准库。

```bash
python3 tools/run_acceptance.py
python3 tools/build_package.py
```

Windows PowerShell：

```powershell
py -3.11 .\tools\run_acceptance.py
py -3.11 .\tools\build_package.py
```

成功后会生成：

```text
dist/org.trpgplatform.rules-residue-0.1.0-dev.1.trpgpkg
```

`*.trpgpkg` 是确定性 ZIP 容器，内部仅包含可运行输入，不包含仓库治理文档与测试源码。

## 目录导航

```text
docs/authority/       权威设计与边界；实现不得绕过
docs/design/          尚处于草案状态的详细游戏设计
docs/architecture/    运行流、状态投影、安全和 Creator 兼容
docs/operations/      施工、素材、打包与发行流程
governance/           机器决策、范围、发布门禁和追溯矩阵
workflow/             Codex → worker → Codex 的 Task Packet、订单示例与交付队列
authoring/            剧情创作源、真相图、世界对象模板与美术 brief；不进入运行包
game-package/         平台可装载的标准游戏包源码
tools/                零依赖验证、锁文件和确定性构建工具
tests/                仓库级自动验收
.codex/               Codex 规划、施工组织与独立验收入口
.opencode/             OpenCode 脚本任务执行入口
.grok/                 Grok 美术任务执行入口
reports/               初始化与验收证据
dist/                  构建产物；除 .gitkeep 外不作为源码维护
```

## 权威读取顺序

Codex 会话先按 `.codex/SESSION_START.md` 生成并验证精确 Reading Map，再在该路由内执行以下权威读取顺序；禁止把目录通配符当作读取路由。实时 freshness 权威入口为 `just codex-check`。

R2 安装后，`governance/r2/decisions.r2.yaml` 是 191 项冻结决策的机器权威，其级别高于 M1 历史 OPEN 容器。R2 导航从 `docs/authority/r2/00_R2_AUTHORITY_ENTRY.md` 开始；M1 与 R2 冲突时按 `governance/r2/authority-map.r2.yaml` 解决，不得把 deferred 内容擅自升级。

1. `governance/r2/decisions.r2.yaml`
2. `docs/authority/r2/R2_TERMINOLOGY.md`
3. `docs/authority/r2/00_R2_AUTHORITY_ENTRY.md` 及当前任务路由的 R2 Section
4. `docs/authority/00_PROJECT_CHARTER.md`
5. `governance/decisions.json`
6. `governance/scope.json`
7. `docs/authority/01_PLATFORM_BOUNDARY.md`
8. `docs/authority/03_DESIGN_PRINCIPLES.md`
9. `docs/authority/04_RULES_AND_STATE_MODEL.md`
10. `docs/authority/05_AI_AGENT_CONTRACT.md`
11. `docs/authority/06_VISIBILITY_MEMORY_CONTRACT.md`
12. `docs/authority/07_GAME_PACKAGE_CONTRACT.md`
13. `docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md`
14. `docs/authority/09_ACCEPTANCE_STANDARD.md`
15. `docs/authority/10_OPEN_DECISIONS.md`

发生冲突时，按上述顺序处理；R2 `FROZEN` 和 M1 `ACCEPTED` 机器决策优先于草案文档，明确的 R2 supersession 优先于旧 M1 OPEN。

## 设计状态标识

- `ACCEPTED`：已经冻结，变更必须经过 Change Control Gate。
- `PROVISIONAL`：为形成可执行垂直切片而采用，可在不破坏已接受边界的前提下替换。
- `OPEN`：尚未决定，不得被实现者静默锁定。
- `REJECTED`：明确废弃或禁止。

## 许可证与原创性

`game-package/` 不得包含任何未经批准的第三方规则、模组、文本、美术、商标或专有设定。Grok 生成素材也必须记录任务 ID、生成工具、提示词摘要、人工编辑和文件哈希，不得因为“AI 生成”而跳过来源与权利审查。当前许可状态见 `LICENSE-PENDING.md`。
