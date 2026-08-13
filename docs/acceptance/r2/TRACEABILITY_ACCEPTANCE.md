<!-- SECTION-ID: R2-ACC-TRACEABILITY -->
# R2追踪与来源验收

## 决策追踪

独立验证：

```text
191 frozen decisions
= 191 decision index rows
= 191 machine register items
= 191 traceability items
```

每项至少指向：

- 权威文档；
- Schema/机器承载；
- M2工作包；
- 验收ID；
- 实现状态。

## 内容来源

每个正式内容对象至少有：

```text
author
modifiers
reviewers
mechanical consistency status
content version
approval version
safety checks
source hashes
```

修改者不能只记录最后一人。

## 版本

证明：

- 战役种子绑定内容版本；
- 进行中战役答案不被热更新静默改变；
- 无法迁移时能继续归档版本；
- 旧事件语义不被复用；
- 生成/构建产物可追溯到候选Commit/Tree和工具版本。

## 失败

缺失任一冻结决策、来源链断裂或版本不绑定：

```text
FAIL
```
