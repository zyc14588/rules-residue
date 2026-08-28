# R2-INT-010 post-platform source-only adapter candidate

This directory is the complete source boundary for a new minimal compatibility
adapter candidate constructed after independent platform capability acceptance.
It is intentionally outside `game-package/` and does not enter the legacy
`.trpgpkg`, `package.lock.json`, Lua runtime, equipment runtime, or rule engine.

The candidate is a generic platform-v2 library project containing one required
namespaced JSON extension. Its payload is only a bounded counter plus non-formal
scope markers. It does not encode long/short equipment semantics, does not grant
first-party privileges, and contains no official-game identity exception.

Governance status remains:

```text
platform capability = ACCEPTED
post-platform rules adapter = IMPLEMENTED / NOT_ACCEPTED
independent adapter acceptance = NOT_RUN
cross-repository acceptance = NOT_RUN
R2-INT-010 = FAIL
M2-B002 = NOT_STARTED
```

Build a deterministic source project and exact lock with:

```bash
python3 tests/m2/probes/r2_int_010_post_platform/builder.py \
  --output-root /tmp/r2-int-010-post-platform-source
```

Validate the checked-in acceptance antecedent and provenance disposition with:

```bash
python3 tests/m2/probes/r2_int_010_post_platform/validator.py --validate
```

The builder reads only the declared JSON inputs in this directory. The separate
validator binds those source bytes to the post-platform PASS record and rejects
all three pre-platform provisional commits as acceptance or execution evidence.
