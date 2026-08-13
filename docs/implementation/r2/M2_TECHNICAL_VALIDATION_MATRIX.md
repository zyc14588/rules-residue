<!-- SECTION-ID: R2-M2-VALIDATION-MATRIX -->
# M2 技术验证矩阵

| ID | 领域 | 核心断言 | 执行角色 | 工作包 |
|---|---|---|---|---|
| `M2-ACC-001` | M1/R2基线 | M1 accepted; R2 installed; route fresh | Codex | `WP01` |
| `M2-ACC-002` | 191决策 | count=191; unique; all indexed/traceable | Codex | `WP01` |
| `M2-ACC-003` | 规则Schema | positive/negative/parity/unknown-field | Codex | `WP02` |
| `M2-ACC-004` | 豁免与后果 | success/failure/immediate/long-term/permanent | Codex+OpenCode | `WP02/03` |
| `M2-ACC-005` | 关键道具反相 | mainline 1→2; TPK current→opposite exactly once | OpenCode | `WP03/06` |
| `M2-ACC-006` | 继承白名单 | only permanent-prefix/cost/key item; player memory out-of-system | Codex | `WP03` |
| `M2-ACC-007` | 锚点 | nearest/original/self-built; original invalidates all others | OpenCode | `WP03` |
| `M2-ACC-008` | 永久异常 | causal attachment, cost recovery, bankruptcy | Codex+OpenCode | `WP03` |
| `M2-ACC-009` | 亡者视角 | private, tethered, no direct chat, paid intervention | Codex+OpenCode | `WP04` |
| `M2-ACC-010` | 个人代价授权 | no vote/proxy/AI spending without owner | Codex | `WP04` |
| `M2-ACC-011` | 2—6人 | all start/run/death/Boss roster paths | Codex | `WP04/08` |
| `M2-ACC-012` | 大区观测 | detailed observation without resolution | Codex+OpenCode | `WP05` |
| `M2-ACC-013` | 逻辑异常区 | explicit warning, no-death solution, non-mainline | Codex+OpenCode | `WP05` |
| `M2-ACC-014` | 逃课 | real shortcut; non-negligible loss; no perfect route | Codex | `WP05` |
| `M2-ACC-015` | 永久稳定 | resolution+extra conditions persists region/faction | OpenCode | `WP05` |
| `M2-ACC-016` | 装备长短 | semantic classifier; prose rewrite invariant | Codex | `WP06` |
| `M2-ACC-017` | 2型暴露 | world response and wrong-use ending risk | OpenCode | `WP06` |
| `M2-ACC-018` | AI权限 | no new truth/fatal rule/cost; minimal visible context | Codex | `WP07` |
| `M2-ACC-019` | 不可逆意图 | ambiguous rejected; exact world action accepted; no popup | Codex | `WP07/08` |
| `M2-ACC-020` | 代理Boss | maintenance/twisted separation; region impacts | OpenCode | `WP08` |
| `M2-ACC-021` | 维护缺口 | observable worsening; TPK reset; permanent rewards retained | OpenCode | `WP08` |
| `M2-ACC-022` | 灭世阈值 | pre-threshold intervention; post-threshold all control removed | Codex+OpenCode | `WP08` |
| `M2-ACC-023` | 真结局模拟 | six-region interfaces + test region; multi-stage outcome | Codex | `WP08` |
| `M2-ACC-024` | 回归名单 | Boss-entry lock; death/disconnect behavior | Codex | `WP08` |
| `M2-ACC-025` | 2D边界 | no 2.5D/3D required path | Codex+Grok | `WP09` |
| `M2-ACC-026` | 地图可见性 | host complete; player observed; skill recording | Codex | `WP09` |
| `M2-ACC-027` | 可访问性 | all mechanical clues have equivalent channels | Codex+Grok | `WP09` |
| `M2-ACC-028` | 红线重复过滤 | every declared stage emits current PASS evidence | Codex | `WP01-10` |
| `M2-ACC-029` | 种子不可变 | load/retry keeps answers; new seed controlled change | Codex | `WP02-10` |
| `M2-ACC-030` | 确定性构建 | same source/locks/toolchain => byte-identical package | Codex | `WP10` |
| `M2-ACC-031` | 独立验收 | read-only exact SHA/tree; no evidence reuse after change | Verifier | `WP10` |

## 证据要求

每项必须提供：

```text
exact candidate commit/tree
test or probe command
exit code
machine-readable result
relevant artifact hashes
negative/adversarial case
source mutation check
```

仅有截图、叙述、模型自评或“测试已通过”文字不构成证据。
