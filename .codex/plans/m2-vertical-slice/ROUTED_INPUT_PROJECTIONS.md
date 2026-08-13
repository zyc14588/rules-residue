<!-- SECTION-ID: R2-M2-REFERENCE-WORK-PACKAGES -->
# Routed projection: M2 reference work packages

Non-authoritative routing transport only. Source: `docs/implementation/r2/M2_REFERENCE_WORK_PACKAGES.yaml`; source SHA-256: `9503b4405a0ed852936bd119f4a6b275edc0278df28709bff54c7a9802299d22`.

```yaml
schema_version: '1.0'
status: REFERENCE_INPUT_NOT_NATIVE_PLAN
work_packages:
- id: M2-WP-01
  title: R2权威安装与M1真相传播
  depends: []
  risk: HIGH
  owner: Codex
  scope: docs/governance/schemas/authoring only
  deliver:
  - R2 authority installed
  - 191 decisions machine-valid
  - M1 OPEN truth superseded
  - progressive routes registered
  - no runtime change
  accept:
  - decision count and uniqueness
  - section IDs/freshness
  - GM truth isolation
  - current M1 acceptance remains pass
- id: M2-WP-02
  title: 规范规则语义与验证器
  depends:
  - M2-WP-01
  risk: HIGH
  owner: Codex
  scope: R2 schemas, validators, fixtures; no gameplay script yet
  deliver:
  - rule semantic schema
  - save protocols
  - immediate/long-term effects
  - collision model
  - residue
  - negative fixtures
  accept:
  - schema/production parity
  - unknown field rejection
  - absolute rule cases
  - logical anomaly deterministic execution
- id: M2-WP-03
  title: 循环、永久状态与锚点内核
  depends:
  - M2-WP-02
  risk: CRITICAL
  owner: Codex+OpenCode
  scope: slice runtime data, Lua, events, tests
  deliver:
  - TPK restart
  - key-item inversion
  - inheritance whitelist
  - permanent anomaly
  - personal universal cost
  - fixed/self-built/original anchors
  accept:
  - deterministic replay
  - exactly-once inversion
  - original anchor invalidates others
  - causal bankruptcy classification
- id: M2-WP-04
  title: 角色、纠缠因果与亡者视角
  depends:
  - M2-WP-02
  - M2-WP-03
  risk: HIGH
  owner: Codex+OpenCode
  scope: character schemas, visibility, Lua and tests
  deliver:
  - 2-6 player creation
  - entangled causality draw
  - dead-view private projection
  - causal tether
  - paid physical intervention
  - personal authorization
  accept:
  - no direct dead-to-living communication
  - range enforced
  - other player cannot spend cost
  - missing talent remains completable
- id: M2-WP-05
  title: 测试大区与逻辑完全异常区
  depends:
  - M2-WP-02
  - M2-WP-04
  risk: CRITICAL
  owner: Codex+OpenCode+Grok
  scope: one M2 test region, 3-5 domains, zone, factions, 2D assets
  deliver:
  - observation
  - resolution
  - permanent stabilization
  - explicit warning
  - no-death solution
  - skip route with loss
  - region rewards
  accept:
  - full region state chain
  - no perfect skip
  - cross-loop behavior
  - 2-6 player alternatives
  - map skill difference
- id: M2-WP-06
  title: 装备规则与关键道具两相
  depends:
  - M2-WP-02
  - M2-WP-05
  risk: HIGH
  owner: Codex+OpenCode+Grok
  scope: equipment semantics, Lua, 2D item assets
  deliver:
  - one short rule
  - one long rule
  - semantic length classifier
  - Type1/Type2 visuals and mechanics
  - early Type2 response
  accept:
  - text length does not change class
  - rule collision
  - same silhouette
  - wrong early use sets ending risk
- id: M2-WP-07
  title: 主持、自然语言与渐进式信息
  depends:
  - M2-WP-02
  - M2-WP-04
  - M2-WP-05
  risk: CRITICAL
  owner: Codex
  scope: AI contract, tools, visibility, recorded/fake model tests
  deliver:
  - action draft
  - actual action validation
  - known info/causal graph
  - player/host/mechanical separation
  - bounded narration
  accept:
  - AI cannot invent fatal rule
  - AI cannot read full seed
  - ambiguous terminal action not executed
  - recorded response tests
- id: M2-WP-08
  title: 代理Boss与三分支终局模拟
  depends:
  - M2-WP-03
  - M2-WP-05
  - M2-WP-06
  - M2-WP-07
  risk: CRITICAL
  owner: Codex+OpenCode
  scope: proxy Boss, maintenance gap, ending state machines
  deliver:
  - multi-stage Boss
  - Boss-entry roster lock
  - maintenance gap
  - branch1/2/3 simulations
  - control removal after destruction threshold
  accept:
  - no confirmation popup but intent exact
  - pre-threshold cost intervention
  - post-threshold no action
  - dead-view return eligibility
  - Boss reset with permanent rewards kept
- id: M2-WP-09
  title: 纯2D表现、地图与可访问性
  depends:
  - M2-WP-05
  - M2-WP-06
  - M2-WP-08
  risk: MEDIUM
  owner: Codex+Grok
  scope: 2D player UI/assets, map layers, text/audio alternatives
  deliver:
  - 2D scenes
  - map skill recording
  - hidden structural tags
  - accessible text/audio clues
  - restart presentation
  accept:
  - no 2.5D dependency
  - host full map/player limited map
  - no answer leak
  - equivalent non-audio channel
- id: M2-WP-10
  title: 完整技术验证、确定性构建与独立验收
  depends:
  - M2-WP-01
  - M2-WP-02
  - M2-WP-03
  - M2-WP-04
  - M2-WP-05
  - M2-WP-06
  - M2-WP-07
  - M2-WP-08
  - M2-WP-09
  risk: CRITICAL
  owner: Independent Codex Verifier
  scope: read-only fixed candidate
  deliver:
  - candidate-bound evidence
  - full end-to-end vectors
  - repeat safety filter evidence
  - deterministic package hashes
  - findings
  accept:
  - all mandatory M2 gates
  - no source mutation
  - no platform modification
  - no unverified external claims
```

