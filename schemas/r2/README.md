<!-- SECTION-ID: R2-SCHEMAS-README -->
# R2 Schema目录

这些Schema是R2权威语义的候选机器合同，必须由Codex根据M1现行Schema注册、代码生成和验证机制集成。

| Schema | 用途 |
|---|---|
| `rule-semantic-v1.schema.json` | 规则定义域、触发、效果、豁免、碰撞、残差与验证 |
| `region-v1.schema.json` | 大区三阶段状态、路线、奖励、阵营与Boss影响 |
| `logical-anomaly-zone-v1.schema.json` | 显著警告、非主线、不死人解和终局权限 |
| `equipment-rule-v1.schema.json` | 规则装备、长短语义与永久绑定 |
| `entangled-causality-v1.schema.json` | 纠缠因果的正负面、观察角度与演化 |
| `faction-v1.schema.json` | 阵营应对方案、认知和终局功能 |
| `campaign-seed-v1.schema.json` | 开局固定的完整不可变种子清单 |
| `reading-map-v1.schema.json` | Commit/Tree/文档/Section/预算绑定 |
| `content-provenance-v1.schema.json` | 作者、修改、审核、版本、安全与来源 |
| `acceptance-result-v1.schema.json` | 固定候选的严格验收结果 |

M2不得用这些文件直接替换现行Schema；先完成兼容性映射、负向测试和生产解析器一致性验证。
