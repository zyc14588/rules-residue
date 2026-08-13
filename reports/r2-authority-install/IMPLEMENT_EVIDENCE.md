<!-- SECTION-ID: R2-INSTALL-IMPLEMENT-EVIDENCE -->
# R2 Authority Install — IMPLEMENT Evidence

## Identity and frozen inputs

- role: `IMPLEMENT`
- lifecycle state at handoff: `VERIFYING`; this report is Builder self-check evidence, not independent `ACCEPT`
- worktree: `/tmp/rules-residue-r2-implement`
- branch: `codex/r2-authority-install-implement`
- PLAN commit: `e27b92143f6e657b31d791c8d305e79ec6b72d7e`
- PLAN tree: `9e3bbd807da4f1991469b76141379964a4c71af8`
- pinned M1 source: `e8e536fe5c96c389736ffcf8d4855fa146a2b9c2`
- package: `/home/zyc14588/RULE_RESIDUAL_R2_AUTHORITY_AND_PROGRESSIVE_DELIVERY_v1.0.0`

The final ephemeral IMPLEMENT Reading Map uses route
`R2-AUTHORITY-INSTALL-IMPLEMENT`, mode `IMPLEMENT`, milestone `M1`, and batch
`M1-B002`. It binds the PLAN commit/tree above, all selected document hashes and
Section IDs, and canonical digest
`756c77d425af84f50052fa655eab460e22d56887cfee6ccf690f51250d9bcfae`.
Its planned context is `34267 / 196608 = 17.429097493489584%`; the enforced
soft/hard limits are `55%` and `70%`. The checked ephemeral map is
`/tmp/r2-authority-install-implement-final2-reading-map.json`; the reproducible
request is `.codex/routes/r2-authority-install-implement-request.json`.

## Route correction finding

`R2-IMP-F001`: an early Builder probe used batch `M1-B003`, contrary to the
frozen machine plan's `M1-B002`. Every map produced by that probe is
`INVALID / DISCARDED` and is excluded from installation evidence. No conclusion
from those maps was retained. The Builder regenerated two correct `M1-B002`
maps, read every routed Section again, and rechecked every working-tree change
against the frozen INSTALL_PLAN, TaskEnvelope, and 124-row disposition matrix.
That recheck found two exploratory edits outside the allowlist in
`docs/authority/01_PLATFORM_BOUNDARY.md` and
`docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md`; both were reverted before
validation. The final correct map identified above then passed the repository
freshness checker.

## Package integrity and disposition

- `PACKAGE_MANIFEST.yaml` SHA-256:
  `a5adb9fad5439926e0c8d46f23f3e3e107812bdd9ce13097acea04b8cc0a7ba1`
- `SHA256SUMS` SHA-256:
  `2d65a2ea9fefffc4f8e785fe2e55a0bdc83b7a54559afbb51162daedc0ab8e72`
- `sha256sum -c SHA256SUMS`: exit `0`, all listed files `OK`, both before and
  after installation
- disposition rows: `124`
- `INSTALL_CANONICAL`: `108`; `98/108` installed targets are byte-for-byte equal
  to their package source and the 10 explicitly recorded Markdown targets use
  whitespace-only repository normalization
- `MERGE_INTO_EXISTING`: `9`
- `REFERENCE_ONLY`: `0`
- `PACKAGE_PROVENANCE_ONLY`: `5`
- `DUPLICATE_OF_CANONICAL`: `2`
- `NOT_APPLICABLE_FIRST_RELEASE`: `0`
- `UNCLASSIFIED`: `0`

Two of the nine Markdown merges needed line-end formatting normalization so
`git diff --check` would remain a hard gate:

1. Package
   `01_REPO_OVERLAY/authoring/story/00_STORY_BIBLE.md` to installed
   `authoring/story/00_STORY_BIBLE.md`: the package line
   ``可见性：`AUTHOR / GM`<U+0020><U+0020>`` became the same line with zero
   trailing U+0020 characters.
2. Package
   `01_REPO_OVERLAY/authoring/story/01_TRUTH_BIBLE.md` to installed
   `authoring/story/01_TRUTH_BIBLE.md`: the package line
   ``> `AUTHOR / GM / MECHANICAL ONLY`<U+0020><U+0020>`` became the same line
   with zero trailing U+0020 characters.

These are the only differences inside those two canonical R2 sections. They
change no normative word, state, identifier, visibility value, truth, or
mechanical meaning. The merge validator canonicalizes **only** ASCII U+0020
characters at each line end, then requires the complete normalized package
document to occur contiguously in the target. It does not skip or partially
match content. The targeted negative test separately deletes a canonical line
and changes a canonical word; both variants are rejected. Raw byte equality is
mandatory for `INSTALL_CANONICAL` except the 10 explicit paths below.

