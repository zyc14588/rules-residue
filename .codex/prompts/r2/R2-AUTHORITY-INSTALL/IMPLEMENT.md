<!-- SECTION-ID: R2-CODEX-R2-INSTALL-IMPLEMENT -->
# R2权威安装：IMPLEMENT

你是Builder。只实现已冻结的R2权威安装批次，不修改计划。

## Phase 0：固定身份

验证：

```text
mode=IMPLEMENT
batch_id=exact
source commit/tree=Reading Map
frozen digest=match
worktree=clean
candidate not yet accepted
```

不一致即停止。

## Phase 1：最小集成

根据实际仓库路径完成：

1. 安装R2自然语言权威文档；
2. 安装191项机器决策与术语；
3. 安装R2 Schema草案并接入现行Schema校验入口；
4. 合并R2 authoring扩展到M1原目录；
5. 将M1相关OPEN真相标记为 `SUPERSEDED_BY_R2`；
6. 更新单一权威入口；
7. 若入口/索引是生成文件，修改机器源并运行现行生成命令；
8. 注册R2渐进式披露路线和独立验收入口。

## 不得实施

- 任何正式runtime行为；
- 关键道具Lua；
- 循环、亡者、Boss状态机；
- 正式大区内容；
- game-package Module；
- 平台适配代码；
- 未决数值。

## Phase 2：机器检查

至少增加或执行：

- `decision_count == 191`；
- 决策ID唯一且范围完整；
- 所有Markdown稳定Section ID唯一；
- YAML/JSON可解析；
- JSON Schema meta-validation；
- 决策追踪项191条；
- authority-map路径存在；
- deferred ID唯一；
-安全策略包含重复过滤阶段和未成年人绝对红线；
- 玩家/GM/机械/审计层隔离；
- `authoring/`未进入包和lock。

## Phase 3：基线回归

运行仓库现行的：

```bash
go run ./cmd/projectctl codex check
python3 tools/run_acceptance.py
python3 tools/build_package.py   # 仅当当前批未改变runtime也可用于证明构建不漂移
git diff --check
git status --short
```

实际存在 `just` 入口时使用对应命令。不得把环境未执行写成PASS。

## Phase 4：候选

提交固定候选，记录Commit、Tree、文件清单、生成命令、测试输出和哈希。进入VERIFYING，但不得自行执行独立ACCEPT。


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
