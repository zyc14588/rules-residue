<!-- SECTION-ID: R2-CODEX-R2-INSTALL-PLAN -->
# R2权威安装：PLAN

你是Planner。目标是在M1已接受工程基础上生成一个最小、可冻结、可验收的R2权威安装批次。此角色不得实施。

## 必读Section

Reading Map至少应包含：

```text
R2-INTEGRATION-M1-BASELINE
R2-INTEGRATION-CONFLICTS
R2-INTEGRATION-INSTALLATION
R2-AUTH-ENTRY
R2-AUTH-M1-INTEGRATION
R2-AUTH-DECISION-INDEX
R2-AUTH-TRACEABILITY
R2-AUTH-SAFETY
```

条件读取：

- 当前M1 OPEN/Truth/Reveal文件的直接Section；
- 现行机器决策Schema；
- 现行生成文件源；
- 现行Task Packet Schema；
- 现行接受标准。

## Phase 1：证明前置

确认：

- M1独立验收PASS且在当前可接受基线；
- M1 authoring/runtime边界存在；
- Module注册验证存在；
- 当前计划允许新增R2批次；
- 实际权威入口与机器决策源位置；
- M1中哪些OPEN项被R2显式关闭。

不满足则只生成阻塞报告，不修改计划。

## Phase 2：冲突表

逐项处理 `R2-INT-001—012`，标记：

```text
PACKAGE_DECLARABLE
PLATFORM_CAPABILITY_PROBE
PLATFORM_CHANGE_PROPOSAL
R2_COMPATIBILITY_ADAPTER
BLOCKED_DESIGN_CONFLICT
```

本批只安装权威层，平台能力冲突可以延期到M2探针，但必须有非阻塞证明。

## Phase 3：冻结任务合同

建议单独批次只允许：

```text
docs/authority/r2/**
governance/r2/**
schemas/r2/**
直接受影响的authoring/story和模板
一个现行权威入口的机器源
.codex/state/MILESTONE_PLAN.yaml（PLAN only）
```

禁止：

```text
game-package/**
dist/**
Lua/runtime implementation
TRPG_PLATFORM
正式六大区内容
```

验收至少包括：

- 191决策完整唯一；
- 稳定Section ID唯一；
- YAML/JSON/Schema有效；
- 决策→文档→Schema→验收追踪完整；
- M1 OPEN真相显式supersede；
- Truth Bible不泄漏；
- 当前M1验收仍通过；
- 无runtime变化。

## Phase 4：渐进式披露

为IMPLEMENT和ACCEPT生成不同Reading Map：

- IMPLEMENT不读取完整知识库与无关大区；
- ACCEPT可读取候选diff、全部191登记和必要权威Section；
- 接受者不读取实现者结论作为权威；
- 路由预算硬门禁生效。

## Phase 5：冻结

按仓库原生生命周期推进 `PLANNED → FROZEN`，生成冻结摘要和候选范围。不得开始实现。


## 最终输出

```text
Result: PASS | FAIL | BLOCKED_EXTERNAL | BLOCKED_ENVIRONMENT | BLOCKED_DESIGN_CONFLICT
Role:
Milestone:
Batch:
Source commit/tree:
Candidate commit/tree:
Route binding:
Changed paths:
Executed commands and exit codes:
Evidence:
Findings:
Next allowed action:
```

不得把计划、建议或未执行命令写成已完成事实。
