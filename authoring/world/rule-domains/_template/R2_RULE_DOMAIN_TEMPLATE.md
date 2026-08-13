<!-- SECTION-ID: R2-AUTHORING-RULE-DOMAIN-TEMPLATE -->
# Rule Domain 模板

```yaml
rule_domain_id:
region_id:
scope:
time_conditions:
identity_conditions:
state_conditions:
rules: []
high_permission_carriers: []
overlapping_domains: []
collision_model:
warning_signals:
entry_conditions:
exit_conditions:
break_conditions:
residue_outputs:
world_change_after_break:
loop_reset_behavior:
permanent_stabilization_behavior:
evidence_refs:
false_signal_refs:
player_visible_text_refs:
host_truth_refs:
acceptance_cases:
```

每条 `rules` 必须指向规范化规则对象，不得只写一段怪谈文本。
