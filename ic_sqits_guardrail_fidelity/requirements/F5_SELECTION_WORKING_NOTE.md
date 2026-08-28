# Step 16 F5 Corpus Selection Working Note

## Status

**APPROVED_BY_HUMAN**

- Target: **14 requirements**
- Semantic authority: `requirements_v1.yaml`
- Human approved the exact 14-requirement set recorded below on 2026-08-28.

## Selection Rules

1. Select exactly 14 requirements from the 20-candidate shortlist below.
2. Preserve each requirement's F0 wording and category exactly as defined in `requirements_v1.yaml`; this note does not reinterpret or replace the canonical source.
3. Keep the target category balance: auth 2, data 2, validation 2, state 3, reliability 3, observability 2.
4. Prefer requirements with distinct, testable semantic structures and observable outcomes over near-duplicate constructions.
5. Use syntax tags only when the F0 semantics instantiate the construct. Tags are descriptive selection aids, not new requirements.
6. Preserve the human-approved set unless a later human decision explicitly records replacements.

### Syntax-Tag Definitions

Tags may overlap when one requirement instantiates multiple constructs.

- `negation`: prohibits an action, outcome, state change, or data exposure.
- `exception`: states an explicit exception, carve-out, or branch exempt from a general rule; a runtime exception alone does not qualify.
- `compound_boolean`: joins multiple prerequisites, outcomes, or alternatives into one rule, including conjunctions and exclusive choices.
- `temporal_ordering`: constrains event or state order, timing, duration, or a before/after relationship.
- `only_if`: makes a condition necessary before an action or transition is permitted.
- `until`: keeps an obligation or prohibition active through a stated terminating condition.

## Candidate Shortlist

| ID | Category | Exact F0 text | Syntax tags | Rationale |
|---|---|---|---|---|
| R001 | authorization/security | A payment request may be approved only by a user with the `approver` role, and the user who submitted the request must not approve that same request. | `only_if`, `negation`, `compound_boolean` | Combines role gating with separation of duties. |
| R003 | authorization/security | A payment may be voided only by its creator or by an `admin` user before settlement, and a successful void must set status to `VOIDED` and append a void audit event. | `only_if`, `temporal_ordering`, `compound_boolean` | Joins actor alternatives, a temporal gate, and two success effects. |
| R004 | authorization/security | If an approval request is made with an inactive session token, the system must return `401`, must not record an approval, and must not change payment state. | `negation`, `compound_boolean` | Exercises a triggered denial with two explicit non-mutation guarantees. |
| R007 | authorization/security | An approval delegate may act for the original approver only during the configured delegation window, and the delegate must not create a further delegation from that temporary authority. | `only_if`, `temporal_ordering`, `negation`, `compound_boolean` | Tests time-bounded authority and prohibition of delegation chaining. |
| R013 | data protection/logging | Secret values from environment variables or secret-manager lookups must not be written to application logs even when an exception occurs. | `negation` | Protects secrets on normal and exceptional paths without creating a carve-out. |
| R016 | data protection/logging | A document-download token must expire 15 minutes after issuance; requests using an expired token must return `410` and must append a token-expired audit event. | `temporal_ordering`, `compound_boolean` | Couples timed expiry with response and audit consequences. |
| R021 | validation/input constraints | A payment-create request must be rejected unless `amount` is greater than 0 and less than or equal to 100000. | `only_if`, `compound_boolean` | Provides lower and upper boundary semantics under an unless condition. |
| R024 | validation/input constraints | A scheduled payment date must not be earlier than the request date and must not be more than 30 calendar days after the request date. | `negation`, `temporal_ordering`, `compound_boolean` | Defines a closed temporal window with two forbidden regions. |
| R025 | validation/input constraints | A rejection decision must include a comment between 10 and 500 characters; approval decisions must not require that comment. | `negation`, `exception`, `compound_boolean` | Contrasts conditional rejection validation with an approval carve-out. |
| R026 | validation/input constraints | A beneficiary bank update request must include either an IBAN or both an account number and routing number, but it must not include both forms at the same time. | `negation`, `compound_boolean` | Encodes nested conjunction plus exclusive alternatives. |
| R031 | state transitions/business invariants | A payment may move from `DRAFT` to `SUBMITTED` only if it has at least one line item and the beneficiary record is verified. | `only_if`, `compound_boolean` | Gates a state transition on two independent prerequisites. |
| R033 | state transitions/business invariants | Once a payment reaches `EXECUTED`, no mutable field except `reconciliation_note` may be changed. | `negation`, `exception`, `temporal_ordering` | Expresses terminal-state immutability with one narrow exception. |
| R036 | state transitions/business invariants | A payment may be canceled only from `DRAFT` or `SUBMITTED`; a cancel request for `APPROVED` or `EXECUTED` must return `409` and leave status unchanged. | `only_if`, `negation`, `compound_boolean` | Covers allowed and denied state sets plus denial behavior. |
| R038 | state transitions/business invariants | Opening a chargeback on a captured payment must set `dispute_status` to `OPEN` and must block creation of further refunds until the dispute is resolved. | `until`, `temporal_ordering`, `compound_boolean` | Creates state and enforces a downstream ban through resolution. |
| R040 | state transitions/business invariants | A partially refunded payment must remain in `CAPTURED` status until the sum of approved refunds equals the captured amount; only then may status become `REFUNDED`. | `until`, `only_if`, `temporal_ordering` | Ties aggregate equality to the earliest permitted terminal transition. |
| R042 | reliability/idempotency | Reusing an idempotency key with a different request body must return `409` and must not create or modify any payment record. | `negation`, `compound_boolean` | Tests conflict handling and complete persistence non-mutation. |
| R045 | reliability/idempotency | Webhook delivery retries may occur on `5xx` responses up to three attempts, and retries must stop immediately after the first successful delivery. | `until`, `temporal_ordering`, `compound_boolean` | Combines retry eligibility, a hard bound, and success termination. |
| R047 | reliability/idempotency | If a payout executor lock remains stale for more than five minutes, exactly one successor worker may acquire the lock and continue the job. | `temporal_ordering`, `compound_boolean` | Exercises timed failover with exclusivity and continuation. |
| R053 | observability/audit | The system must record approval latency as the elapsed time between payment submission and the first terminal approval or rejection decision. | `temporal_ordering`, `compound_boolean` | Derives a metric from ordered start and first-terminal events. |
| R057 | observability/audit | When the provider retry circuit opens, the system must emit one alert event per open interval and must not emit duplicate alerts until the circuit has closed again. | `until`, `temporal_ordering`, `negation`, `compound_boolean` | Requires interval-scoped alerting and suppression through closure. |

