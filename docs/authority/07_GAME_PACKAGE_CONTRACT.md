# 07 — Game Package Contract

## 包身份

- Package ID：`org.trpgplatform.rules-residue`
- Version：SemVer 开发版本
- Host API：`trpg.game-package/0.1-draft`
- Lua：5.5
- 入口：`bootstrap`、`plan_action`、`resolve_action`、`project_state`

## 运行约束

- 无网络、文件系统、系统时钟、环境变量、进程、动态库和 debug；
- 无脚本随机；
- 所有输入由宿主提供且带 Schema 版本；
- 所有输出为 JSON 可序列化数据；
- 宿主对 CPU、内存、指令、回调次数和输出大小实施硬预算；
- 失败时事务完整回滚，污染 VM 必须销毁并从 Checkpoint 重建。

## 锁文件

`package.lock.json` 记录全部运行输入的相对路径、字节数和 SHA-256，不包含自身与 `tests/`。构建前必须校验锁文件；打包顺序、时间戳和权限元数据固定，确保相同源码产生相同包哈希。

## Creator Tool

Creator Tool 必须能读取 manifest、规则数据、场景、Schema、脚本和本地化。未知字段在往返时必须保留；不允许仅官方内部工具才能生成的隐藏二进制区段。

## 兼容性

当前 Host API 为草案。平台正式版本发布后，必须：

1. 记录兼容范围；
2. 提供 manifest/状态/场景迁移；
3. 用 Golden Scenario 证明前后语义；
4. 禁止静默加载不兼容包。
