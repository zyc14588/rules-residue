# Hybrid Pipeline — 操作指南

## 新功能的推荐顺序

```text
Codex: 读取权威设计 → 生成 feature plan
Codex: 固定 Schema / interfaces / acceptance vectors
OpenCode: 编写 Lua/脚本并局部自测
DeepSeek Harness: 只按 validated Literary Order Package 生成文学候选稿
Grok: 只按 validated Visual Order Package 生成原创视觉候选物与素材记录
Codex: 接收各路候选物 → 检查订单、哈希、范围 → 更新 manifest/lock（若需要）
Codex: 运行完整 acceptance → 输出 PASS/FAIL/BLOCKED
```

## 任务目录

- `workflow/queue/`：待执行 Task Packet；
- `workflow/returns/`：执行者返回摘要或机器报告；
- `workflow/examples/`：格式示例，不作为真实待办；
- `.codex/`：规划与验收提示词；
- `.opencode/`：脚本执行提示词；
- `.grok/`：美术执行提示词。
- `docs/operations/agents/m3/deepseek-harness/`：受控文学 worker 合同；
- `.codex/prompts/m3/STORY-CONSTRUCTION/`：M3 Story Construction 唯一执行发现页与角色提示词。

不要把模型聊天记录当作唯一需求来源。重要约束必须进入 Task Packet 或权威文档。

Raw literary/art requests 均不是 production authority。OpenCode 继续保持 script-only；DeepSeek Harness 和 Grok 只能写各自受控返回路径，执行者自审不能形成最终 PASS。
