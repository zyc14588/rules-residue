<!-- SECTION-ID: M3-DEEPSEEK-PRECONTENT-M0-PROFILE -->
# DeepSeek Harness synthetic M0 reference-profile candidate

```yaml
profile_id: TEST-DEEPSEEK-HARNESS-PRECONTENT-M0-R1
provider_id: DEEPSEEK-HARNESS
requested_model: deepseek-v4-pro
harness_mode: minimal
thinking: enabled
reasoning_effort: high
complexity: medium
max_input_tokens: 120000
max_output_tokens: 24000
modality: text
certificate_subject: PROVIDER
authorization_in_m3_b002: CONTRACT_ONLY_NO_CALL
certification_status: NOT_CERTIFIED
namespace_prefix: TEST-
canon: false
release_eligible: false
promotion_allowed: false
disposition: TEST_EVIDENCE_ONLY
```

Every future B003 run must bind requested alias, resolved model, Provider revision,
actual fingerprint when available, Harness/adapter identity, configuration hash,
policy evidence, data-control evidence, jurisdiction, input/order/context hashes,
output hashes, rights obligations, cost, and latency. Alias-only identity cannot satisfy
a resolved-identity or fingerprint gate. M3-B002 does not invoke Harness.
