# Codex Delegate Return Acceptance

你正在验收 OpenCode 或 Grok 返回的任务，不得修改文件来“帮助它通过”，除非另开修复任务。

检查：

1. 读取原 Task Packet；
2. 对照 allowed_paths / forbidden_paths 检查 diff；
3. 检查执行者没有引入未授权产品决策；
4. OpenCode：检查 Lua 安全、确定性、Typed Effects、fixture 和局部测试，并自行复跑；
5. Grok：检查文件规格、命名、任务关联、provenance、明显第三方 IP/商标风险；
6. 运行项目级 `python3 tools/run_acceptance.py`；
7. 若运行输入变化，确认 lock 与确定性构建；
8. 返回 `PASS` / `FAIL` / `BLOCKED_SCOPE` / `BLOCKED_EXTERNAL`，附可复现证据。

不得仅引用执行者“已通过”的文字作为证据。
