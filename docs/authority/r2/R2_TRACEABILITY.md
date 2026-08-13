<!-- SECTION-ID: R2-AUTH-TRACEABILITY -->
# R2 决策追踪矩阵

| 决策组 | 权威文档 | 主要机器承载 | 首个验证入口 |
|---|---|---|---|
| `R2-A` | `01_GAME_VISION_AND_PLAYER_CONTRACT.md` | `game-vision/player-contract` | `M2-PROBE-EXPERIENCE` |
| `R2-B` | `03_RULE_CAUSALITY_LOOP_AND_COST.md` | `rule-semantic-v1.schema.json` | `M2-ACC-RULE` |
| `R2-C` | `03_RULE_CAUSALITY_LOOP_AND_COST.md` | `campaign-seed/rule/checkpoint schemas` | `M2-ACC-LOOP` |
| `R2-D` | `04_CHARACTER_EQUIPMENT_AND_GROWTH.md` | `entangled-causality/equipment schemas` | `M2-ACC-CHARACTER` |
| `R2-E` | `02_WORLD_AND_MAIN_TRUTH.md` | `authoring Truth Bible / reveal policy` | `M2-ACC-TRUTH-ISOLATION` |
| `R2-F` | `05_CONTINENT_REGIONS_AND_FACTIONS.md` | `region/logical-zone/faction schemas` | `M2-ACC-REGION` |
| `R2-G` | `06_FINAL_BOSS_ENDINGS_AND_RETURN.md` | `ending fixtures / seed manifest` | `M2-ACC-ENDINGS` |
| `R2-H` | `07_CAMPAIGN_HOSTING_AND_RUNTIME.md` | `session/visibility/action fixtures` | `M2-ACC-HOSTING` |
| `R2-I` | `08_VISUAL_AUDIO_AND_TEXT_STYLE.md` | `art briefs/content provenance` | `M2-ACC-PRESENTATION` |
| `R2-J` | `10_CONTENT_VALIDATION_AND_RELEASE_GATES.md` | `governance/r2 + acceptance schemas` | `M2-ACC-GOVERNANCE` |

## 完整追踪要求

`governance/r2/traceability-matrix.r2.yaml` 必须为每个191项决策提供：

- 权威文档；
- 目标Schema或数据对象；
- M2工作包；
- 验收用例；
- 当前实现状态；
- 延期ID（如适用）。

任何决策缺少机器追踪时，R2权威安装验收失败。
