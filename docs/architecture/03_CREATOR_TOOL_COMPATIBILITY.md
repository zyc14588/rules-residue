# Creator Tool Compatibility

《规则残差》必须通过标准 Creator Tool 路径维护，不能有隐藏官方编辑器。

## 往返不变量

导入后未编辑并重新导出时：

- manifest 的未知字段保留；
- ID、引用、可见性、脚本路径和 Schema 版本不变；
- JSON 允许格式变化，但规范化语义哈希一致；
- Lua 源码不得被无提示重写；
- 资源哈希与来源元数据保持；
- Tutorial/Golden 向量继续通过。

## 图形与 Lua 双向同步

图形节点只能表示已经声明的规则原语。无法无损表达的 Lua 代码必须作为受保护高级区段显示，Creator Tool 不得假装已完全图形化。