### Explicit INSTALL_CANONICAL whitespace adapter

The frozen disposition remains `INSTALL_CANONICAL`. PLAN scope review found it
consistent to apply an explicit repository compatibility adapter to 10 paths so
the mandatory `git diff --check` gate can pass. The adapter removes only package
EOL U+0020 bytes or one package-provided final blank line. It does not change
words, IDs, headings, ordering, links, or the final newline. Machine-readable
evidence is in
`governance/evidence/r2-authority-install/canonical-normalizations.yaml`.

| Package source → installed target | Diff type | Source SHA-256 | Target SHA-256 |
|---|---|---|---|
| `03_CODEX_PROGRESSIVE_DISCLOSURE/M2-VERTICAL-SLICE/ACCEPT.md` → `.codex/prompts/r2/M2-VERTICAL-SLICE/ACCEPT.md` | drop one final blank line | `af44e25a13e2e549a87d4f875853342f1796cd3ed635961f9ec1f5ec117852a4` | `f0431da7bbfe57cdd513df15f8362c9fb36a6b36d435e5b4e36baa3568e195d9` |
| `03_CODEX_PROGRESSIVE_DISCLOSURE/M2-VERTICAL-SLICE/IMPLEMENT.md` → `.codex/prompts/r2/M2-VERTICAL-SLICE/IMPLEMENT.md` | drop one final blank line | `b4ec0633ff6408e675175d0bb7109b5cf831c277d16de50d8ec7debcb6e58167` | `a21deb9b0b8a08f85f53ad0d783cc2014416a37b26a228137ece17d70d751a98` |
| `03_CODEX_PROGRESSIVE_DISCLOSURE/M2-VERTICAL-SLICE/PLAN.md` → `.codex/prompts/r2/M2-VERTICAL-SLICE/PLAN.md` | drop one final blank line | `0e7c9291a39a046a3647dc468f8071aded1886069ea56bae91e133932c3b1c59` | `fef9dafcdfb755f36aadc2619ab7684b74155a63e0a0191ce6cb5010c183a8a5` |
| `03_CODEX_PROGRESSIVE_DISCLOSURE/M2-VERTICAL-SLICE/REPAIR.md` → `.codex/prompts/r2/M2-VERTICAL-SLICE/REPAIR.md` | drop one final blank line | `96d4ecfc5f5de9b1aee6254d1fb02b03970410f948af46a83aca99d42d4a4485` | `713f515e54a874e231956c8a5260e1c942c1e2a9fa19a4d9419037bcfb388db3` |
| `03_CODEX_PROGRESSIVE_DISCLOSURE/R2-AUTHORITY-INSTALL/ACCEPT.md` → `.codex/prompts/r2/R2-AUTHORITY-INSTALL/ACCEPT.md` | drop one final blank line | `4255c6dab164d3455a0c96240fb4f1bd51b9a8c4289616cd09d62dcc5dd9fa6d` | `a9d5ddfbdefcc2df928c2fe1e8d78e0fd511ce040ecbf73283da341323ddc227` |
| `03_CODEX_PROGRESSIVE_DISCLOSURE/R2-AUTHORITY-INSTALL/IMPLEMENT.md` → `.codex/prompts/r2/R2-AUTHORITY-INSTALL/IMPLEMENT.md` | drop one final blank line | `b637b4c6dc86e50f91d2f3368faaf2f2997fb3ef5eb6c63d8712a8987b16a78f` | `69f0a0554d05906a8d37477846895605d3085a7b9ea646278805b68aa3a802e0` |
| `03_CODEX_PROGRESSIVE_DISCLOSURE/R2-AUTHORITY-INSTALL/PLAN.md` → `.codex/prompts/r2/R2-AUTHORITY-INSTALL/PLAN.md` | drop one final blank line | `4a422f911705f3847c393278d14bf0a7862ad911b118114e5bb58fb409406ddd` | `f8f88bc610894b7535cd090b6464f9b2dda71e6f472f504816b35a1fb11f8b93` |
| `03_CODEX_PROGRESSIVE_DISCLOSURE/R2-AUTHORITY-INSTALL/REPAIR.md` → `.codex/prompts/r2/R2-AUTHORITY-INSTALL/REPAIR.md` | drop one final blank line | `652a5e325c12d5c3f9f826705bcc854bcddfa7cc564cf2705f57656a3a3fbb9e` | `472c418daddedcdeda8d338e0e30d99057a91fae7bf9797e370b3db50a64c6af` |
| `01_REPO_OVERLAY/docs/authority/r2/00_R2_AUTHORITY_ENTRY.md` → `docs/authority/r2/00_R2_AUTHORITY_ENTRY.md` | strip 6 EOL U+0020 bytes on source lines 4–6 | `761f766a891ff62fafe4808d7592ff565089876a27a00c6f7e455c7e68d254df` | `f5e2a033d09724e616c03019e22b02e62b64aa152f2f276c25a3cd334db32db2` |
| `01_REPO_OVERLAY/docs/operations/R2_PROGRESSIVE_DISCLOSURE_PROTOCOL.md` → `docs/operations/r2/R2_PROGRESSIVE_DISCLOSURE_PROTOCOL.md` | strip 2 EOL U+0020 bytes on source line 41 | `d9cd2c568fb766c2894c7a6ce97710cae7bea291908f576ad6b5ca89c89bdda3` | `5c15dfde8ee11feb0f70e9f51b86f44bd9f359f6b04065e6bba0b35b8e92c258` |