## Recommendation

Recommend exactly these 14 IDs:

`R001`, `R003`, `R013`, `R016`, `R024`, `R026`, `R033`, `R036`, `R040`, `R042`, `R045`, `R047`, `R053`, `R057`

Balance below refers to **category balance**. Syntax tags may overlap and are reviewed separately.

### Recommended-Set Syntax Review

| ID | Syntax tags |
|---|---|
| R001 | `only_if`, `negation`, `compound_boolean` |
| R003 | `only_if`, `temporal_ordering`, `compound_boolean` |
| R013 | `negation` |
| R016 | `temporal_ordering`, `compound_boolean` |
| R024 | `negation`, `temporal_ordering`, `compound_boolean` |
| R026 | `negation`, `compound_boolean` |
| R033 | `negation`, `exception`, `temporal_ordering` |
| R036 | `only_if`, `negation`, `compound_boolean` |
| R040 | `until`, `only_if`, `temporal_ordering` |
| R042 | `negation`, `compound_boolean` |
| R045 | `until`, `temporal_ordering`, `compound_boolean` |
| R047 | `temporal_ordering`, `compound_boolean` |
| R053 | `temporal_ordering`, `compound_boolean` |
| R057 | `until`, `temporal_ordering`, `negation`, `compound_boolean` |

Aggregate syntax-tag counts for the recommended set:

| Syntax tag | Count |
|---|---:|
| `negation` | 8 |
| `exception` | 1 |
| `compound_boolean` | 11 |
| `temporal_ordering` | 9 |
| `only_if` | 4 |
| `until` | 3 |

Genuine exception syntax is represented by R033. R025 remains available as a replacement if human review prefers more branch/exception coverage.

| Category shorthand | Canonical category | Count |
|---|---|---:|
| auth | authorization/security | 2 |
| data | data protection/logging | 2 |
| validation | validation/input constraints | 2 |
| state | state transitions/business invariants | 3 |
| reliability | reliability/idempotency | 3 |
| observability | observability/audit | 2 |
| **Total** | | **14** |

## Alternatives / Excluded From Recommendation

These six candidates remain valid alternatives but are not in the recommendation:

| ID | Category | Why held as an alternative |
|---|---|---|
| R004 | authorization/security | Strong denial case, but recommended auth pair offers broader actor, temporal, state, and audit interactions. |
| R007 | authorization/security | Useful delegation-window case, but overlaps temporal authorization already represented by R003. |
| R021 | validation/input constraints | Clear numeric bounds, but less structurally varied than the selected temporal-window and exclusive-form cases. |
| R025 | validation/input constraints | Valuable branch-sensitive rule, but selected validation pair gives temporal and nested exclusive-boolean coverage. |
| R031 | state transitions/business invariants | Strong prerequisite gate, but selected state set emphasizes exception, negative-state branches, and aggregate temporal transition. |
| R038 | state transitions/business invariants | Useful `until` rule, but `until` is already represented by R040, R045, and R057 in the recommended corpus. |

## Human Decision

Status: **APPROVED_BY_HUMAN**

- Approved IDs: `R001`, `R003`, `R013`, `R016`, `R024`, `R026`, `R033`, `R036`, `R040`, `R042`, `R045`, `R047`, `R053`, `R057`
- Approval date: **2026-08-28**
- [x] Approve the recommended 14 IDs exactly as listed.
- [ ] Approve with replacements. List each replacement as `REMOVE R___; ADD R___`:

```text
Decision: APPROVED_BY_HUMAN
Replacements:
Reviewer:
Date: 2026-08-28
Notes:
```
