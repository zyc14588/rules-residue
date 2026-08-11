# Art Brief 模板

```yaml
brief_id: art-brief.<slug>
asset_id: asset.<slug>
intended_asset: ""
status: PLANNED
purpose: ""
target_audience: ""
linked_content_ids: []
visual_requirements: []
originality_requirements:
  - 必须为本项目原创内容。
  - 不得直接复制任何第三方作品。
  - 不得仿制受保护角色、Logo、界面或具体作品资产。
  - 参考资料只能作为非复制性的风格或事实参考，并须按项目 provenance 政策记录。
prohibited_content:
  - 未获批准的第三方受保护内容、商标或品牌标识。
  - 要求复刻具体作品资产或受保护界面的指令。
delivery_requirements:
  dimensions: ""
  aspect_ratio: ""
  format: ""
  alpha_channel: false
  file_name: ""
  allowed_output_directory: game-package/assets/<scoped-path>/
task_packet_id: null
provenance_required: true
provenance_contract:
  standard: docs/operations/ART_PROVENANCE.md
  required_return_fields:
    tool: ""
    model_or_version: ""
    generation_method: ""
    prompt_summary: ""
    source_or_reference_summary: ""
    human_edits: ""
    final_file_hash: ""
    rights_status: pending
    review_status: pending
human_aesthetic_approval: pending
```

`provenance_contract` 是交付门禁；最终素材仍须返回独立的标准 provenance 记录，并经过人工权利与审美审核。
