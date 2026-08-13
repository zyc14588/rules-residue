<!-- SECTION-ID: R2-OPENCODE-SCRIPT-IMPLEMENT -->
# OpenCode Lua脚本施工

## 实施顺序

1. 验证Task Packet和输入哈希；
2. 阅读当前规则语义、Schema、fixture与Host API；
3. 先写/确认失败测试；
4. 实现最小Lua；
5. 运行脚本侧targeted测试；
6. 检查确定性、预算、回滚、检查点和重放；
7. 输出Return Manifest。

## R2硬约束

- 规则触发、定义域、豁免、即时/长期效果均由输入语义决定；
- TPK道具反相只能执行一次；
- 团灭信息只从候选池选择一个单元；
- 亡者不能直接向活人频道发送内容；
- 亡者活动受关键道具距离限制；
- 个人通用代价必须验证持有人授权；
- 原初锚点被选中后其他锚点全部失效；
- 结局阈值后拒绝一切动作；
- 不得用显示中文字符串作为逻辑键；
- 固定种子与相同状态必须产生可重放结果。

## 停止

语义不完整或Schema冲突：

```text
BLOCKED_AUTHORITY_CONFLICT
```

不要自行选择常见实现。
