# Lua Entrypoints

这些脚本是 Game Package 合同的最小参考实现，不是独立可执行程序。

- `bootstrap.lua`：从宿主提供的已验证场景、参与者和 Authority Contract 生成初始状态。
- `plan_action.lua`：把结构化动作变成权威随机请求或资源消费请求。
- `resolve_action.lua`：消费宿主随机/批准结果并返回 Typed Effects。
- `project_state.lua`：在调用客户端或 Agent 前生成参与者投影。

宿主必须把 `scripts/` 作为只读模块根，使 `require("lib.*")` 只能加载包内白名单模块。Lua 无权提交 Effects；宿主仍需校验引用、资源上下限、权限、幂等与事务。
