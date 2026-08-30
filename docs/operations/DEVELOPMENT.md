# Development

## 依赖

- Python 3.11+
- 平台集成阶段：Lua 5.5 宿主或 TRPG_PLATFORM 测试环境
- 可选：`just`

本仓库自动验收不下载依赖。

## 混合开发职责

- Codex：先规划、拆分 Task Packet、定义验收，最后独立验证；
- OpenCode：脚本任务实施；
- DeepSeek Harness：只按已验证文学订单生产文学候选稿；
- Grok：只按已验证视觉订单生产原创视觉候选物；
- Owner：独占 T1/T2/C1 与候选精确哈希批准；
- 所有跨模型交付遵循 `docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md`。

## 常用命令

```bash
python3 tools/validate_project.py
python3 tools/validate_story_construction_governance.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tools/update_lock.py
python3 tools/build_package.py
python3 tools/run_acceptance.py
```

修改 `game-package/` 运行文件后先更新锁文件，再运行验收。不要手工修改哈希。

剧情创作从现有 `authoring/` 权威源开始；M3 路由从 `.codex/prompts/m3/STORY-CONSTRUCTION/README.md` 进入。创作源到运行内容的提升、Module 注册和泄漏边界见 `CONTENT_AUTHORING_PIPELINE.md`。不要直接把 Truth Bible、文学候选稿、订单或治理产物复制进 Game Package。
