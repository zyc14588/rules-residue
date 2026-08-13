<!-- SECTION-ID: R2-OPENCODE-SCRIPT-REPAIR -->
# OpenCode脚本修复

只在收到稳定finding时执行。

- 固定失败输入和候选；
- 复现finding；
- 只改Task Packet允许的Lua/测试路径；
- 不修改规则语义或Schema；
- 添加回归测试；
- 返回新产物哈希；
- 无法在现有语义内修复时返回 `BLOCKED_AUTHORITY_CONFLICT`。

禁止顺手重构无关脚本。
