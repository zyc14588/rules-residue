<!-- SECTION-ID: R2-OTHER-PLATFORM-README -->
# 其他平台渐进式披露施工文档组

本目录不是让多个平台并行改同一批文件，而是提供等价的最小权限合同。

## 包含

- `opencode/`：Lua与游戏脚本执行者；
- `grok/`：原创纯2D美术执行者；
- `portable-agent/`：可映射到Claude Code、Gemini CLI、Cursor、GitHub Copilot coding agent、ChatGPT Agent等通用工具的角色协议。

## 统一原则

1. 平台能力不会自动扩大任务权限；
2. 每个任务必须有权威引用、输入哈希、允许/禁止路径、输出和验收；
3. 只披露当前任务所需Section，不读取完整Truth Bible或种子；
4. 返回物必须由Codex集成并重验；
5. 执行者不能批准自身产物；
6. 任何平台都不得输出私密思维链作为验收证据。
