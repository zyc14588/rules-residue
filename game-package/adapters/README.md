# Platform v2 minimal probe adapter

This directory is the rules-side source boundary for the
`R2-INT-010-REM-001 minimal capability probe / NOT formal M2-B002 semantics`.
It preserves the existing `trpg.game-package.manifest/0.1-draft` package and
provides a deterministic adapter input for a separate standard platform v2
project.

`game-package/adapters/` and `game-package/extensions/` are intentionally
outside the legacy runtime whitelist. They do not enter the legacy
`package.lock.json` or legacy `.trpgpkg`; the generator copies only the named
source files into its separate v2 project boundary.

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
sibling `source-exact-lock.json` seed. It is not a Creator archive and is not
Host/Creator PASS evidence. A later independent cross-repository phase must
use the accepted platform Host and real accepted Creator binary to import,
edit, export, and re-import it.
