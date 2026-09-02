<!-- SECTION-ID: M3-GROK-PRECONTENT-RETURN -->
# Grok synthetic M0 return contract

Only a separately authorized M3-B003 run may return evidence under this contract.

```yaml
schema_version: rules-residue.grok.precontent-return/1.0.0
task_id:
order_id:
run_id:
status: RETURNED|BLOCKED_INPUT|BLOCKED_AUTHORITY_CONFLICT|BLOCKED_ENVIRONMENT
provider_id: XAI-GROK-CLI
requested_model_alias:
resolved_model:
provider_revision:
actual_fingerprint:
adapter_identity:
configuration_sha256:
input_sha256:
order_sha256:
context_manifest_sha256:
output_files:
  - path:
    role: SOURCE|EXPORT|METADATA
    sha256:
    dimensions:
rights:
  status: RIGHTS_PENDING
  original: true
  source_license_provenance: []
  rights_obligations: []
safety:
  result: PASS|FAIL
accessibility_notes: []
self_review_findings: []
authority_changed: false
private_chain_of_thought_recorded: false
```

`authority_changed=true`, unresolved actual identity, missing provenance, or safety failure
invalidates the return. Worker self-review cannot form final PASS. M3-B002 creates no return.
