<!-- SECTION-ID: M3-SCG-PRECONTENT-READINESS -->
# Pre-Content Readiness and TEST-only M0 Framework

```text
AUTHORITY_SCOPE = CONSTRUCTION_GOVERNANCE_ONLY
R2_CANON_PRECEDENCE = HIGHER
MILESTONE = M3
BATCH = M3-B002
LIFECYCLE = APPROVED + ACTIVE + NOT_RELEASED
APPROVAL = PENDING_OWNER_ACTIVATION_HASH_APPROVAL_M3_B002
TRACKED_TARGET_STATE = TRACKED_B002_TARGET_STATE_ACTIVE
ACTIVE_WIP = TRUE
AUTHORITATIVE_ACTIVATION_EFFECTIVE = FALSE
```

M3-B002 binds `SCG-PRE-Q001` through `SCG-PRE-Q021` append-only and installs a
synthetic, permanently non-promotable M0 validation framework. It changes no R2 Canon,
authoring source, Game Package, runtime input, Lua, platform code, or M2 machine state.

The accepted implementation Candidate is fixed at `74fecbe6984f150f83c364e5d5a5850132cfc147`
with tree `b81fa075a1b812478dbc3e196429c7392279e28f`. Its single-use implementation Owner
approval has been consumed by `SCG-PRECONTENT-M3-B002-ACCEPT-001`, which returned
`PASS_FIXED_M3_B002_CANDIDATE_ACCEPTED`. That approval and ACCEPT do not transfer to the
tracked activation Candidate.

Model B preserves the 68-record R1 manifest and pending receipt byte-for-byte, then adds an R2
manifest with exactly 61 unchanged old leaves, seven changed old leaves, eight new semantic leaves,
and 76 total leaves. Approval consumption, receipts, future approval/ACCEPT, detached envelope/tag,
and remote state remain outside the Merkle. The original 20 schemas are immutable; exactly five
activation lifecycle/audit schemas are additive.

The accepted `d80aae8` activation Candidate is retained as closeout-defective historical evidence.
Its additive authoritative-effect repair preserves the R2 manifest and the R1 final receipt
byte-for-byte, then adds an R3 manifest with exactly 70 unchanged old leaves, six changed old
leaves, five new semantic leaves, and 81 total leaves. The three repair schemas extend—but do not
repurpose—the five activation-v1 schemas, yielding the fixed `20 + 5 + 3 = 28` schema topology.
The R3 manifest, R3 receipt, future repair approval/ACCEPT, detached envelope/tag, and local or
remote ref state remain outside the semantic Merkle.

Tracked state remains `APPROVED + ACTIVE + NOT_RELEASED`, `active_wip=true`, and
`authoritative_activation_effective=false`. The repository-native `authoritative-effect` phase is
the only interface that may compute the external projection. It fails closed unless an explicit
new repair Owner approval, exactly one independent repair ACCEPT consumption event, canonical v2
closeout envelope, matching annotated tag, exact local authoritative branch, and a single strictly
parsed remote branch/tag snapshot all bind the same one-commit repair Candidate. A complete valid
proof computes `AUTHORITATIVE_M3_B002_EFFECTIVE=true`, `effective_active_wip=false`, and
`global_active_WIP=0` without writing tracked state. Normal acceptance remains offline.

Every synthetic story artifact uses the `TEST-` namespace and the fixed boundary
`canon=false`, `release_eligible=false`, `promotion_allowed=false`, and
`disposition=TEST_EVIDENCE_ONLY`. Renaming or copying a TEST identity into a formal
identity is forbidden; useful ideas must re-enter through a new Change Set.

Provider profiles in this batch are contract-only candidates. DeepSeek Harness, Grok,
OpenCode, and Story M0 execution counts remain zero. Any network-capable wrapper is
default-deny and requires a separately approved M3-B003 authorization envelope.

Pre-content readiness combines closed schemas, deterministic context manifests and
omission reports, machine-computed M2 capability isolation, Provider identity and
rights evidence, revision-bound intensity contracts, causal/epistemic proof, and the
fixed first-region score `0.70 * risk_coverage + 0.30 * controllability`. Missing
evidence scores zero. B002 defines the contracts but produces no real region score and
no readiness result.

The external forensic evidence policy is content-addressed, append-only, secret-free,
and private-chain-of-thought-free. Redacted raw protocol evidence is retained through
M3-B004 independent ACCEPT plus 90 days; deletion then requires a separate Owner
disposition. Permanent hashes, receipts, normalized TEST evidence, and tombstones remain.

B003 remains blocked until this exact activation Candidate receives activation-specific Owner
full-hash approval, a second independent ACCEPT, a valid detached accepted envelope/tag, final
fast-forward integration, and WIP returns to zero, and until every Provider, host-resource, identity,
consumer-data-control, alias-resolution, and external-evidence-root prerequisite is
separately proven and authorized.
