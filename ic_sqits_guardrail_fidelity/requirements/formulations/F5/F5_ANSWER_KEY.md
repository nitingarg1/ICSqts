HIDDEN EVALUATION ARTIFACT - DO NOT DISTRIBUTE WITH PUBLIC F5 CORPUS

- selected: 14
- split: 7 preserve_semantics / 7 near_miss
- human_validation_status: approved
- human_validation_date: 2026-08-28

## R001

- category: authorization/security
- variant_type: preserve_semantics
- difficult_syntax_stressed: permission expressed with "only if", a conjunction, role membership, and negated submitter identity
- exact_semantic_change: none
- review_note: Compare that approval requires the `approver` role and separately requires the actor not to be the submitter of that same payment request; both conditions must hold.

## R003

- category: authorization/security
- variant_type: near_miss
- difficult_syntax_stressed: AND/OR grouping changes the scope of the pre-settlement condition, followed by an implication with two required success effects
- exact_semantic_change: The pre-settlement condition applies only when the actor is the payment creator; an `admin` may void after settlement, whereas F0 requires both creators and admins to act before settlement.
- review_note: Confirm the single changed point is settlement-condition scope; creator-or-admin authorization, successful status change to `VOIDED`, and appending a void audit event remain unchanged.

## R013

- category: data protection/logging
- variant_type: preserve_semantics
- difficult_syntax_stressed: universal quantification over secret values with negated occurrence across all log output and an exception-path inclusion
- exact_semantic_change: none
- review_note: Compare that every secret obtained from either environment variables or secret-manager lookups is prohibited from all application logs in both normal execution and exception output.

## R016

- category: data protection/logging
- variant_type: near_miss
- difficult_syntax_stressed: let-bound issuance time, strict temporal comparison, and post-expiry implication with conjunctive response and audit effects
- exact_semantic_change: Expiry begins only when elapsed time strictly exceeds 15 minutes, rather than at 15 minutes after issuance as required by F0.
- review_note: Check the boundary at exactly 15 minutes; the `410` response and token-expired audit event after expiry remain unchanged.

## R024

- category: validation/input constraints
- variant_type: preserve_semantics
- difficult_syntax_stressed: chained inclusive temporal inequality with a calendar-day offset
- exact_semantic_change: none
- review_note: Compare both inclusive bounds: the scheduled date may equal the request date, may be at most 30 calendar days later, and may be neither earlier nor more than 30 calendar days later.

## R026

- category: validation/input constraints
- variant_type: preserve_semantics
- difficult_syntax_stressed: necessary constraint using XOR over one atomic option and one nested conjunction
- exact_semantic_change: none
- review_note: Compare all four identifier-form combinations: the constraint permits IBAN alone or account number plus routing number, and rejects neither complete form or both forms together, without asserting that this constraint alone guarantees overall request validity.

## R033

- category: state transitions/business invariants
- variant_type: near_miss
- difficult_syntax_stressed: implication into universal field quantification with an explicit inclusion that reverses the source exception
- exact_semantic_change: `reconciliation_note` loses its sole update exception and becomes immutable with every other mutable field after the payment reaches `EXECUTED`.
- review_note: Confirm post-`EXECUTED` immutability still applies to every other mutable field and that only the `reconciliation_note` exception changed.

## R036

- category: state transitions/business invariants
- variant_type: preserve_semantics
- difficult_syntax_stressed: only-if restriction over status-set membership plus a state-conditioned response and before/after equality
- exact_semantic_change: none
- review_note: Compare that cancellation may occur only for `DRAFT` or `SUBMITTED`, without guaranteeing success in those states; for `APPROVED` or `EXECUTED`, the response is `409` and status remains unchanged.

## R040

- category: state transitions/business invariants
- variant_type: near_miss
- difficult_syntax_stressed: bounded aggregate inequality followed by an "only if" transition threshold over a refund sum
- exact_semantic_change: The `REFUNDED` condition changes from approved refunds equaling the captured amount to approved refunds being at least the captured amount.
- review_note: Check equality versus at-least at and above the captured amount; the requirement to remain `CAPTURED` while the positive refund sum is below the captured amount remains unchanged.

## R042

- category: reliability/idempotency
- variant_type: preserve_semantics
- difficult_syntax_stressed: two-request relational condition combining key equality and body inequality, implying both a conflict response and non-mutation
- exact_semantic_change: none
- review_note: Compare that reuse of the same idempotency key with a different body returns `409` and that the second request neither creates nor modifies any payment record.

## R045

- category: reliability/idempotency
- variant_type: preserve_semantics
- difficult_syntax_stressed: bounded attempt cardinality combined with preceding-attempt causality and a no-attempt-after-success temporal prohibition
- exact_semantic_change: none
- review_note: Compare that retries occur only after `5xx`, total delivery attempts are limited to three, and all retries stop immediately after the first successful delivery.

## R047

- category: reliability/idempotency
- variant_type: near_miss
- difficult_syntax_stressed: inclusive temporal threshold combined with an upper cardinality bound for exclusive successor takeover
- exact_semantic_change: The stale-lock threshold changes from more than five minutes to at least five minutes, allowing takeover at exactly five minutes.
- review_note: Check only the strict-versus-inclusive time boundary; permission for successor takeover and the prohibition on multiple successor workers remain unchanged, without requiring that takeover occur.

## R053

- category: observability/audit
- variant_type: near_miss
- difficult_syntax_stressed: metric assignment from timestamp subtraction with an event selector inside the expression
- exact_semantic_change: The latency endpoint changes from the first terminal approval-or-rejection decision to the latest terminal approval-or-rejection decision.
- review_note: Check first-versus-latest terminal decision selection; payment submission remains the start timestamp and the computed elapsed value must still be recorded.

## R057

- category: observability/audit
- variant_type: near_miss
- difficult_syntax_stressed: per-interval cardinality bound combined with temporal suppression lasting until a closing transition
- exact_semantic_change: Exactly one alert per open interval becomes at most one alert per open interval, allowing zero alerts.
- review_note: Check the lost alert-existence obligation; duplicate alerts remain suppressed throughout each open interval until the circuit closes again.
