<!-- SECTION-ID: M2-ROUTE-B001 -->
# M2-B001 Reading Map Request Blueprint

Authority: `R2-INTEGRATION-CONFLICTS`, `R2-AUTH-M1-INTEGRATION`, `R2-M2-VALIDATION-MATRIX`, `R2-M2-STOP-CONDITIONS`. Dynamic inputs: frozen B001 envelope, exact probe schemas, and only the target-specific Host/Creator contract. Route IDs end in `-PLAN`, `-IMPLEMENT`, `-ACCEPT`, or `-REPAIR`; every request binds its actual role in `mode`, plus `milestone=M2` and `batch_id=M2-B001`.

<!-- SECTION-ID: M2-ROUTE-B002 -->
# M2-B002 Reading Map Request Blueprint

Authority: `R2-AUTH-RULE-LOOP`, `R2-AUTH-CHARACTER-EQUIPMENT`, `R2-AUTH-CONTINENT-REGIONS`, `R2-AUTH-ENDINGS`, `R2-AUTH-CAMPAIGN-HOSTING`. Dynamic inputs: accepted B001 evidence, frozen B002 envelope, and exact schema paths.

<!-- SECTION-ID: M2-ROUTE-B003 -->
# M2-B003 Reading Map Request Blueprint

Authority: `R2-AUTH-WORLD-TRUTH`, `R2-AUTH-RULE-LOOP`, `R2-AUTH-CAMPAIGN-HOSTING`, `R2-AUTH-SAFETY`. Dynamic inputs: accepted B002 schemas, frozen B003 envelope, and exact fixture IDs; Truth Bible is never routed wholesale.

<!-- SECTION-ID: M2-ROUTE-B004 -->
# M2-B004 Reading Map Request Blueprint

Authority: `R2-AUTH-RULE-LOOP`, `R2-AUTH-CAMPAIGN-HOSTING`, `R2-M2-STOP-CONDITIONS`. IMPLEMENT adds only the frozen OpenCode packet, accepted schemas, and B003 fixtures. ACCEPT adds the exact candidate diff/tests, not the worker summary.

<!-- SECTION-ID: M2-ROUTE-B005 -->
# M2-B005 Reading Map Request Blueprint

Authority: `R2-AUTH-RULE-LOOP`, `R2-AUTH-CONTINENT-REGIONS`, `R2-AUTH-ENDINGS`, `R2-AUTH-DEFERRED`. Dynamic inputs: frozen packet, accepted transition fixtures, and bound external persistence evidence.

<!-- SECTION-ID: M2-ROUTE-B006 -->
# M2-B006 Reading Map Request Blueprint

Authority: `R2-AUTH-CHARACTER-EQUIPMENT`, `R2-AUTH-RULE-LOOP`, `R2-AUTH-CAMPAIGN-HOSTING`, `R2-AUTH-DEFERRED`. Dynamic inputs: frozen packet, accepted loop API, and bound seat/deceased-view evidence.

<!-- SECTION-ID: M2-ROUTE-B007 -->
# M2-B007 Reading Map Request Blueprint

Authority: `R2-AUTH-VISION`, `R2-AUTH-WORLD-TRUTH`, `R2-AUTH-CONTINENT-REGIONS`, `R2-AUTH-SAFETY`, `R2-M2-INPUT`. Dynamic inputs are limited to M2 test-region schemas and source objects; full story/truth sources are forbidden.

<!-- SECTION-ID: M2-ROUTE-B008 -->
# M2-B008 Reading Map Request Blueprint

Authority: `R2-AUTH-RULE-LOOP`, `R2-AUTH-CONTINENT-REGIONS`, `R2-AUTH-CAMPAIGN-HOSTING`, `R2-AUTH-SAFETY`. Dynamic inputs: frozen OpenCode packet and accepted region objects/fixtures.

<!-- SECTION-ID: M2-ROUTE-B009 -->
# M2-B009 Reading Map Request Blueprint

Authority: `R2-AUTH-RULE-LOOP`, `R2-AUTH-CHARACTER-EQUIPMENT`, `R2-AUTH-WORLD-TRUTH`, `R2-AUTH-PRESENTATION`. Dynamic inputs: frozen packet, equipment/key-item fixtures, and the exact Creator extension contract/evidence.

<!-- SECTION-ID: M2-ROUTE-B010 -->
# M2-B010 Reading Map Request Blueprint

Authority: `R2-AUTH-VISION`, `R2-AUTH-WORLD-TRUTH`, `R2-AUTH-CHARACTER-EQUIPMENT`, `R2-AUTH-CAMPAIGN-HOSTING`, `R2-AUTH-SAFETY`. Dynamic inputs: frozen envelope, action/projection schemas, and recorded model fixtures only; no live model is authoritative.

<!-- SECTION-ID: M2-ROUTE-B011 -->
# M2-B011 Reading Map Request Blueprint

Authority: `R2-AUTH-WORLD-TRUTH`, `R2-AUTH-ENDINGS`, `R2-AUTH-CAMPAIGN-HOSTING`, `R2-AUTH-DEFERRED`. Dynamic inputs: frozen envelope, accepted Boss/ending schemas, and M2 proxy fixtures only.

<!-- SECTION-ID: M2-ROUTE-B012 -->
# M2-B012 Reading Map Request Blueprint

Authority: `R2-AUTH-WORLD-TRUTH`, `R2-AUTH-ENDINGS`, `R2-AUTH-CAMPAIGN-HOSTING`, `R2-AUTH-SAFETY`. Dynamic inputs: frozen OpenCode packet, accepted B011 fixtures, and bound termination-event evidence.

<!-- SECTION-ID: M2-ROUTE-B013 -->
# M2-B013 Reading Map Request Blueprint

Authority: `R2-AUTH-PRESENTATION`, `R2-AUTH-CONTINENT-REGIONS`, `R2-AUTH-SAFETY`. Grok receives only the public technical brief, sizes/formats, and accessibility/safety constraints; no definitions, seed, or hidden truth.

<!-- SECTION-ID: M2-ROUTE-B014 -->
# M2-B014 Reading Map Request Blueprint

Authority: `R2-AUTH-PRESENTATION`, `R2-AUTH-SAFETY`, `R2-M2-INPUT`. Grok receives only selected public final-slice briefs and accepted visual mechanics; formal character/Boss identities are forbidden.

<!-- SECTION-ID: M2-ROUTE-B015 -->
# M2-B015 Reading Map Request Blueprint

Authority: `R2-AUTH-M2-CONTRACT`, `R2-AUTH-VALIDATION`, `R2-ACC-M2-STRICT`, `R2-M2-VALIDATION-MATRIX`, `R2-M2-STOP-CONDITIONS`. Dynamic inputs: accepted batch evidence, exact integration envelope, external results, manifest, and lock.

<!-- SECTION-ID: M2-ROUTE-B016 -->
# M2-B016 Reading Map Request Blueprint

Authority: `R2-ACC-M2-STRICT`, `R2-AUTH-VALIDATION`, `R2-M2-VALIDATION-MATRIX`, `R2-M2-STOP-CONDITIONS`, `R2-ACC-PROGRESSIVE-DISCLOSURE`. Dynamic inputs: exact B015 candidate diff, frozen contracts, mandatory commands, and external evidence. Builder conclusions and mutable implementation context are forbidden.

For every blueprint, PLAN/IMPLEMENT/ACCEPT/REPAIR create separate requests and ephemeral maps at their own fixed source commit/tree. Requests use `capacity_bytes=196608`, soft `0.55`, hard `0.70`; a stale map is rejected and regenerated, and hard overflow is `BLOCK_AND_REPLAN`.
