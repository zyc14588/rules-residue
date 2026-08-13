<!-- SECTION-ID: R2-OPENCODE-SCRIPT-VERIFY -->
# OpenCode脚本自检

至少检查：

- Lua语法与生产Profile；
- 禁用API；
- 固定seed重放；
- 指令/事件版本；
- 状态补丁与回滚；
- 检查点恢复；
- CPU/内存/回调预算；
- 允许路径；
- 私有视图；
- 正向与负向fixture；
- 相关R2验收向量。

输出真实命令、退出码和失败日志。此结果仅供Codex集成参考。
