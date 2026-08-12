<!-- SECTION-ID: M1-CODEX-SESSION-START -->
# 《规则残差》Codex Session Start

你正在独立第一方游戏仓库工作，不是在 TRPG_PLATFORM 平台仓库工作。你同时承担混合开发流程中的**任务规划与最终验证协调**职责。

## Phase 0：只读建立事实

渐进式披露已经启用。常规 Codex 会话必须先从当前固定 HEAD 生成 Reading Map，并在读取正文前验证 `source_commit`、`source_tree`、文档 SHA-256、稳定 Section ID、route/mode/milestone/batch 与 binding digest。Reading Map 是 `.codex/routes/generated/` 下不入库的会话产物；HEAD、tree 或文档内容变化后旧 map 必须拒绝并重新生成。

不得用 `docs/**`、`authoring/**`、`*`、目录或 glob 代替明确的文件与 Section ID 路由。规划内容预算按实际选中 Section 的 UTF-8 字节计算：软限额为 55%，硬限额为 70%。软限额只能通过删减 optional Section 降至 55% 以内；超过硬限额必须 `BLOCK_AND_REPLAN`。

PLAN、IMPLEMENT、ACCEPT、REPAIR 各自在自己的固定 source commit/worktree 重新生成 Reading Map，不继承另一阶段的 map。route baseline bootstrap 例外已经关闭；后续任务不得在没有有效 Reading Map 的情况下启动。

先执行当前仓库 freshness 门禁：

```bash
just codex-check
```

随后在 Reading Map 允许的 Section 内，按 `README.md` 的权威读取顺序依次读取任务所需的最小集合，包括：

1. `AGENTS.md`
2. `README.md`
3. `governance/decisions.json`
4. `governance/scope.json`
5. `docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md`
6. `docs/authority/01_PLATFORM_BOUNDARY.md`
7. 与任务直接相关且已经路由的权威文档、Schema、脚本和测试

然后执行：

```bash
python3 tools/run_acceptance.py
```

若基线失败，先报告失败证据；除非任务明确要求，不得顺手修复无关问题。

## Phase 1：规划与路由

输出：任务理解、依赖、将修改的文件、不会修改的文件、对应决策/需求/验收 ID、主要风险。

若任务适合混合开发：

- Lua/脚本实现 → 生成 `owner=opencode` 的 Task Packet；
- 美术资产 → 生成 `owner=grok` 的 Task Packet；
- 规格、Schema、fixture、整合和最终验收 → Codex 保留。

不得为了“充分利用模型”强行拆分没有独立边界的小任务。

## Phase 2：签发 Task Packet / 最小实现

Task Packet 必须通过 schema；执行者不得靠聊天上下文猜测缺失的产品决策。保持平台解耦、确定性、规则知识分层、Typed Effects、秘密隔离和原创性。

## Phase 3：接收与严格自验

对 OpenCode/Grok 返回内容先检查范围和 provenance，再更新锁文件并运行完整验收。报告真实命令、退出码、变更文件和剩余 blocker。不得把执行者自测当成最终验收证据。
