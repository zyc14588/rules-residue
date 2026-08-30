# Codex Mixed-Development Task Planner

目标：把一个《规则残差》Feature 转成可独立执行、可验收的任务图。

1. 读取 `AGENTS.md`、权威设计、决策、scope 和混合开发合同。
2. 识别 Feature 的 authoritative semantics；若触及 OPEN 决策，停止该部分并标为 `BLOCKED_DECISION`。
3. 优先由 Codex 固定 Schema、接口、fixture 与验收向量。
4. 把 Lua/游戏脚本实现拆为 `owner=opencode`、`task_type=script`。
5. 把文学正文拆为 `owner=deepseek_harness`、`task_type=literary`，并从 `.codex/prompts/m3/STORY-CONSTRUCTION/README.md` 取得结构化订单；OpenCode 不得承接文学任务。
6. 把原创美术拆为 `owner=grok`、`task_type=art`，只签发通过 `VALIDATED_VISUAL_ORDER_PACKAGE` 门禁的订单。
7. 每个 Task Packet 都必须列出 allowed_paths、forbidden_paths、acceptance 与 expected_outputs。
8. 不把同一文件同时交给两个并行任务修改。
9. 最后保留一个 `owner=codex` 的 integration/acceptance 任务；worker 自审不得形成最终 PASS。
10. 用 `workflow/task-packet.schema.json` 校验所有任务包后才允许签发。
