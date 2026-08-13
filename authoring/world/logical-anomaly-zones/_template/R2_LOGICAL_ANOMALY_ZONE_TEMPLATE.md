<!-- SECTION-ID: R2-AUTHORING-LAZ-TEMPLATE -->
# 逻辑完全异常区模板

```yaml
zone_id:
region_id:
explicit_warning_refs: []
non_mainline_proof:
logic_conflict_pairs: []
deterministic_execution_model:
entry_lock_behavior:
no_death_solution_ref:
unsafe_solutions: []
exit_methods: []
required_for_region_resolution:
rewards: []
restart_interference:
campaign_end_authority:
accessibility_alternatives:
safety_labels: []
acceptance_cases:
```

## 硬门禁

- `explicit_warning_refs` 非空；
- `non_mainline_proof` 可验证；
- `no_death_solution_ref` 非空；
- 正确解不依赖随机死人；
- 若可终止战役，必须有额外世界内终止警告和明确动作契约。