The validator applies those transformations only when both target and package
source equal the explicit frozen mapping, checks the exact number of removed
ASCII bytes, compares the entire resulting byte string, and verifies every
recorded source/target hash. The remaining 98 paths still require raw byte
equality. A temporary-copy negative test deletes a normative line and changes a
normative phrase in a normalized prompt; both are rejected as normalized byte
mismatches.

## Installed scope

The installation includes the R2 authority documents, 191-decision machine
registry, terminology, authority map, traceability, deferred and safety
registries, R2 schemas, authoring extensions, M1-to-R2 supersession history,
M2 planning inputs, Codex PLAN/IMPLEMENT/ACCEPT/REPAIR prompt sets for this
install and M2, OpenCode/Grok/portable-agent handoffs and adapters, independent
acceptance packet, operations/usage material, Task Packet examples, package
provenance, and `R2-INT-001..012` compatibility classifications.

The installed M2 contract records `implementation_started: false`. No M2 work
was executed. Source-to-working-tree checks show no change under
`game-package/**` or `dist/**`, no Lua/runtime change, and no change to package
lock or runtime module registry. Authoring and Truth Bible sources remain
outside the package manifest.

## Static validator coverage

`tools/validate_r2_install.py`, invoked directly and by `just r2-validate` and
the existing project validator, checks package integrity and disposition;
191 exact decisions and group counts; ID, option, index, traceability, deferred,
terminology, YAML/JSON/Schema, Section-ID and authority-path integrity; M1
supersession and single active R2 truth; player/GM/mechanical/audit boundaries;
repeat content-safety stages and minor-abuse red lines; route identity,
freshness/budget probes and prompt discovery; other-agent handoffs; M2-input
presence with implementation false; acceptance documents; Task Packet examples;
conflict classifications; and pinned-source runtime/package boundaries.

Negative probes execute only in temporary copies. They reject a missing
decision, duplicate decision ID, duplicate Section ID, broken JSON Schema,
missing traceability row, Truth Bible package leak, missing safety stage, and
both deletion and word mutation within a normalized merge section. The existing
Codex route tests independently reject stale commit/tree/document bindings,
missing or duplicate Section IDs, bad route/mode/milestone/batch identity,
oversized context, bulk reads, and external-root escape.

## Findings and remediations

- `R2-IMP-F001`: wrong early batch probe; maps discarded, correct B002 Sections
  re-read, full change set rechecked, exploratory out-of-scope edits reverted.
- `R2-IMP-F002`: initial R2 validator expectations did not represent valid
  package facts (`FROZEN_WITH_DEFERRED_SPEC`, route schema mapping, equivalent
  safety phrase, merged-session Section discovery, and return-envelope naming).
  Each was corrected without changing frozen R2 content or weakening a gate;
  the final validator passes and has negative probes.
- `R2-IMP-F003`: `just acceptance` was once launched concurrently with a direct
  `tools/run_acceptance.py` invocation. Both writers targeted the same ignored
  `dist/*.trpgpkg`, and one exited nonzero with `FileNotFoundError`. This was a
  Builder orchestration race, not a repository defect. The commands were then
  run sequentially and passed. Final verification also runs them sequentially.
- `R2-IMP-F004`: `git diff --check` found the two package Markdown trailing-space
  lines documented above. Only their terminal U+0020 bytes were removed; the
  validator now performs the narrowly scoped complete-document normalization,
  and deletion/word-change probes remain rejected.
- `R2-IMP-F005`: the staged-diff variant of `git diff --check` exposed package
  whitespace in 10 newly added `INSTALL_CANONICAL` files: eight single final
  blank lines and four EOL-space lines across two documents. Read-only PLAN
  review returned `PLAN_CONSISTENT`. The explicit 10-path adapter, hashes, and
  fail-closed probes above are the complete remediation; disposition and
  normative text remain unchanged.

## Executed command evidence

