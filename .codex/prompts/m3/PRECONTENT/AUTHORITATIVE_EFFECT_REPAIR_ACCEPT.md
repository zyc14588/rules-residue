<!-- SECTION-ID: M3-CODEX-PRECONTENT-AUTHORITATIVE-EFFECT-REPAIR-ACCEPT -->
# M3-B002 authoritative-effect repair independent ACCEPT

This role is read-only and starts only at the exact one-commit repair Candidate whose direct
parent is `d80aae8d1dfede85d91ff0367f4c6a18d62bb2a7`, after the Owner supplies a new
candidate-specific full-hash approval using the additive v2 approval contract. The prior d80
approval and ACCEPT are historical evidence only and cannot authorize or be replayed for the
repair Candidate.

Generate a fresh candidate-bound ACCEPT Reading Map in a separate clean worktree. Independently
recompute the exact 13-path diff, R2-to-R3 `70/6/5/81` transition, `20/5/3/28` schema sets,
non-self-referential R3 receipt, fixed Canon/runtime/Q001-Q130/M2/Provider evidence, and zero-call
state. Run the complete negative proof matrix and the real CLI positive path in an isolated Git
repository with an annotated tag and bare remote. The positive fixture must never inspect or push
the production origin.

The only successful result is
`PASS_FIXED_M3_B002_AUTHORITATIVE_EFFECT_REPAIR_CANDIDATE_ACCEPTED`. ACCEPT consumes the new
approval as exactly one external event without modifying the issued `consumed=false` JSON. It must
not modify the Candidate, create a production envelope or proof tag, integrate, push, call a
Provider, execute Story M0, release content, or start M3-B003.
