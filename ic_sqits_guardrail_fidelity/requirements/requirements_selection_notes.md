# Requirements Selection Notes

Selection target approved: 48-55.
Frozen selection chosen: 48 requirements, 8 per category.

## authorization/security

requirement_id | category | keep/maybe/drop | obligations_count | state_effect | role_or_negation_or_exception | evidence_clear | duplicate_of | notes
R001 | authorization/security | keep | 3 | no | yes | yes | - | Multi-obligation role check plus self-approval ban; clear deny branch.
R002 | authorization/security | keep | 4 | no | yes | yes | - | Threshold + two distinct approvers + finance_manager requirement; strong semantic richness.
R003 | authorization/security | keep | 4 | yes | yes | yes | - | Role + temporal precondition + explicit status and audit effects.
R004 | authorization/security | keep | 4 | no | yes | yes | - | Strong negative control: `401`, no approval record, no payment-state mutation.
R005 | authorization/security | keep | 4 | no | yes | yes | - | Role-conditioned field suppression with concrete payload evidence.
R006 | authorization/security | drop | 3 | no | yes | yes | - | Valid but compact; weaker than richer auth rules with stronger branch or state effects.
R007 | authorization/security | keep | 3 | no | yes | yes | - | Delegation-window exception plus chained-delegation ban.
R008 | authorization/security | keep | 4 | no | yes | yes | - | Role gate + settled-state precondition + incident-ticket reference.
R009 | authorization/security | maybe | 4 | no | yes | yes | R005 | Useful export artifact, but overlaps role-based forbidden exposure shape.
R010 | authorization/security | keep | 4 | no | yes | yes | - | Service-to-service allowlist auth with explicit no-record negative path.

Strong keeps: R001, R002, R003, R004, R005, R007, R008, R010.
Maybes: R009.
Drops: R006.

## data protection/logging

requirement_id | category | keep/maybe/drop | obligations_count | state_effect | role_or_negation_or_exception | evidence_clear | duplicate_of | notes
R011 | data protection/logging | keep | 3 | no | yes | yes | - | Deterministic log masking with precise forbidden output.
R012 | data protection/logging | keep | 4 | yes | no | yes | - | Status-change audit completeness with fixed fields and direct transition linkage.
R013 | data protection/logging | keep | 3 | no | yes | yes | - | Secret non-leak rule across normal and exception logging paths.
R014 | data protection/logging | keep | 4 | yes | yes | yes | - | Permission-denial audit rule with fixed security fields.
R015 | data protection/logging | drop | 3 | no | yes | yes | R005 | Cross-category duplicate of readonly masking shape already covered more broadly.
R016 | data protection/logging | keep | 3 | yes | yes | yes | - | Time expiry + `410` + audit side effect give rich variant space.
R017 | data protection/logging | maybe | 2 | no | yes | yes | - | Clear rule, but thinner than selected logging rules with more obligations.
R018 | data protection/logging | keep | 3 | yes | no | yes | - | Download audit with requester, filters, row count, and timestamp.
R019 | data protection/logging | keep | 2 | no | yes | yes | - | Salted-hash versus raw-email negative control is highly testable.
R020 | data protection/logging | keep | 3 | yes | yes | yes | - | Symmetric success/denial audit coverage adds useful branch richness.

Strong keeps: R011, R012, R013, R014, R016, R018, R019, R020.
Maybes: R017.
Drops: R015.

## validation/input constraints

requirement_id | category | keep/maybe/drop | obligations_count | state_effect | role_or_negation_or_exception | evidence_clear | duplicate_of | notes
R021 | validation/input constraints | keep | 3 | no | no | yes | - | Clean numeric lower/upper bound rule with strong boundary cases.
R022 | validation/input constraints | drop | 3 | no | no | yes | - | Too trivial as a one-check enum rule once richer validations are available.
R023 | validation/input constraints | maybe | 3 | no | no | yes | - | Useful header validation, but semantically thinner than selected items.
R024 | validation/input constraints | keep | 3 | no | yes | yes | - | Temporal lower and upper window bounds are easy to benchmark.
R025 | validation/input constraints | keep | 4 | no | yes | yes | - | Best conditional validation candidate: rejection requires comment, approval does not.
R026 | validation/input constraints | keep | 4 | no | yes | yes | - | Exclusive-or structure gives strong compliant, violating, and boundary variants.
R027 | validation/input constraints | keep | 4 | no | yes | yes | - | File-type plus file-size checks create multiple concrete failure modes.
R028 | validation/input constraints | keep | 3 | no | yes | yes | - | Collection cardinality plus uniqueness in same artifact.
R029 | validation/input constraints | keep | 3 | no | yes | yes | - | HTTPS plus tenant allowlist is security-relevant and observable.
R030 | validation/input constraints | keep | 3 | no | yes | yes | - | Cross-record remaining-balance invariant is richer than simple field validation.

Strong keeps: R021, R024, R025, R026, R027, R028, R029, R030.
Maybes: R023.
Drops: R022.

## state transitions/business invariants

