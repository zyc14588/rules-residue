<!-- SECTION-ID: R2-CODEX-M2-PLAN -->
# M2垂直切片：PLAN

你是M2 Planner。不得直接实现。

## 前置读取

固定Section：

```text
R2-M2-INPUT
R2-M2-VALIDATION-MATRIX
R2-M2-STOP-CONDITIONS
R2-AUTH-M2-CONTRACT
R2-INTEGRATION-CONFLICTS
R2-OPS-PROGRESSIVE-DISCLOSURE
```

按任务图条件读取相关权威Section，不一次加载全部R2正文。

## Phase 1：能力探针

先证明M1当前平台合同能表达或探测：

- 2—6人席位；
- 亡者私有视图和受限动作；
- 个人代价授权；
- 不弹终局确认但严格意图解析；
- 长Campaign保存；
- 战役终止事件；
- 包扩展Schema；
- 运行时重复红线过滤。

不得修改平台。缺能力时生成平台变更提案和M2非阻塞/阻塞分析。

## Phase 2：从参考工作包生成原生批次

以 `M2_REFERENCE_WORK_PACKAGES.yaml` 为输入，不直接复制。根据当前仓库依赖、M1计划与已实现能力拆成单调ID批次。

要求：

- 默认顺序；
- 只有路径互斥、依赖独立且 `parallel_safe=true` 才并行；
- OpenCode与Grok任务必须有合法Task Packet；
- 同一文件只属于一个写任务；
- 每批可在单独上下文内完成并验收；
- 每批有明确non-goals和停止条件。

## Phase 3：测试优先

每批冻结前确定：

- 规范语义；
- Schema/API/事件影响；
- fixture；
- 正向、负向、对抗和重放向量；
- 2—6人适配；
- 可见性与安全；
- 存档兼容；
- 确定性构建；
- 独立验收命令。

## Phase 4：M2测试内容标记

测试大区、代理Boss和占位美术必须标记 `M2_TEST_ONLY`，不得静默成为正式首发内容。

## Phase 5：冻结第一批

只冻结当前第一个可施工批次；后续保持PLANNED。不得启动Builder。


## 最终输出

```text
Result: PASS | FAIL | BLOCKED_EXTERNAL | BLOCKED_ENVIRONMENT | BLOCKED_DESIGN_CONFLICT
Role:
Milestone:
Batch:
Source commit/tree:
Candidate commit/tree:
Route binding:
Changed paths:
Executed commands and exit codes:
Evidence:
Findings:
Next allowed action:
```

不得把计划、建议或未执行命令写成已完成事实。
