# Codex Implementation Prompt Template

请在《规则残差》仓库中完成下述任务。严格遵守 `AGENTS.md`、`.codex/SESSION_START.md` 和混合开发合同。

## 任务

`<填写单一、可验证任务>`

## 规划要求

先判断任务是否需要拆给 OpenCode（脚本）或 Grok（美术）。需要时生成合法 Task Packet；Codex 保留规格、接口、集成和验收职责。

## 允许范围

- `<文件或目录>`

## 禁止范围

- TRPG_PLATFORM 平台代码；
- 第三方规则或素材；
- 与任务无关的重构；
- 放宽验收、Schema、Lua 安全或公开发行门禁；
- 擅自定义最终世界真相或归乡条件。

## 必须满足

- 对应需求：`<RR-P0-...>`
- 对应决策：`<RR-D... / RR-P...>`
- 对应验收：`<ACC-...>`
- 修改运行输入后更新 `package.lock.json`；
- 运行 `python3 tools/run_acceptance.py`。

## 交付格式

1. 实施/任务规划摘要；
2. Task Packet（若有）；
3. 修改文件与原因；
4. 验证命令、退出码和关键输出；
5. 风险与未解决事项；
6. 最终 commit SHA（仅在被要求提交时）。
