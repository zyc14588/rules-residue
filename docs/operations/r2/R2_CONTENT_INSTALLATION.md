<!-- SECTION-ID: R2-OPS-CONTENT-INSTALLATION -->
# R2内容安装与运行转换

## 权威安装批次

只安装：

```text
docs/authority/r2/**
governance/r2/**
schemas/r2/**
affected authoring/**
operations/prompt documents
```

不修改 `game-package/**`。

## M2转换批次

每个内容对象按以下顺序：

```text
authoring object
→ normative semantic object
→ JSON Schema validation
→ versioned fixture
→ Lua task packet if needed
→ art task packet if needed
→ Codex integration
→ module registration
→ package lock update
→ local acceptance
→ deterministic build
→ independent acceptance
```

## 禁止伪编译器

除非实际实现并验收，不得宣称可以自动将任意Markdown剧情编译为runtime。R2提供的是模板、语义模型和受控转换过程。

## 玩家/GM泄漏测试

必须证明：

- Truth Bible不进入包；
- 内部可靠状态不进入玩家文本；
- 全种子清单不进入普通AI；
- Grok/OpenCode任务不包含无关终局答案；
- 辅助阅读层不直接显示真假；
- 结局审计不揭露无关未探索内容。
