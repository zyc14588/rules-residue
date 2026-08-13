<!-- SECTION-ID: R2-CODEX-README -->
# Codex 渐进式披露施工文档组

## 角色与顺序

```text
R2权威安装：
  PLAN → IMPLEMENT → ACCEPT
                 ↘ FAIL → REPAIR → 新候选 → ACCEPT

M2垂直切片：
  PLAN → 分批冻结
       → 每批 IMPLEMENT → ACCEPT
                         ↘ FAIL → REPAIR → ACCEPT
```

每个角色必须使用新会话/新受控运行，不共享未持久化聊天记忆。

## 文件

```text
SESSION_START.md
R2-AUTHORITY-INSTALL/
  PLAN.md
  IMPLEMENT.md
  ACCEPT.md
  REPAIR.md
M2-VERTICAL-SLICE/
  PLAN.md
  IMPLEMENT.md
  ACCEPT.md
  REPAIR.md
```

## 使用原则

- 先从实际仓库生成原生Reading Map；
- 只读Reading Map列出的文件与Section；
- 软上下文55%，硬上限70%；
- 路由绑定Commit、Tree、文档哈希和稳定Section ID；
- 过期路由不能施工或验收；
- PLAN是唯一可修改里程碑计划的角色；
- ACCEPT只读且固定候选SHA；
- REPAIR只能修已有finding，不得重规划；
- OpenCode/Grok只通过合法Task Packet接收最小上下文。
