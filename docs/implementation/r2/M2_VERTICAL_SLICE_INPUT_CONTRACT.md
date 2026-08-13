<!-- SECTION-ID: R2-M2-INPUT -->
# M2 完整技术垂直切片输入契约

状态：`PROPOSED / REQUIRES_NATIVE_PLAN_AND_FREEZE`

## 前置

```text
M1独立验收PASS且目标基线已合并
→ R2权威安装批次PASS
→ M2由全新PLAN上下文生成原生路线
```

本文件不得直接替代 `.codex/state/MILESTONE_PLAN.yaml` 或现有 TaskEnvelope。

## 业务目标

使用一个明确标记为 `M2_TEST_REGION` 的非正式测试大区，证明以下完整链：

```text
角色创建
→ 纠缠因果
→ 角色1教程
→ 规则文本与实际规则分离
→ 高危区/逻辑异常区
→ 规则验证与豁免
→ 装备规则
→ 主要纠缠观测/解决/永久稳定
→ 死亡与亡者视角
→ TPK、信息、永久异常和重启
→ 锚点
→ 代理Boss
→ 三分支判定
→ 保存/恢复/重放/审计/确定性构建
```

## 内容范围

### 真实实现

- 一个完整测试Region；
- 3—5个互相关联Rule Domain；
- 一个逻辑完全异常区；
- 2—3个测试阵营；
- 1个Truth子图；
- 1个正式可运行Module或按M1当前Schema拆分的最小Module集合；
- 1件长规则装备、1件短规则装备；
- 1条大区独特规则；
- 关键道具两相；
- 亡者视角；
- 循环与锚点；
- 代理Boss与终局模拟。

### 只做接口/fixture

- 其余五个大区；
- 正式角色1名称与美术；
- 正式Boss人格名单；
- 正式世界文本；
- 100小时内容量；
- 真结局后高资源开局数值。

## 验收策略

每个工作包：

```text
PLAN
→ FROZEN
→ IMPLEMENT
→ fixed candidate SHA
→ independent ACCEPT
→ PASS / targeted REPAIR / BLOCKED
```

不得在一个大批次中同时实现全部M2。
