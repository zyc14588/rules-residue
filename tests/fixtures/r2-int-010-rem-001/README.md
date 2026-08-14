# R2-INT-010-REM-001 source-only test/integration fixture

This directory is the repository source boundary for the
`R2-INT-010-REM-001 minimal capability probe / NOT formal M2-B002 semantics`.
It is outside the frozen `game-package/` runtime and supplies deterministic
inputs for a separate temporary standard platform v2 project.

This fixture is **NOT a Creator artifact**, **NOT Host evidence**, and **NOT
Creator/Host PASS evidence**. It does not modify the legacy
`trpg.game-package.manifest/0.1-draft` package, its manifest, or its lock. The
builder reads only the legacy package ID and version, then copies these named
fixture bytes into the temporary v2 project at legal local package paths under
`adapters/` and `extensions/<derived-namespace>/`.

The adapter derives its extension namespace from the stable package ID by
normalizing a platform `/` separator to `.`, retaining canonical dotted IDs,
and appending the fixed `probe` segment. For this package the result is
`org.trpgplatform.rules-residue.probe`. The generic platform package ID is
derived by splitting the final segment into
`org.trpgplatform/rules-residue`.

The declared extension contains only a bounded counter, an enabled flag, and
scope markers fixed to `formal_B002=false` and `formal_B009=false`. It does not
define rule equipment, short/long rule algorithms, Lua, runtime behavior, or
any formal R2 semantics.

Build the deterministic source fixture with:

```bash
python3 tools/build_platform_v2_probe.py --output-root /tmp/rules-residue-v2-probe
```

The output contains `project/`, which has a standard v2 `package.toml`, and a
sibling `source-exact-lock.json` seed. A later independent cross-repository
phase must use the accepted platform Host and real accepted Creator binary to
import, edit, export, and re-import it.