<!-- SECTION-ID: R2-INSTALL-INTEGRATION-CONFLICT-EVIDENCE -->
# Routed projection: R2 installation integration classifications

Non-authoritative routing transport only. Source: `governance/evidence/r2-authority-install/integration-conflicts.yaml`; source SHA-256: `8647db042fcfae3bfc0e7913373b23bbed1d95224d7e417c8e09effbcd34ace0`.

```yaml
schema_version: '1.0'
record_id: R2-INTEGRATION-CONFLICT-CLASSIFICATION
installation_scope: AUTHORITY_ONLY
default_status: DEFERRED_WITH_NON_BLOCKING_PROOF
blocked_design_conflicts: []
items:
- conflict_id: R2-INT-001
  classification: PLATFORM_CAPABILITY_PROBE
  status: DEFERRED_WITH_NON_BLOCKING_PROOF
  proof: Install 2-to-6-seat authority now; probe host schema and server limits during M2.
- conflict_id: R2-INT-002
  classification: PLATFORM_CAPABILITY_PROBE
  status: DEFERRED_WITH_NON_BLOCKING_PROOF
  proof: Install deceased-view whitelist and tether contracts now; probe host support during M2.
- conflict_id: R2-INT-003
  classification: R2_COMPATIBILITY_ADAPTER
  status: DEFERRED_WITH_NON_BLOCKING_PROOF
  proof: Preserve explicit in-world multi-step intent; a package-side M2 adapter must not add a terminal UI confirmation.
- conflict_id: R2-INT-004
  classification: R2_COMPATIBILITY_ADAPTER
  status: DEFERRED_WITH_NON_BLOCKING_PROOF
  proof: Distinguish platform safety warnings from puzzle signals while retaining conspicuous anomaly and campaign-termination warnings.
- conflict_id: R2-INT-005
  classification: PLATFORM_CAPABILITY_PROBE
  status: DEFERRED_WITH_NON_BLOCKING_PROOF
  proof: Install 35-to-60 session and approximately 100-hour authority; probe campaign save and version locking during M2.
- conflict_id: R2-INT-006
  classification: PLATFORM_CAPABILITY_PROBE
  status: DEFERRED_WITH_NON_BLOCKING_PROOF
  proof: Install lineage-level unlock boundaries; probe account and cross-campaign declarations without inheriting answer state.
- conflict_id: R2-INT-007
  classification: PACKAGE_DECLARABLE
  status: DEFERRED_WITH_NON_BLOCKING_PROOF
  proof: Install six-region eligibility and the one-test-region M2 limit without claiming complete launch content.
- conflict_id: R2-INT-008
  classification: PLATFORM_CAPABILITY_PROBE
  status: DEFERRED_WITH_NON_BLOCKING_PROOF
  proof: Install world-destruction termination semantics; M2 may simulate only in a candidate package and must not rewrite platform history.
- conflict_id: R2-INT-009
  classification: PACKAGE_DECLARABLE
  status: DEFERRED_WITH_NON_BLOCKING_PROOF
  proof: Install separation among player claims, evidence, Agent memory, and authoritative state.
- conflict_id: R2-INT-010
  classification: R2_COMPATIBILITY_ADAPTER
  status: DEFERRED_WITH_NON_BLOCKING_PROOF
  proof: Use schemas/r2 and package-namespaced extensions without changing the platform generic item model.
- conflict_id: R2-INT-011
  classification: PLATFORM_CAPABILITY_PROBE
  status: DEFERRED_WITH_NON_BLOCKING_PROOF
  proof: Install all 18 repeat-filter stages; probe runtime generation, restore, and hot-update support during M2.
- conflict_id: R2-INT-012
  classification: R2_COMPATIBILITY_ADAPTER
  status: DEFERRED_WITH_NON_BLOCKING_PROOF
  proof: Keep logical-anomaly mechanical execution deterministic and never randomize the correct answer.
```
