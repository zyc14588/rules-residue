<!-- SECTION-ID: R2-INTEGRATION-M1-BASELINE -->
# M1 工程基线绑定与重验证要求

## 已知输入

用户报告的 M1 剧情架构候选：

```text
task/result: M1-CONTENT-ARCHITECTURE-RECOVERY-002 / PASS
branch: design/r1-story-architecture
HEAD: a14fdfca42af2848aa72ddc4d2fd73b8917e152f
inspection: HEAD → 当前 tracked/untracked 工作树
```

上述内容是本包的**提交时参考**，不是本包在用户仓库中独立复核得到的事实。

## M1 可复用工程基础

R2 集成只允许复用并扩展以下 M1 契约：

1. `authoring/` 是创作源、Truth Bible、Mystery Graph、Region、Rule Domain、NPC、线索与美术 brief 的维护层；
2. `game-package/` 是经过结构化并可被平台装载的运行输入；
3. `authoring/` 不得进入 `.trpgpkg`、package lock 或玩家运行时可见数据；
4. Region、Rule Domain、Arc、Authoring Module、NPC/Faction/Entity、Clue/Hypothesis/Revelation 具有不同职责；
5. Module 验证采用注册表驱动，不得只验证 tutorial/golden；
6. 内容转换链为规格优先，脚本交付给 OpenCode，美术交付给 Grok，最终由 Codex 集成并独立验收；
7. `projectctl` / `.codex` 路由必须使用稳定 Section ID、精确 Commit/Tree/文档哈希和上下文预算。

## R2 集成前机器复核

Codex 必须在目标仓库执行并持久化：

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse HEAD^{tree}
python3 tools/run_acceptance.py
go run ./cmd/projectctl codex check
```

实际命令若已由 `Justfile` 封装，应优先使用仓库现行入口，例如：

```bash
just codex-check
just check
just test
```

必须读取实际仓库中的：

```text
AGENTS.md
README.md
governance/decisions.*
governance/scope.*
docs/authority/**
.codex/SESSION_START.md
.codex/state/MILESTONE_PLAN.yaml
authoring/**
game-package/manifest.*
schemas/**
workflow/task-packet.schema.*
tools/run_acceptance.py
tools/build_package.py
```

但不得无界读取整个 `docs/**`、全 Git 历史或聊天记录。具体文件与 Section 必须由 PLAN 路由生成。

## 基线判定

仅当以下全部成立才可开始 R2 集成：

```text
M1_BASELINE_EXISTS=PASS
M1_INDEPENDENT_ACCEPTANCE=PASS
TARGET_BRANCH_ALLOWED=PASS
TARGET_HEAD_PINNED=PASS
TRACKED_WORKTREE_CLEAN=PASS
CODEX_ROUTE_FRESH=PASS
CURRENT_ACCEPTANCE_BASELINE=PASS
AUTHORING_RUNTIME_BOUNDARY_PRESENT=PASS
MODULE_REGISTRY_VALIDATION_PRESENT=PASS
```

任一失败：

```text
R2_AUTHORITY_INSTALL_BLOCKED_M1_BASELINE
```

不得通过本交付包反向补做或掩盖 M1 未完成工作。
