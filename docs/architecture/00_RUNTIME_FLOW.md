# Runtime Flow

```text
Human/AI Input
  │
  ▼
StructuredAction schema validation
  │
  ▼
Session Actor serial queue + idempotency check
  │
  ▼
Lua plan_action(ctx, action)
  ├─ roll_request ──► Host authoritative RNG
  └─ resource_spend ─► Host validates balance/permission
  │
  ▼
Lua resolve_action(ctx, action, resolution_input)
  │
  ▼
Typed Effects validation
  │
  ▼
Atomic commit: Event + State + Outbox + Checkpoint policy
  │
  ├─ failure: full rollback; discard contaminated VM
  └─ success: derive projections
                 │
                 ├─ Human clients
                 ├─ AI GM context
                 ├─ AI player context
                 └─ Memory/summary jobs
```

外部 AI、RAG 或图像服务只能通过持久异步任务返回新系统命令，不能在 Lua 事务中阻塞或直接写状态。
