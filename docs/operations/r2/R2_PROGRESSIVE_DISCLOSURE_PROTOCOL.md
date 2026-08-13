<!-- SECTION-ID: R2-OPS-PROGRESSIVE-DISCLOSURE -->
# R2 渐进式披露协议

## 目的

让施工代理只读取完成当前角色和批次所需的最小权威内容，防止：

- 上下文膨胀；
- GM真相泄漏；
- 过期路由施工；
- 通过聊天记忆替代仓库事实；
- OpenCode/Grok越权设计；
- 验收者读取实现者结论后产生确认偏差。

## 绑定

每份Reading Map必须绑定：

```text
mode
milestone
batch_id
source_commit
source_tree
document path
document sha256
stable section IDs
context budget
binding digest
```

任一文档哈希、Commit或Tree变化，路由立即过期。

## 上下文预算

```text
soft limit = 55%
hard limit = 70%
```

软超限：删除非必要示例、历史、低风险附录并重新生成。
硬超限：停止并要求PLAN拆批，禁止继续施工。

## 披露层级

### L0：身份与停止条件

角色、目标、候选SHA、允许/禁止路径、输出Schema、停止条件。

### L1：最小权威

当前任务直接依赖的冻结决策、术语和Section。

### L2：对象规格

当前Region、Rule、Schema、Task Packet、fixture。

### L3：条件触发

只有发生冲突、失败、GM信息、迁移、红线或平台能力缺口时读取对应专题。

### L4：审计证据

仅独立验收读取候选diff、日志、哈希、CI和来源记录。

## 禁止无界读取

禁止：

- `cat docs/**/*.md`；
- 递归读取整个 `authoring/`；
- 读取全部Git历史；
- 将完整Truth Bible交给脚本或美术执行者；
- 将本知识库压缩包当作每批默认上下文；
- 读取之前模型的自然语言总结代替当前文件。

## 角色披露

| 角色 | 默认可读 |
|---|---|
| Codex Planner | 权威入口、任务相关决策、M1路线和直接依赖 |
| Codex Builder | 冻结TaskEnvelope、当前规格、允许路径、测试向量 |
| Independent Verifier | 冻结契约、候选diff、相关权威、完整强制测试 |
| OpenCode | 脚本语义、Schema、fixture、Host API边界、允许Lua路径 |
| Grok | 美术brief、公开表现、必要遮蔽、尺寸/权利/安全 |
| Portable Agent | 按角色映射，不因平台名称扩大权限 |

## 路由生成责任

PLAN模式负责生成/更新Reading Map。IMPLEMENT、ACCEPT、REPAIR不得修改冻结计划，只能拒绝过期或缺失路由。
