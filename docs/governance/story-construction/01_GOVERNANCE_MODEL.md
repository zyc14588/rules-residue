<!-- SECTION-ID: M3-SCG-GOVERNANCE-MODEL -->
# Story Construction Governance Model

```text
AUTHORITY_SCOPE = CONSTRUCTION_GOVERNANCE_ONLY
R2_CANON_PRECEDENCE = HIGHER
```

Canon tiers are `T1` Root Canon, `T2` Structural Canon, and `T3` Instance Canon. T1 and T2 require explicit Owner approval. T3 may be instantiated only inside an approved Canon Envelope. Content impact classes are `P0` pure presentation, `P1` Canon implementation, `C1` Canonical Conveyance/Reveal, and `C2` Canon change. C1 requires Owner approval; C2 blocks and becomes a new Change Set.

The role plane is deliberately separate from the Owner approval plane:

- Codex: Planner, Framework Builder, final assembly, and Verifier.
- DeepSeek Harness (`owner=deepseek_harness`, `task_type=literary`): official literary text worker, candidate output only.
- Grok: visual production worker, consuming only a validated Visual Order Package.
- OpenCode: Lua/game scripting only; its existing default-deny gates stay active.
- Owner: T1, T2, C1 Reveal, and exact candidate-hash approval.

Workers cannot approve themselves, modify authority, or directly persist authoritative state. AI output remains a structured candidate until Codex validation and every required Owner approval succeed.
