<!-- SECTION-ID: M3-SCG-CHANGESET-LIFECYCLE -->
# Change Set and Lifecycle

```text
AUTHORITY_SCOPE = CONSTRUCTION_GOVERNANCE_ONLY
R2_CANON_PRECEDENCE = HIGHER
```

Primary lifecycle stages are `DRAFT → CANDIDATE → APPROVED → RELEASED`. Orthogonal disposition is `ACTIVE | QUARANTINED | REJECTED | SUPERSEDED`; validation and approval remain separate fields. A split, retargeted, or content-changing candidate receives a new Change Set and new hashes.

Every Change Set binds its base commit/tree/canon hash, source package, records, dependencies, authority classes, T1/T2/T3 and P0/P1/C1/C2 impacts, migration, tests, proposed canon hash, Merkle root, receipt payload hash, and approval status. `candidate_binding.strategy` is always `EXACT_HEAD_AT_VALIDATION`; a tracked candidate must not predict or self-reference its own future commit or tree.

Owner approval binds the exact Change Set, base commit/tree/canon hash, candidate commit/tree, proposed canon hash, Merkle root, and receipt payload hash. It is candidate-specific, single-use, non-transferable, and revocable before integration. Any identity change invalidates it. Released history is never rewritten; later changes use a new Change Set.
