<!-- SECTION-ID: R2-ACC-AUTHORITY-INSTALL -->
# R2权威安装独立验收

## 身份门禁

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse HEAD^{tree}
git log -1 --oneline --decorate
```

记录base/candidate、Reading Map digest、冻结批次摘要。工作树、索引和Git引用在验收前后必须相同。

## 必查

### 范围

- 无runtime、package、dist、平台代码变化；
- 只有冻结文档、机器登记、Schema和直接受影响authoring；
- 生成文件由现行生成器产生。

### 决策

- 191项；
- 组数量10/14/16/18/20/21/22/22/24/24；
- ID唯一；
- 选项和用户修订完整；
- 文档和机器源一致。

### M1传播

- 旧OPEN主线真相明确supersede；
- Truth Bible不含冲突ACTIVE真相；
- authoring/runtime边界保持；
- Module注册验证未退化；
- M1现行接受套件仍通过。

### Schema与追踪

- 所有JSON/YAML可解析；
- 所有Schema meta-valid；
- 191项追踪存在；
- 延期ID唯一且未被实现；
- authority-map所有路径存在。

### 安全

- 绝对红线准确；
- 每次检查重新过滤；
- 知识库不进入runtime；
- 玩家/主持/机械/审计隔离。

## 负向

在隔离临时输入中证明以下均被拒绝：

- 缺一个决策；
- 重复ID；
- 重复Section；
- 破坏Schema；
- 缺追踪；
- Truth Bible加入包；
- 删除运行时安全过滤；
- 过期路由。

## 结论

任何强制项缺少执行证据：

```text
FAIL
```

环境不允许执行强制命令：

```text
BLOCKED_ENVIRONMENT
```
