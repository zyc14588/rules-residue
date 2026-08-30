# Art Provenance

Grok 只能消费通过验证的 Visual Order Package；原始 art request、聊天消息或文学稿不构成 production authority。Grok 生成或辅助生成、且经独立审查后拟采用的素材必须拥有可审计来源记录。最低记录：

- `asset_id`；
- 关联 `task_id`；
- 文件路径与 SHA-256；
- 使用的生成工具/模型名称（能确定时）；
- 提示词摘要或创作说明；
- 是否包含用户提供参考图；
- 人工编辑步骤摘要；
- 许可证/权利状态；
- 审核者与审核状态。

记录还必须关联 Visual Order 的订单哈希、Canon/Dossier/Reveal refs、semantic composition proof、无障碍等价表达与 capability declaration。Grok 不得借画面补全规则、故事真相、谜题答案、机械数值或地图拓扑。

项目不得因为素材由生成式模型产生，就默认其不存在版权、商标或相似性风险。公开发行前仍需执行项目自己的素材权利门禁。