Commands below were actually executed in this IMPLEMENT worktree unless another
working directory is shown. The final verification block is updated only after
its sequential run completes.

| Command | Exit | Result |
|---|---:|---|
| `python3 tools/codex_route.py check --map /tmp/r2-authority-install-implement-final2-reading-map.json --route-id R2-AUTHORITY-INSTALL-IMPLEMENT --mode IMPLEMENT --milestone M1 --batch-id M1-B002 --allow-root <R2_PACKAGE>` | 0 | `CHECK: PASS`; `CODEX_ROUTE_FRESH=PASS` |
| earlier check invocation using unsupported `--request/--reading-map` flags | 2 | CLI usage error; immediately rerun with the supported flags above |
| `(cd <R2_PACKAGE> && sha256sum -c SHA256SUMS)` | 0 | every listed file `OK` |
| `just r2-validate` after merge-normalization probe | 0 | all R2 validator groups PASS |
| `python3 -m unittest tests.test_r2_installation.R2InstallationNegativeProbeTests.test_merged_canonical_section_deletion_and_word_change_are_rejected -v` | 0 | delete and word-change subprobes rejected |
| first normalized-canonical targeted test using two non-existent probe phrases | 1 | test-fixture error; corrected to phrases present in the frozen prompt |
| `python3 -m unittest tests.test_r2_installation.R2InstallationNegativeProbeTests.test_normalized_install_canonical_deletion_and_word_change_are_rejected -v` | 0 | normalized canonical delete and word-change subprobes rejected |
| `git diff --name-status <M1_SOURCE> -- game-package dist` | 0 | empty output |
| `git diff --name-status <PLAN_COMMIT> -- .codex/state <frozen plan/disposition/TaskEnvelope>` | 0 | empty output |
| first `git diff --check` before line-end normalization | 2 | reported only the two documented trailing-space lines |
| `just r2-validate` immediately after removing those spaces but before validator normalization | 1 | rejected the two merge sections; led to narrowly scoped normalization plus negative probes |
| `just acceptance` launched concurrently with direct acceptance | nonzero | invalidated orchestration-race run; `R2-IMP-F003` |
| sequential rerun `just acceptance` | 0 | PASS |
| sequential rerun `python3 tools/run_acceptance.py` | 0 | PASS |

## Final Builder verification

The first pre-candidate verification was run sequentially before the staged
whitespace finding `R2-IMP-F005`:

| Command | Exit | Evidence summary |
|---|---:|---|
| `just validate` | 0 | all existing M1 groups plus R2 registry PASS |
| `just test` | 0 | `Ran 97 tests`; `OK` |
| `just acceptance` | 0 | 97 tests, validator and deterministic package build PASS; SHA-256 `29ea1e0278e37d183d4c0ff396437088b4873c58c5e9a9c857093f6c552a6314` |
| `just codex-check` | 0 | baseline route fresh plus 26 negative route tests PASS |
| `just r2-validate` | 0 | every R2 static-validation group PASS |
| `python3 tools/run_acceptance.py` | 0 | 97 tests, validator and deterministic package build PASS; same package SHA-256 |
| `just clean` | 0 | removed ignored temporary `.trpgpkg`; no build artifact retained |

After `R2-IMP-F005`, the complete final suite was rerun sequentially:

| Command | Exit | Final post-normalization evidence |
|---|---:|---|
| `just validate` | 0 | all M1 and R2 validation groups PASS |
| `just test` | 0 | `Ran 98 tests`; `OK`, including both normalized-canonical mutation subprobes |
| `just acceptance` | 0 | 98 tests, validator and deterministic package build PASS; SHA-256 `29ea1e0278e37d183d4c0ff396437088b4873c58c5e9a9c857093f6c552a6314` |
| `just codex-check` | 0 | `CODEX_ROUTE_FRESH=PASS`; 26 negative route tests PASS |
| `just r2-validate` | 0 | package/disposition, 191 decisions, schema/Section, supersession/safety, routes/handoffs/M2 inputs, and runtime-boundary groups PASS |
| `python3 tools/run_acceptance.py` | 0 | 98 tests, validator and deterministic package build PASS; same package SHA-256 |
| `just clean` | 0 | temporary ignored package removed |
| `(cd <R2_PACKAGE> && sha256sum -c SHA256SUMS)` | 0 | all 123 listed payload/wrapper entries `OK` after implementation |
| final B002 Reading Map generate/check | 0 | digest `756c77d425af84f50052fa655eab460e22d56887cfee6ccf690f51250d9bcfae`; route fresh; budget OK |

The remaining pre-commit staged range, allowlist, status, and `git diff --check`
audits are recorded by the Builder handoff together with the fixed candidate
commit and tree.
