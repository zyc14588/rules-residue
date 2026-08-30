# 《规则残差》持久化提示词包使用说明

> 当前执行入口：`M3-STORY-CONSTRUCTION`，发现页为 `.codex/prompts/m3/STORY-CONSTRUCTION/README.md`。
>
> `.codex/STORY_ARCHITECTURE_BUILD_PROMPT.md` is historical only；`.codex/STORY_UPDATE_PROMPT.md` is historical and superseded，二者均不得签发新的正式文学任务。下方旧文件清单只保留 predecessor 追溯用途。

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

## 当前推荐执行顺序

### Story Construction 治理与施工

从以下发现页选择 PLAN / IMPLEMENT / ACCEPT / REPAIR，并生成绑定当前 commit/tree、route identity 与 Section-ID 的新鲜 Reading Map：

```text
.codex/prompts/m3/STORY-CONSTRUCTION/README.md
```

文学正文只通过 validated Literary Order Package 交给 DeepSeek Harness；视觉候选物只通过 validated Visual Order Package 交给 Grok；Lua/游戏脚本继续只交给 OpenCode。任何 worker 返回后都必须由独立 Codex 会话验收。

验收入口仍可使用：

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

不得回调旧 Story Update。使用 M3 PLAN 路由形成 Change Set 与订单，再由 IMPLEMENT 执行；涉及 T1/T2/C1 或候选哈希时必须取得 Owner 对精确身份的显式批准。

## 推荐纪律

1. **一次剧情更新只处理一个逻辑主题。** 例如“一座 Region + 其基础规则域”，不要一次同时重写终局真相、角色系统和 30 个 Module。
2. 剧情源先落 `authoring/`，成熟后再结构化到 `game-package/`。
3. OpenCode 不负责文学或剧情决定；DeepSeek Harness 不批准 Canon；Grok 不负责规则/真相/机械值；Codex 不应替 Owner 决定仍为 OPEN 的终极真相。
4. 所有 worker 返回后必须进入独立 Codex 验收链，worker 自审不能形成最终 PASS。
5. 对会改变既有 Campaign 世界事实的剧情修改，优先按 RETCON/存档兼容流程处理。
6. 每个施工批次结束都保留真实命令、退出码、Task Packet、产物哈希和 blocker。

## 历史建议（非执行授权）

以下内容仅保留为旧建议，不表示 M0、正式 Region 或内容生产已经获准：

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
