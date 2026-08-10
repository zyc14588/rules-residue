# 09 — Strict Acceptance Standard

## 本仓库可自动完成的门禁

```bash
python3 tools/run_acceptance.py
```

该命令必须：

1. 验证所有 JSON 与内部 Schema 子集；
2. 验证决策、范围、门禁和追溯关系；
3. 验证 manifest、场景、固定向量和本地化引用；
4. 验证 package.lock；
5. 扫描 Lua 禁止 API 和第三方 IP 标识；
6. 运行全部 unittest；
7. 构建两次包并比较 SHA-256；
8. 生成机器可读与人类可读报告。

## 外部集成门禁

M0 本地 PASS 不等于正式可玩。以下仍需平台仓库或 Creator Tool 完成：

- Lua 5.5 真实语法与沙箱执行；
- Host Callback 预算与事务回滚；
- 多人 Actor 串行顺序、断线与恢复；
- Agent Gateway 权限、可见性和上下文压缩；
- Creator 导入—编辑—导出语义等价；
- 最终许可证与正式 API 兼容认证。

## 零容忍项

秘密泄漏、非权威随机、AI 直接写状态、锁文件不一致、第三方受保护内容、删除验收向量、公开发行门禁被绕过，任一项出现即 FAIL。
