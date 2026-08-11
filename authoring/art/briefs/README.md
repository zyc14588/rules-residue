# Art Briefs

## 索引

| brief_id | 用途 | Task Packet | 输出路径 | 状态 |
|---|---|---|---|---|

## 必填字段

下列字段就是 `_template/ART_BRIEF.md` 的顶层必填合同；字段即使暂时未知也必须保留，并使用 `null`、空字符串或 `pending` 明示未完成状态。

<!-- art-brief-required-fields:start -->

- `brief_id`
- `asset_id`
- `intended_asset`
- `status`
- `purpose`
- `target_audience`
- `linked_content_ids`
- `visual_requirements`
- `originality_requirements`
- `prohibited_content`
- `delivery_requirements`
- `task_packet_id`
- `provenance_required`
- `provenance_contract`
- `human_aesthetic_approval`

<!-- art-brief-required-fields:end -->

`delivery_requirements` 必须给出尺寸、比例、格式、透明通道、文件名和允许输出目录。`originality_requirements` 必须明确项目原创、禁止复制或仿制受保护内容，以及参考资料的非复制性使用与来源记录要求。

## Provenance 返回合同

最终返回物必须按 `docs/operations/ART_PROVENANCE.md` 提供标准 provenance 记录。Brief 中的 `provenance_contract.required_return_fields` 至少要求：`tool`、`model_or_version`、`generation_method`、`prompt_summary`、`source_or_reference_summary`、`human_edits`、`final_file_hash`、`rights_status`、`review_status`。这些字段定义交付要求，不替代最终素材旁的标准 provenance 记录，也不代表权利或审美审核已经通过。
