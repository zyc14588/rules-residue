# World Authoring

世界由持久、可重访的 Region 和可叠加的 Rule Domain 构成。

- Region 是地理/社会/资源与持久状态容器，不是一次性副本；
- Rule Domain 是异常规则的作用范围与执行语义，可跨 Region 或嵌套于其中；
- Module 是一次可装载的局部内容单元，可以引用多个 Region/Rule Domain，但不拥有整个 Region；
- Arc 以条件连接这些对象，不规定唯一游玩顺序。

## Region 索引

| region_id | 文件 | 状态 | runtime refs |
|---|---|---|---|

## Rule Domain 索引

| rule_domain_id | 文件 | 状态 | runtime refs |
|---|---|---|---|

从 `_template/` 创建条目后再加入对应索引。模板本身不得登记为内容。
