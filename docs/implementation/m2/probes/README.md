<!-- SECTION-ID: M2-B001-PROBE-EVIDENCE -->
# M2-B001 capability-probe evidence

This directory defines the evidence contract for `R2-INT-001` through
`R2-INT-012`. It is fact-finding infrastructure, not a Game Package, runtime,
platform implementation, or approval of a platform change.

The authoritative result is `reports/m2/probes/probe-results.json`. A probe is
`PASS` only when every required target has actually passed. A successful local
reference check may establish adapter feasibility while the overall probe stays
`BLOCKED_EXTERNAL`; it must never promote an unavailable Host or Creator Tool
target to `PASS`.

## Candidate and source binding

Every result carries the frozen source commit/tree, route digest, and the
`EXACT_HEAD_AT_VALIDATION` strategy. The validator resolves that strategy only
when invoked with `--candidate <exact-commit> --candidate-tree <exact-tree>` in
a clean checkout. It verifies ancestry, exact HEAD/tree identity, tracked
evidence paths, and all hashes in the evidence manifest. This avoids a
self-referential commit hash inside the commit while still making stale or
tampered evidence fail closed.

External results additionally bind:

- the exact Task Packet SHA-256;
- the game source and exact candidate commit/tree;
- the external repository commit/tree and clean tracked state;
- every command, exit code, and output digest.

The two portable packets remain `PLANNED`. Their existence is not external
approval and their expected result is not evidence.

## Local checks

Run all B001 contract, fixture, safety, and negative checks with:

```bash
python3 tests/m2/probes/validate_m2_b001.py --all
python3 tests/m2/probes/test_m2_b001_probes.py -v
```

After committing the candidate, add exact candidate arguments to the first
command. Independent ACCEPT must run the same command in a new read-only
worktree and must not reuse the IMPLEMENT conclusion.
