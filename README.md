<!-- SECTION-ID: M1-README-ENTRY -->
# 《规则残差》 / Rules Residue

> 独立第一方原创 TRPG 项目；TRPG_PLATFORM 的标准 Game Package、AI Agent、多人与 Creator Tool 参考实现。
>
> **核心定位：无限流 × 规则怪谈 × 异世界开放世界跑团。玩家必须在相互叠加、冲突和变化的规则中寻找生路，验证并破解规则，跨越开放世界中的规则域，逐步查清世界真相与回家的方法。**

## 当前状态

- **项目阶段**：M0 / Project Initialization Revision 1
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

Game Package 采用三角色混合开发：

- **Codex**：任务规划、拆解、依赖排序、代码/数据变更规划、最终验证与验收；
- **OpenCode**：领取由 Codex 签发的 `script` Task Packet，负责 Lua/游戏脚本编码及脚本侧自测；
- **Grok**：领取由 Codex 签发的 `art` Task Packet，负责原创美术素材创作及素材交付信息；
- **Codex 最终验收**：任何 OpenCode/Grok 产物都必须重新进入 Codex 验收，不得直接成为受信任运行输入。

权威合同见 `docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md`；机器任务格式见 `workflow/task-packet.schema.json`。

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
workflow/             Codex → OpenCode/Grok → Codex 的 Task Packet 与交付队列
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

1. `docs/authority/00_PROJECT_CHARTER.md`
2. `governance/decisions.json`
3. `governance/scope.json`
4. `docs/authority/01_PLATFORM_BOUNDARY.md`
5. `docs/authority/03_DESIGN_PRINCIPLES.md`
6. `docs/authority/04_RULES_AND_STATE_MODEL.md`
7. `docs/authority/05_AI_AGENT_CONTRACT.md`
8. `docs/authority/06_VISIBILITY_MEMORY_CONTRACT.md`
9. `docs/authority/07_GAME_PACKAGE_CONTRACT.md`
10. `docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md`
11. `docs/authority/09_ACCEPTANCE_STANDARD.md`
12. `docs/authority/10_OPEN_DECISIONS.md`

发生冲突时，按上述顺序处理；机器登记中的 `ACCEPTED` 决策优先于草案文档。

## 设计状态标识

- `ACCEPTED`：已经冻结，变更必须经过 Change Control Gate。
- `PROVISIONAL`：为形成可执行垂直切片而采用，可在不破坏已接受边界的前提下替换。
- `OPEN`：尚未决定，不得被实现者静默锁定。
- `REJECTED`：明确废弃或禁止。

## 许可证与原创性

`game-package/` 不得包含任何未经批准的第三方规则、模组、文本、美术、商标或专有设定。Grok 生成素材也必须记录任务 ID、生成工具、提示词摘要、人工编辑和文件哈希，不得因为“AI 生成”而跳过来源与权利审查。当前许可状态见 `LICENSE-PENDING.md`。
