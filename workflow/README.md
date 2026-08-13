<!-- SECTION-ID: M1-WORKFLOW-README -->
# Workflow

本目录保存跨模型 Task Packet 与返回记录。

- `queue/`：待执行任务；
- `returns/`：执行者返回机器摘要；
- `examples/`：格式示例，不代表真实 backlog；
- `task-packet.schema.json`：任务包唯一 Schema。

Task Packet 不取代 Git diff、测试或验收证据，只负责使不同模型之间的职责和输入输出可审计。

R2 概念候选已无损转换为符合本仓库唯一 `task-packet.schema.json` 的 JSON 示例：`examples/r2-script-task-packet.json` 与 `examples/r2-art-task-packet.json`。示例只是未签发输入，不表示 M2 已开始。
