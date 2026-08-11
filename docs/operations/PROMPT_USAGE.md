# 《规则残差》持久化提示词包使用说明

## 文件放置

将本包内容覆盖/复制到《规则残差》仓库根目录：

```text
.codex/
├── BUILD_AND_INTEGRATION_PROMPT.md
├── STRICT_ACCEPTANCE_PROMPT.md
├── STORY_ARCHITECTURE_BUILD_PROMPT.md
└── STORY_UPDATE_PROMPT.md

docs/operations/
└── PROMPT_USAGE.md
```

这些文件不会替换现有：

```text
.codex/SESSION_START.md
.codex/IMPLEMENTATION_PROMPT.md
.codex/ACCEPTANCE_PROMPT.md
.codex/TASK_PLANNER_PROMPT.md
.codex/DELEGATE_ACCEPTANCE_PROMPT.md
```

新文件作为更严格的长期入口；旧模板仍可用于小任务。

## 推荐执行顺序

### 第一次：建立正式剧情架构

开启一个新的 Codex 会话，提供仓库，并把：

```text
.codex/STORY_ARCHITECTURE_BUILD_PROMPT.md
```

完整粘贴给 Codex 执行。

目标是先完成 M1-CONTENT-ARCHITECTURE，不开始大规模写正式主线。

完成后，**另开一个独立 Codex 会话**，使用：

```text
.codex/STRICT_ACCEPTANCE_PROMPT.md
```

严格验收 M1。

### 日常编码/集成批次

使用：

```text
.codex/BUILD_AND_INTEGRATION_PROMPT.md
```

在“本次任务输入”填写具体目标。Codex 负责拆 Task Packet；Lua 给 OpenCode，美术给 Grok，最后回 Codex 集成。

完成后另开独立 Codex 会话，使用严格验收提示词。

### 每次剧情新增/重写

使用：

```text
.codex/STORY_UPDATE_PROMPT.md
```

把你的剧情决定粘贴到“本次剧情变更”。Codex 先更新 `authoring/`，再判断哪些内容需要转为 runtime、OpenCode 脚本任务或 Grok 美术任务。

## 推荐纪律

1. **一次剧情更新只处理一个逻辑主题。** 例如“一座 Region + 其基础规则域”，不要一次同时重写终局真相、角色系统和 30 个 Module。
2. 剧情源先落 `authoring/`，成熟后再结构化到 `game-package/`。
3. OpenCode 不负责决定剧情；Grok 不负责决定规则；Codex 不应替项目所有者决定仍为 OPEN 的终极真相。
4. OpenCode/Grok 返回后必须进入独立 Codex 验收链。
5. 对会改变既有 Campaign 世界事实的剧情修改，优先按 RETCON/存档兼容流程处理。
6. 每个施工批次结束都保留真实命令、退出码、Task Packet、产物哈希和 blocker。

## 推荐的第一批剧情工作

完成 M1-CONTENT-ARCHITECTURE 后，建议第一批只设计：

```text
第一片正式 Region
    +
3–5 个彼此有关联的 Rule Domain
    +
1 个非线性 Truth 子图
    +
1 个正式可玩 Module
```

这样可以先验证开放世界、规则叠加、规则破解、线索泄漏和混合开发链，再扩展整季内容。
