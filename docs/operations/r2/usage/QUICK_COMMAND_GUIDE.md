<!-- SECTION-ID: R2-USAGE-COMMAND-GUIDE -->
# 命令使用速查

实际命令必须以仓库现行README/Justfile为准。以下只是探测顺序：

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse HEAD^{tree}

go run ./cmd/projectctl codex check
go run ./cmd/projectctl codex plan   # 参数以现行CLI为准
go run ./cmd/projectctl codex route  # 参数以现行CLI为准

python3 tools/run_acceptance.py
python3 tools/build_package.py
python3 tools/update_lock.py         # 仅game-package变化时
git diff --check
```

若仓库提供 `just`：

```bash
just --list
```

然后使用现行的 `codex-plan/codex-route/codex-check/codex-accept` 和构建验收入口。不得因为本文件示例与当前CLI不同而自行创建第二套命令。