requirement_id | category | keep/maybe/drop | obligations_count | state_effect | role_or_negation_or_exception | evidence_clear | duplicate_of | notes
R031 | state transitions/business invariants | keep | 4 | yes | yes | yes | - | Classic transition gate with two concrete preconditions.
R032 | state transitions/business invariants | keep | 4 | yes | yes | yes | - | Policy-derived threshold before approval transition.
R033 | state transitions/business invariants | keep | 3 | no | yes | yes | - | Post-execution immutability with one explicit exception.
R034 | state transitions/business invariants | keep | 2 | yes | no | yes | - | Direct state-effect rule: set `REJECTED` and clear scheduled timestamp.
R035 | state transitions/business invariants | maybe | 3 | no | yes | yes | R043 | Good duplicate-suppression rule, but overlaps reliability idempotency set.
R036 | state transitions/business invariants | keep | 4 | no | yes | yes | - | Allowed-state matrix plus `409` and unchanged-state negative path.
R037 | state transitions/business invariants | keep | 3 | yes | yes | yes | - | Expiry-driven invalidation plus emitted event.
R038 | state transitions/business invariants | keep | 2 | yes | yes | yes | - | Dispute state change plus refund block gives explicit downstream effect.
R039 | state transitions/business invariants | drop | 2 | yes | yes | yes | R044 | Narrow duplicate-event state shape weaker than broader idempotency/event rules.
R040 | state transitions/business invariants | keep | 2 | yes | yes | yes | - | Aggregate refund total drives final status transition.

Strong keeps: R031, R032, R033, R034, R036, R037, R038, R040.
Maybes: R035.
Drops: R039.

## reliability/idempotency

requirement_id | category | keep/maybe/drop | obligations_count | state_effect | role_or_negation_or_exception | evidence_clear | duplicate_of | notes
R041 | reliability/idempotency | keep | 4 | no | yes | yes | - | Core same-key same-body idempotency with original ID reuse and no duplicate row.
R042 | reliability/idempotency | keep | 3 | no | yes | yes | - | Conflict branch for same key different body; strong negative control.
R043 | reliability/idempotency | keep | 3 | no | yes | yes | - | Retry-after-timeout must remain single approval action.
R044 | reliability/idempotency | keep | 3 | yes | yes | yes | - | Duplicate message suppression plus required `duplicate_ignored` event.
R045 | reliability/idempotency | keep | 3 | no | yes | yes | - | Bounded retries with clear stop-on-success behavior.
R046 | reliability/idempotency | keep | 3 | yes | yes | yes | - | Crash recovery under same job ID without duplicate rows.
R047 | reliability/idempotency | keep | 3 | yes | yes | mixed | - | Concurrency takeover rule adds distinct stale-lock semantic challenge.
R048 | reliability/idempotency | drop | 2 | no | yes | yes | R045 | Simple time-window dedup weaker than richer retry/idempotency rules.
R049 | reliability/idempotency | keep | 3 | yes | yes | yes | - | Checksum duplicate import with duplicate marking and no reapply.
R050 | reliability/idempotency | maybe | 2 | no | no | mixed | - | Useful uniqueness invariant, but thinner and less branch-rich than selected set.

Strong keeps: R041, R042, R043, R044, R045, R046, R047, R049.
Maybes: R050.
Drops: R048.

## observability/audit

requirement_id | category | keep/maybe/drop | obligations_count | state_effect | role_or_negation_or_exception | evidence_clear | duplicate_of | notes
R051 | observability/audit | keep | 2 | no | no | yes | - | Cross-artifact `correlation_id` consistency between response and request log.
R052 | observability/audit | maybe | 3 | yes | yes | yes | - | Useful failure metric rule, but lighter than selected observability items.
R053 | observability/audit | keep | 3 | yes | yes | yes | - | Derived latency metric from two timestamps and first terminal decision.
R054 | observability/audit | keep | 3 | yes | no | yes | - | Structured start/end job events with fixed fields.
R055 | observability/audit | keep | 3 | yes | yes | yes | - | Direct guardrail traceability to originating `requirement_id`.
R056 | observability/audit | drop | 3 | yes | no | yes | R012 | Close duplicate of status-transition audit completeness already kept.
R057 | observability/audit | keep | 3 | yes | yes | yes | - | One alert per open interval with reopen exception and dedup semantics.
R058 | observability/audit | keep | 3 | yes | yes | yes | - | Manual override reason plus audit artifact on privileged path.
R059 | observability/audit | keep | 3 | yes | no | yes | - | Metric increment plus review-case creation gives strong semantic richness.
R060 | observability/audit | keep | 3 | yes | no | yes | - | Export completion event with fixed measurable fields.

Strong keeps: R051, R053, R054, R055, R057, R058, R059, R060.
Maybes: R052.
Drops: R056.

## Final Selection

Frozen set IDs: R001, R002, R003, R004, R005, R007, R008, R010, R011, R012, R013, R014, R016, R018, R019, R020, R021, R024, R025, R026, R027, R028, R029, R030, R031, R032, R033, R034, R036, R037, R038, R040, R041, R042, R043, R044, R045, R046, R047, R049, R051, R053, R054, R055, R057, R058, R059, R060.

Cross-category duplicate cuts: R015 -> R005, R035 -> R043, R056 -> R012.

Quota check:
- Total selected: 48.
- Selected per category: 8 each.
- Selected with 3-4 obligations: 43.
- Selected with explicit state effects: 23.
- Selected with role, negation, or exception structure: 39.

Final sweep outcome:
- No category starved.
- Trivial enum/header-only items deprioritized first.
- Duplicate audit-completeness and masking shapes reduced.
- Final set keeps threshold, role check, negation, exception, state transition, audit/event, retry/idempotency, and forbidden-exposure coverage.
