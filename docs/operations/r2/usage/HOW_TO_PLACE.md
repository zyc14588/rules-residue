<!-- SECTION-ID: R2-USAGE-PLACE -->
# 文件放置建议

## 不要整体覆盖

先由Codex检查目标仓库。通常映射为：

```text
01_REPO_OVERLAY/docs/authority/r2/
  → <repo>/docs/authority/r2/

01_REPO_OVERLAY/governance/r2/
  → <repo>/governance/r2/

01_REPO_OVERLAY/schemas/r2/
  → <repo>/schemas/r2/

01_REPO_OVERLAY/authoring/**
  → 合并到<repo>/authoring/**，不建立第二套authoring

01_REPO_OVERLAY/docs/operations/**
  → <repo>/docs/operations/

01_REPO_OVERLAY/workflow/templates/**
  → 与现行Task Packet Schema对齐后放入<repo>/workflow/templates/

03_CODEX_PROGRESSIVE_DISCLOSURE/**
  → 按现行.codex入口设计集成，优先作为持久化提示词/路由源

04_OTHER_PLATFORM_PROGRESSIVE_DISCLOSURE/**
  → <repo>/docs/operations/agents/ 或现行混合工作流目录

05_INDEPENDENT_ACCEPTANCE_PACKET/**
  → <repo>/docs/acceptance/r2/ 或现行独立验收目录
```

## 需要由Codex决定的实际映射

- 当前权威入口文件；
- 当前机器决策Schema；
- 生成文档源；
- `.codex` prompt/route目录；
- Schema注册表；
- Task Packet样例位置；
- 独立验收证据目录。

## 绝不能放入

- `game-package/`运行包；
- `.trpgpkg`；
- package lock；
- 玩家可见内容目录；
- 普通AI默认上下文；
- `TRPG_PLATFORM`平台仓库。
