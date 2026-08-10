# Hybrid Pipeline — 操作指南

## 新功能的推荐顺序

```text
Codex: 读取权威设计 → 生成 feature plan
Codex: 固定 Schema / interfaces / acceptance vectors
OpenCode: 编写 Lua/脚本并局部自测
Grok: 并行生成所需原创美术与素材记录
Codex: 接收两路产物 → 检查范围 → 更新 manifest/lock（若需要）
Codex: 运行完整 acceptance → 输出 PASS/FAIL/BLOCKED
```

## 任务目录

- `workflow/queue/`：待执行 Task Packet；
- `workflow/returns/`：执行者返回摘要或机器报告；
- `workflow/examples/`：格式示例，不作为真实待办；
- `.codex/`：规划与验收提示词；
- `.opencode/`：脚本执行提示词；
- `.grok/`：美术执行提示词。

不要把模型聊天记录当作唯一需求来源。重要约束必须进入 Task Packet 或权威文档。
