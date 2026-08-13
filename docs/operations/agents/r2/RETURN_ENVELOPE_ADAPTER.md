<!-- SECTION-ID: R2-OTHER-PLATFORM-RETURN-ADAPTER -->
# R2 external-agent return envelope compatibility adapter

本适配层不改变包内 OpenCode、Grok 或 portable-agent 的冻结返回字段；它只将三种候选格式映射到仓库统一的 Codex 集成语义。

| 统一语义 | OpenCode | Grok | portable-agent |
|---|---|---|---|
| `candidate artifact` | `artifacts[]` + `changed_paths[]` | `files[]` | `candidate_commit` + `changed_paths[]` |
| `evidence` | `commands[]` + `tests[]` + artifact hashes | file hashes + `rights` + `safety` | `commands[]` + `evidence[]` |
| `limitations` | `unresolved[]` + blocked status | `self_review_findings[]` + blocked status | `findings[]` + blocked result |

三类执行者都必须返回 candidate artifact、evidence 和 limitations 三部分。任一部分无法从原生字段得到时，Codex 必须拒绝集成或返回 blocker，不得自行补写证据。

该适配不赋予外部执行者任何权威设计、Schema、机械或最终验收修改权。
