# 贡献规则

## 分支与提交

- 每项工作使用独立分支和单一问题范围。
- 提交信息建议采用 `type(scope): summary`。
- 不得提交真实 API Key、生产数据、第三方规则书或未经授权素材。

## 变更分类

- `docs`：不改变运行合同的文档修订。
- `contract`：Schema、manifest、状态、事件或 Agent 合同变更。
- `rules`：规则数据或 Lua 规则逻辑变更。
- `content`：原创场景、NPC、线索或本地化。
- `tooling`：验证、构建、CI 和开发工具。
- `governance`：决策、范围、门禁与追溯关系。

`contract`、`rules`、`governance` 变更必须更新相应决策或追溯项。

## 本地门禁

```bash
python3 tools/run_acceptance.py
```

所有失败均视为阻塞，不接受“与本次修改无关”的未清理红灯。
