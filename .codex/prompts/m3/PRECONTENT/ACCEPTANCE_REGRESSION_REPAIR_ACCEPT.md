<!-- SECTION-ID: M3-CODEX-PRECONTENT-ACCEPTANCE-REGRESSION-REPAIR-ACCEPT -->
# M3-B003 P0-B R4 acceptance-regression repair independent ACCEPT

This role is read-only. It starts only at the exact one-commit R4 Candidate whose direct parent is
`2d7f78f5b24623729cb64a798b59d6f469e6de2b`, after the Owner supplies a candidate-specific
full-hash approval conforming to the R4 Owner-approval schema. The accepted B002 approval,
independent ACCEPT, closeout envelope, and production proof tag remain immutable predecessor
evidence; none of them authorizes the successor Candidate.

Generate a fresh Candidate-bound ACCEPT Reading Map in a separate clean worktree. Independently
recompute the exact 15-path diff, the R3-to-R4 `75/6/7/88` transition, the predecessor/R4/combined
`28/4/32` schema sets, the non-self-referential R4 receipt, and every fixed Canon, Q001-Q130, M2,
runtime, and Provider-zero-call preservation value. Revalidate the original B002 proof and the
successor proof independently. Ancestry by itself is never acceptance.

Run the synthetic-tag regression matrix only in isolated temporary repositories with absolute local
bare remotes. The logical contracts remain bound to the production B002 and R4 tag names; test-only
physical refs must be exact digest-derived refs under
`refs/tags/test-fixtures/scg-precontent-authoritative-effect/`. Never delete, move, retarget, hide, or
stage out the installed production B002 tag.

The only successful result is
`PASS_FIXED_M3_B003_P0_B_R4_ACCEPTANCE_REGRESSION_REPAIR_CANDIDATE_ACCEPTED`. ACCEPT consumes the
new approval as one external event without modifying its issued `consumed=false` bytes. It must not
modify the Candidate, create a production closeout envelope or tag, integrate, push, call a Provider,
execute Story M0, release content, or begin R5.
