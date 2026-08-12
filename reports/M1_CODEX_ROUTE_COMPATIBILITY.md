# M1 Codex Route Engineering Compatibility

For repository `zyc14588/rules-residue`, the command shown in R2 package v1.0.0 as:

```bash
go run ./cmd/projectctl codex check
```

is interpreted as a progressive-disclosure freshness capability probe, not as a requirement to introduce a Go project or copy platform tooling into this independent game repository.

The approved capability-equivalent implementation is:

```bash
just codex-check
```

with the Python 3.11+, standard-library-only backend `python3 tools/codex_route.py`. The gate binds and revalidates:

- current Git Commit;
- current Git Tree;
- routed document SHA-256;
- stable Section IDs and their uniqueness;
- route identity and mode;
- milestone and batch identity;
- the 55% soft and 70% hard context budgets;
- a canonical JSON binding digest; and
- stale commit, tree, or document rejection.

When those checks pass, this repository reports `CODEX_ROUTE_FRESH=PASS`. The absence of `cmd/projectctl` and `go.mod` is allowed and is not independently a failure. No Go toolchain or Go project should be added for literal command parity.

The digest algorithm is SHA-256 over the UTF-8 bytes produced by Python `json.dumps` with `sort_keys=True`, `separators=(",", ":")`, and `ensure_ascii=False`. Its input is the complete Reading Map except `generated_at` and `binding_digest`; this binds the required identity, Git, context-budget, document, Section, reason, and forbidden-read fields without introducing a timestamp-dependent digest.

This statement records an engineering compatibility fact only. It does not install R2 authority, alter any R2 frozen design, change M1 game semantics, or resolve the still-OPEN final world truth and return-home conditions.
