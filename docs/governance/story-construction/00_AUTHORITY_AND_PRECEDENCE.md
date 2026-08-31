<!-- SECTION-ID: M3-SCG-AUTHORITY-PRECEDENCE -->
# Story Construction Governance — Authority and Precedence

```text
AUTHORITY_SCOPE = CONSTRUCTION_GOVERNANCE_ONLY
R2_CANON_PRECEDENCE = HIGHER
TRACKED_TARGET_STATE = ACTIVE
AUTHORITATIVE_ACTIVATION_EFFECTIVE = FALSE
ACTIVATION_APPROVAL_STATUS = PENDING_OWNER_ACTIVATION_HASH_APPROVAL
```

This layer governs how story content is proposed, ordered, validated, approved, superseded, and released. It does not define `WORLD_TRUTH`, `RULE_TRUTH`, `STORY_TRUTH`, `BOSS_TRUTH`, `ENDING_TRUTH`, or `FORMAL_REGION_CONTENT`. The 191 frozen R2 decisions and the existing Git authoring sources remain Canon authority.

```text
R2 Canon / existing Git authoring authority
  > Story Construction Governance
  > validated worker candidates
  > presentation and examples
```

The Canon Registry installed here is an index, governance layer, and validation layer over existing sources. It is not a second source of truth and cannot reverse-write derived data into `authoring/` or `governance/r2/`.

`CS-R2-SC-GOV-INSTALL-001` has consumed the exact, single-use implementation approval only for the already accepted implementation candidate `7305a9decacf4a6361692fe9359a1afa96801722`. The tracked activation candidate expresses `APPROVED + ACTIVE` and binds Q001–Q130 to this repository, but it cannot make itself authoritatively effective.

Authoritative activation requires the exact activation candidate commit/tree, a new activation-specific Owner full-hash approval, `PASS_FIXED_ACTIVATION_CANDIDATE_ACCEPTED`, a valid detached accepted activation envelope/annotated tag, and final fast-forward integration. Missing any proof keeps `AUTHORITATIVE_ACTIVATION_EFFECTIVE=false`; copying or cherry-picking tracked ACTIVE files never transfers that authority.
