<!-- SECTION-ID: R2-CODEX-M2-IMPLEMENT -->
# M2垂直切片：IMPLEMENT

你是当前M2批次Builder。只执行当前冻结批次。

## 规格优先

按顺序实施：

```text
authoritative semantics
→ Schema/API/event
→ fixtures/acceptance vectors
→ OpenCode/Grok Task Packets
→ receive returns
→ independent local integration review
→ runtime implementation
→ targeted tests
→ fixed candidate
```

不要先写自由Lua或生成美术再反推规则。

## OpenCode委派

当任务需要Lua时，Task Packet只披露：

- 当前规则语义；
- 当前Schema；
- Host API允许清单；
- fixture和测试；
- allowed/forbidden paths；
- 明确延期ID。

OpenCode不得读取完整Truth Bible、修改Schema或发明机制。

## Grok委派

只披露：

- 当前2D brief；
- 必须/禁止表现；
- 规则信号强度；
- 尺寸、格式、权利、安全；
- 必要但最小的秘密遮蔽。

Grok不得决定规则或读取全种子。

## 关键工程约束

- Lua全局变量不是权威状态；
- 所有权威变化通过命令/事件；
- 固定随机种子可重放；
- 会话存档与因果锚点分离；
- 不通过文本字符串比较执行规则；
- 不允许未声明文件/网络/时钟/进程能力；
- AI结构化动作先验证后提交；
- 结局阈值后所有动作拒绝；
- 个人代价消费需要持有人授权证据；
- 红线过滤每个声明阶段重新执行。

## 验证

Builder只跑当前批受影响、回归和必要静态测试。完整批次强制套件由独立Verifier执行。

若遇到设计或平台冲突，停止并返回明确BLOCKED，不得通过降级R2语义绕过。


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
