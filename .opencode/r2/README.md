<!-- SECTION-ID: R2-OPENCODE-README -->
# OpenCode施工组

用途：只实现Lua 5.5 Platform Profile及脚本侧fixture/test。

## 推荐顺序

```text
SESSION_START
→ SCRIPT_IMPLEMENT
→ RETURN_CONTRACT
→ Codex集成
```

发生独立finding时使用 `SCRIPT_REPAIR`。`SCRIPT_VERIFY`用于OpenCode自检，不能替代独立Codex ACCEPT。
