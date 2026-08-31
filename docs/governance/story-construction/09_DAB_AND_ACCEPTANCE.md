<!-- SECTION-ID: M3-SCG-DAB-ACCEPTANCE -->
# DAB and Acceptance

```text
AUTHORITY_SCOPE = CONSTRUCTION_GOVERNANCE_ONLY
R2_CANON_PRECEDENCE = HIGHER
```

DAB means Decision & Audit Bundle. Tiers are `MINIMAL`, `STANDARD`, and `FORENSIC`. FORENSIC is mandatory for T1, T2, C1, failure/dispute investigation, Release Candidate, and release evidence.

A DAB carries decisions, approvals, generation identity and hashes, validation, targeted repairs, permitted waivers, and release evidence. It is not Canon and must never request or record a model's private chain-of-thought.

Independent ACCEPT runs read-only at an exact candidate commit/tree and recomputes the Canon hashes, governance Merkle root, receipt payload hash, schemas, routes, supersession, M2 preservation, package exclusion, and deterministic builds. Builder or worker conclusions are not evidence of final PASS.

The implementation candidate has the fixed result `PASS_FIXED_CANDIDATE_ACCEPTED`; its Owner approval is recorded as single-use, non-transferable, and consumed by that exact ACCEPT task. This consumption does not approve the activation candidate.

Activation requires a second read-only ACCEPT at the exact activation commit/tree after activation-specific Owner full-hash approval. A detached outer envelope binds that approval, the second ACCEPT, exact annotated-tag target, final inner receipt hashes, clean verifier, and one-commit fast-forward lineage. Until the accepted envelope/tag and final integration exist, tracked `ACTIVE` remains non-authoritative.
