# State Projections

权威状态可以包含所有参与者、场景真相和未公开线索，但任何客户端或 Agent 输入都必须先运行 `project_state`。

P0 投影算法：

1. 复制明确标记为 `public` 的字段；
2. 加入与目标 participant/team/agent 匹配的字段；
3. GM 只有在 Authority Contract 授权时获得 `gm_only`；
4. 未知或缺失 visibility 一律不可见；
5. 事件、状态、工具结果、记忆和错误日志使用同一规则；
6. 投影结果附 `source_state_revision` 和 `audience_id`。

不得先把完整状态交给模型，再依赖提示词让模型保密。
