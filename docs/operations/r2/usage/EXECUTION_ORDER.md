<!-- SECTION-ID: R2-USAGE-EXECUTION-ORDER -->
# 执行顺序

## 阶段0：保存本交付

保留ZIP、`SHA256SUMS`、`PACKAGE_MANIFEST.yaml`和`INTEGRITY_REPORT.json`。

## 阶段1：R2权威安装PLAN

新开Codex会话，提供：

```text
03_CODEX_PROGRESSIVE_DISCLOSURE/SESSION_START.md
03_CODEX_PROGRESSIVE_DISCLOSURE/R2-AUTHORITY-INSTALL/PLAN.md
```

让Codex在实际仓库中重新生成Reading Map并创建原生批次。不要直接复制本包中的参考M2工作包到计划。

## 阶段2：R2权威安装IMPLEMENT

Planner冻结后，新开Builder会话使用：

```text
R2-AUTHORITY-INSTALL/IMPLEMENT.md
```

Builder按实际仓库路径集成 `01_REPO_OVERLAY/`，但不能修改runtime。

## 阶段3：独立ACCEPT

在隔离工作区/独立会话使用：

```text
R2-AUTHORITY-INSTALL/ACCEPT.md
05_INDEPENDENT_ACCEPTANCE_PACKET/R2_AUTHORITY_INSTALL_ACCEPTANCE.md
```

失败后只用REPAIR修复finding，再重新验收。

## 阶段4：M2 PLAN

R2安装PASS并合并后，使用：

```text
M2-VERTICAL-SLICE/PLAN.md
02_M2_IMPLEMENTATION_INPUT/**
```

让Codex按当前工程依赖生成原生M2批次。

## 阶段5：逐批施工

每批：

```text
Codex IMPLEMENT
→ 如需脚本：OpenCode Task Packet
→ 如需美术：Grok Art Task Packet
→ Codex集成与targeted测试
→ 固定候选
→ 独立Codex ACCEPT
```

## 阶段6：M2最终技术验收

最后一个M2批次执行完整 `M2-ACC-001—031`、十条E2E路线、确定性构建和安全重复过滤。

## 禁止跳步

- M1未PASS时不能安装R2；
- R2安装未PASS时不能M2；
- 不得让Builder兼任Verifier；
- 不得跳过中间批次直接做最终E2E；
- 环境BLOCK不得自动触发业务修复；
- 候选变化后旧验收证据失效。
