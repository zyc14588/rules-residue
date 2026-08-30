<!-- SECTION-ID: M3-SCG-CANON-REGISTRY -->
# Canon Registry and Normalization

```text
AUTHORITY_SCOPE = CONSTRUCTION_GOVERNANCE_ONLY
R2_CANON_PRECEDENCE = HIGHER
```

Human-authoritative representation remains YAML and existing Git authoring source. Derived canonical JSON is UTF-8, NFC-normalized, key-sorted, finite-number normalized, and versioned by Schema and canonicalization SemVer. Reference lists use their declared semantic order; otherwise they use lexical order.

The base Canon hash is calculated from an exact, lexically ordered index of existing R2 and authoring sources. This installation changes no Canon fact, so `proposed_canon_hash == base_canon_hash`. The governance Merkle root covers Q001–Q130 and the source-intake, authority-overlay, registry, traceability, and supersession records.

`canonical-manifest.json` is one-way: it records inputs and their hashes but never its own hash, a receipt hash, or an approval hash. The detached pending receipt hashes only its payload. Candidate commit/tree remain null in tracked artifacts and are bound later by Owner approval and independent ACCEPT.
