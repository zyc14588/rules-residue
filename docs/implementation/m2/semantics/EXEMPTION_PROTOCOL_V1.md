<!-- SECTION-ID: M2-EXEMPTION-PROTOCOL-V1-DRAFT -->
# C14 独立豁免协议字段合同

状态：`UNREGISTERED_SCHEMA_CANDIDATE`。本合同仅验证声明结构，未注册到运行时，也不使完整 B002 就绪。它衔接已批准的 `OWNER-C14-TEMPLATE-APPROVAL-2026-10-07-001`，不申请重新决定 C14。

依据是 R2-C14、R2-B08 和批准提案 Section 2（SHA-256 `855ad32fe59d26783bb4b37f411813155ed984b9b1b41d65ac7c6b5b2ae61ac3`）。首版仅支持避免、削弱、推迟；安全验证天赋独立，转移不在首版中。

新增 `schemas/r2/exemption-protocol-v1.schema.json` 是独立、未注册的设计 Schema；安装的 `rule-semantic-v1.schema.json` 及其校验和保持不变。旧 `save_protocol` 不得自动转成新协议，也不得因旧 `STANDARD` 或 `PAID_SAFE_VERIFICATION` 枚举产生通用豁免。完整 B002 仍须显式完成规范化映射和调用方集成。

| 字段 | 约束 |
|---|---|
| `protocol_id / rule_id / causal_source_refs` | 绑定具体规则和因果源，不能使用通配符替代规则 |
| `exemption.applicability` | 明示作用域和资格条件引用 |
| `exemption.check` | 确定性条件，或 Host 随机请求及已记录结果事件；不得自行随机 |
| `exemption.costs` | 只引用已声明代价；个人代价要求所有者和授权证据，不规定数值 |
| `exemption.success` | `AVOID / WEAKEN / POSTPONE`；推迟必须带确定性激活条件 |
| `failure` | 即时与长期效果引用都不可省略 |
| `precedence` | 引用现有冲突规则及例外；协议本身不提升优先级 |
| `visibility / audit_contract_ref / provenance_refs` | 分离表现与机械字段，绑定审计和来源 |

普通规则使用 `exemption.kind=PER_RULE`。只有被权威源明确识别的绝对规则可使用 `NONE_ABSOLUTE`；此分支不接受检查、代价或成功字段。`exemption.absence_authority_ref` 的存在不等于批准：集成器必须从权威源解析它，并核对声明的规则身份及绝对规则分类，禁止信任包内自声明。

身份、失败、优先级、可见性与审计放在共享根对象，只有豁免分支放入 `exemption`，避免重复展开同一验证子树。每个对象拒绝未知字段，引用数组保留唯一性且最多 16 项；标识符上限 128 字符。这是候选数据格式的资源边界，不是规则数值或玩法平衡。`mechanical_only_fields` 使用语义维度名，不是 JSON 路径；清单不能取代 Host 的访问控制。平台解析器的总体资源预算仍适用，本次只证明列出的 22 个向量一致，不宣称所有最大尺寸组合均能运行。

本增量的 22 个结构向量包括 4 个正向和 18 个负向：缺检查、伪全局豁免、安全验证误作豁免、转移、Lua 随机、随机事件缺失、个人授权缺失、生产金额、无触发推迟、缺任一失败层、缺冲突绑定、玩家种子字段和伪绝对规则等。`TEST-*` 仅为教程型门禁测试引用，不新增正式场景、角色、世界真相或谜题。

这些向量已在游戏 `6caf57cd` 的原生 Schema 子集和平台 `4a35626e` 的 `internal/package/extension.Load` 入口逐例得到一致结果。此结果只验证未注册设计附件的结构兼容；不证明引用存在、个人授权真实、绝对规则已获权威分类或运行时结果正确。

设计附件检查命令（在安装候选的根目录）：

```sh
python3 -m unittest discover -s tests/m2/schema -p 'test_*.py' -v
```

完整 B002 的必需验收继续包括 M2-ACC-003/004/016/028、生产解析器一致性、引用解析/身份绑定、固定种子和事件重放、2—6 人授权与可见性，以及 `python3 tools/run_acceptance.py`。本次结构测试不能替代它们，也不能清除 INT-011/012 或将 B002 标为 READY。

本增量无 Lua、运行时登记、规则数值、代价扣除、存档迁移或美术。后续 B003/B004 在 Schema、引用解析与 fixture 独立验收后才可消费；OpenCode 仍只接合法脚本 Task Packet。
