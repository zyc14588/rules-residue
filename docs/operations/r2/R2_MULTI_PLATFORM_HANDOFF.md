<!-- SECTION-ID: R2-OPS-MULTI-PLATFORM-HANDOFF -->
# Codex / OpenCode / Grok / 其他Agent交接合同

## Codex

负责：

- 读取当前仓库事实；
- PLAN与冻结范围；
- 规范语义、Schema、fixture与Task Packet；
- 接收脚本/美术；
- 自己重跑验证；
- 集成、构建与候选提交；
- 生成独立验收输入。

不得让Codex实现者自行批准候选。

## OpenCode

只实现明确Lua/游戏脚本任务：

- 不修改权威文档、Schema、治理和美术；
- 不发明新规则、代价、真相或结局；
- 使用固定随机、时钟、文件、网络和Host API边界；
- 返回diff、测试、未决项和来源哈希；
- 自测不等于验收。

## Grok

只生产明确原创2D资产：

- 不决定机械；
- 不访问完整Truth Bible或种子；
- 不使用第三方受保护素材；
- 返回源文件、派生文件、哈希、尺寸、权利声明和安全自检；
- 不把内部结构标签画进玩家资产。

## 其他平台Agent

必须映射到 `Planner / Builder / Verifier / Repair / Script Worker / Art Worker` 之一。平台具备更强工具权限也不得扩大任务权限。

## 返回状态

```text
RETURNED
BLOCKED_INPUT
BLOCKED_AUTHORITY_CONFLICT
BLOCKED_ENVIRONMENT
REJECTED_SCOPE
```

只有Codex集成者可以将RETURNED产物纳入候选，只有独立验收者可以给出最终PASS。
