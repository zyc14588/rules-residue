# Content Authoring Pipeline

本文件定义 `authoring/` 创作源提升为标准 Game Package 运行内容的边界。它不声明存在自动 Markdown 编译器。

## 分层与权威性

```text
authoring source
      ↓
Codex consistency/spec pass
      ↓
structured runtime data / Schema / fixture
      ↓
OpenCode script（需要时）
DeepSeek literary candidate（需要时，先进入受控 return）
Grok visual candidate（需要时，先进入受控 return）
      ↓
Codex integration
      ↓
game-package/
      ↓
acceptance
      ↓
.trpgpkg
```

- `authoring/` 表达创作意图、关联和 GM-only 设计，不是运行时权威事实；
- `game-package/` 只接收已选定、结构化、可投影并可验证的最小内容；
- 已提交 Event/State 才是游玩事实，创作源不能覆盖运行状态；
- `dist/` 只保存确定性构建产物。

## 对象映射

| 创作对象 | 运行目标 | 转换要求 |
|---|---|---|
| Region | Campaign/Scenario 中的持久世界引用与状态字段 | 保留稳定 ID、连接、重访变化和迁移策略 |
| Rule Domain | 规则数据、条件、优先级与必要 Lua 逻辑 | 明确 scope/trigger/conditions/effects/exceptions/conflicts/priority |
| Arc | 条件、Flag、Track、Event 与 Module 入口 | 不把文件顺序转成强制章节顺序 |
| Authoring Module | `game-package/modules/<name>/` | 生成合法 Module manifest、Scenario、expected path 及必要关联文件 |
| NPC/Faction/Entity | Scenario/状态/可见性数据 | 分离公开事实、真实事实、角色认知和错误认知 |
| Clue/Hypothesis/Revelation | Fact、Event、投影与记忆来源 | 假设不能自动升级为 truth；关键线索提供失败推进 |
| Literary order | 已审核文学候选稿 | 通过 DeepSeek Harness 文学订单、T1/T2/C1 与 Codex 独立检查后才可投影；候选稿不能直接进入 runtime |
| Art brief | 已审核素材与 provenance | 通过 validated Visual Order Package、Grok 返回与 Codex 独立检查后才可进入 assets |

当前 Scenario Schema 仍是 P0 草案承载格式；无法无损表达的新语义必须先走决策/Schema/fixture 变更，不能塞进未声明字段或只留在 AI 叙事中。

## Codex consistency/spec pass

提升前至少检查：

1. ID 唯一且所有引用可解析；
2. Region、Rule Domain、Module、Arc 与 Campaign 没有被混为一层；
3. 关键路径存在失败推进，局部 ending 不冒充归乡或 Campaign 结束；
4. Rule Domain 的作用域、触发、条件、效果、例外、冲突和优先级可结构化；
5. WorldTruth、Hypothesis、confirmed knowledge、Projection 与 Agent Memory 分离；
6. 终极真相或归乡条件若仍为 `OPEN`，只保留容器和引用，不补写答案；
7. 运行所需但现有 Schema 无法表达的部分先进入显式规格/决策流程。

## Runtime Module 注册合同

`game-package/manifest.json#/content/modules` 是运行时 Module 注册权威之一。每个条目必须：

- 使用相对 `game-package/` 的规范 POSIX 路径；
- 位于 `modules/**/manifest.json`，不可通过 `..`、绝对路径或符号链接逃逸包根；
- 指向存在且符合 Module Manifest Schema 的文件；
- 使用全包唯一 Module ID；
- 引用同一 Module 目录内、存在且符合对应 Schema 的 Scenario 与 expected path；
- 与 Scenario/expected path 的 Module ID 及 classification 保持一致。

验证器会扫描 `game-package/modules/**/manifest.json`。任何未注册的可执行 Module 都会使验收失败。模板默认只放在 `authoring/**/_template/`；如兼容性 fixture 必须暂存于 `game-package/modules/`，其目录必须显式包含 `.non-runtime-module` 标记，整个子树会同时从注册发现、package lock 和 `.trpgpkg` 排除，且不得被运行注册表引用。

Tutorial 与 Golden 仍保留专用回归要求；它们不替代其他已注册 Module 的 Schema、引用和向量校验。

## 混合施工边界

- Codex：维护 authoring、数据规格、Schema/fixture、Task Packet、集成与最终验收；
- OpenCode：只在合法 `script` Task Packet 允许路径内实现 Lua/脚本；
- DeepSeek Harness：只在合法 `literary` Task Packet 与 validated Literary Order Package 下产出受控文学候选返回；
- Grok：只在合法 `art` Task Packet 与 validated Visual Order Package 下产出原创视觉候选物与 provenance 草稿；
- worker 的返回状态不是最终 PASS，Codex 必须独立检查 diff、订单/输入哈希、来源、lock 与 acceptance。

不需要脚本、文学或美术时不得制造虚假 Task Packet 或虚假工作量。

## 提升与验收清单

1. 复制创作模板并在对应 authoring 索引登记；
2. 完成一致性检查并确定最小运行投影；
3. 创建/更新结构化运行数据、Schema 和 fixture；
4. 有跨模型工作时签发合法 Task Packet，并独立复验返回产物；
5. 把 runtime Module manifest 加入包注册表；
6. 运行 `python3 tools/update_lock.py`；
7. 运行 `python3 tools/run_acceptance.py`；
8. 运行 `python3 tools/build_package.py` 后再次运行 acceptance；
9. 检查 `git diff --check` 与 `git status --short`。

## 打包与泄漏边界

`tools/lib/common.py` 只从 `game-package/` 的允许运行顶层收集文件，因此 `authoring/` 不参与 `package.lock.json`，也不进入 `.trpgpkg`。自动测试同时检查这一边界以及注册 Module 的实际入包路径。

Truth Bible、完整内部推理、美术参考和创作备注不得通过复制、manifest 引用或脚本常量绕过该边界。
