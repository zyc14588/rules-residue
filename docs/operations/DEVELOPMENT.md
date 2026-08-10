# Development

## 依赖

- Python 3.11+
- 平台集成阶段：Lua 5.5 宿主或 TRPG_PLATFORM 测试环境
- 可选：`just`

本仓库自动验收不下载依赖。

## 混合开发职责

- Codex：先规划、拆分 Task Packet、定义验收，最后独立验证；
- OpenCode：脚本任务实施；
- Grok：美术素材生成；
- 所有跨模型交付遵循 `docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md`。

## 常用命令

```bash
python3 tools/validate_project.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tools/update_lock.py
python3 tools/build_package.py
python3 tools/run_acceptance.py
```

修改 `game-package/` 运行文件后先更新锁文件，再运行验收。不要手工修改哈希。
