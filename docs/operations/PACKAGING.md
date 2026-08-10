# Packaging

`tools/build_package.py` 执行：

1. 严格验证项目；
2. 校验 `package.lock.json`；
3. 只收集运行输入；
4. 按相对路径排序；
5. 使用固定 ZIP 时间戳 `1980-01-01T00:00:00`；
6. 使用固定权限与压缩参数；
7. 输出包和 `.sha256`。

运行包排除 `game-package/tests/`。仓库 ZIP 与 `.trpgpkg` 用途不同：前者用于开发，后者供平台装载。
