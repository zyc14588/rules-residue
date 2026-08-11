# Authoring Modules

Authoring Module 是准备转换为 runtime Module 的局部内容设计。它不是 Campaign，也不等同于 Region 或 Rule Domain。

## 索引

| authoring module_id | 文件 | Region refs | Rule Domain refs | runtime registry path | 状态 |
|---|---|---|---|---|---|

## 提升规则

1. 完成引用完整性和秘密边界检查；
2. 把需要运行的字段显式转写为 `game-package/modules/<name>/` 中的 Schema 合法数据；
3. 如需 Lua 或美术，先签发合法 Task Packet；
4. 把 Module manifest 路径加入 `game-package/manifest.json#/content/modules`；
5. 更新 package lock 并运行验收。

未注册的 `game-package/modules/**/manifest.json` 会使验收失败；创作模板只放在本目录，不放入运行目录。
