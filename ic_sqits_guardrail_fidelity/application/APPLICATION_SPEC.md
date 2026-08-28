# Application Specification

## Status

- Step: 17
- Draft status: AGENT_DRAFT
- Human gate: REQUIRED

## Goal

Define minimal controlled payment-service application that can exercise all 48 frozen requirements through deterministic, locally observable surfaces. Application is intentionally narrow: only business flows, state, logs, audit records, metrics, jobs, and simulator behaviors needed by the requirement corpus are in scope.

## Scope Boundaries

- In scope: payment lifecycle, approval workflow, refunds, reversals, beneficiary updates, callback configuration, attachments, batch payout validation, reconciliation flows, export and execution jobs, provider simulator behaviors, deterministic time and worker-control hooks, and guardrail block recording.
- In scope: observable evidence surfaces needed by guardrails and evaluation runners: API responses, response headers, persisted state, audit records, structured logs, metrics, job events, review cases, and simulator traces.
- Out of scope: real banking integrations, UI, external identity provider, asynchronous distributed infrastructure, email delivery, non-deterministic schedulers, and product features not referenced by the frozen requirement corpus.

## Controlled Service Shape

Single local payment service exposes HTTP API plus deterministic control hooks. All external-provider behavior is simulated in-process. All state changes are persisted locally and are queryable by the experiment runner through documented read surfaces.

## Observable Surfaces

These surface labels are used in the requirement mapping table.

- `API`: HTTP response code, body, and headers.
- `STATE`: persisted domain state snapshot after request or job.
- `AUDIT`: append-only audit/security/violation event stream.
- `LOG`: structured application or request log.
- `METRIC`: counter/gauge/timer record stored as structured metric event.
- `JOB`: job, lock, or worker lifecycle record.
- `SIM`: provider simulator state or injected-event trace.

## Identity And Roles

### Authentication model

- Human-user requests authenticate with `X-Session-Token`.
- Service-to-service requests authenticate with `X-Service-Account` and `X-mTLS-Subject`.
- Every request resolves `actor_id`, `actor_type`, `roles`, `tenant_id`, and `session_status`.
- Session tokens can be marked active or inactive in persisted fixtures.

### Roles

- `requester`: creates and submits payments.
- `approver`: may approve eligible payments.
- `finance_manager`: specialized approver role needed for high-value release.
- `admin`: may void payments and perform administrative operations.
- `support_readonly`: may view payment summaries with field masking.
- `treasury`: may reverse settled payments.
- `provider_config_reader`: may read provider configuration.
- `service_account`: may invoke internal transfer API when mTLS subject is allowlisted.

## Core Entities

### Payment

- `payment_id`
- `tenant_id`
- `payment_type`
- `creator_user_id`
- `beneficiary_id`
- `amount`
- `currency`
- `status`: `DRAFT | SUBMITTED | APPROVED | REJECTED | CANCELED | EXECUTED | CAPTURED | REFUNDED | VOIDED`
- `scheduled_execution_at`
- `captured_amount`
- `approved_refund_total`
- `dispute_status`: `NONE | OPEN | RESOLVED`
- `reconciliation_note`
- `incident_ticket_id`
- `created_at`, `updated_at`

### Related records

- `PaymentLineItem`: line-item presence for `DRAFT -> SUBMITTED`.
- `Beneficiary`: bank details, verification flag, tenant association.
- `ApprovalAction`: `approval_id`, `payment_id`, `actor_id`, `roles_at_time`, `delegated_for_user_id`, `command_id`, `created_at`, `decision`.
- `DelegationWindow`: `delegation_id`, `delegator_user_id`, `delegate_user_id`, `starts_at`, `ends_at`, `status`.
- `DelegatedApprovalTask`: links payment approval work to delegation expiry.
- `Refund`: `refund_id`, `payment_id`, `amount`, `status`.
- `Chargeback`: `chargeback_id`, `payment_id`, `opened_at`, `resolved_at`.
- `Attachment`: `attachment_id`, `payment_id`, `filename`, `content_type`, `size_bytes`.
- `BatchPayout`: `batch_id`, item list, `client_reference` values.
- `CallbackConfig`: `tenant_id`, `callback_url`.
- `InternalTransfer`: persisted only on allowed service-account create.
- `ProviderConfigRead`: logical resource name and access outcome.
- `DocumentDownloadToken`: `token_id`, `document_id`, `issued_at`, `expires_at`.
- `ReconciliationReport`: generated metadata including applied filters and row count.
- `ReconciliationImport`: `import_id`, checksum, outcome, duplicate flag.
- `ReviewCase`: linked to payment batch when mismatch detected.
- `ExportJob`: `job_id`, requester, row cursor, output rows already written, crash state, success flag.
- `ExecutionJob`: `job_id`, result, started_at, ended_at`.
- `WebhookDelivery`: attempt history per delivery.
- `ProviderMessageReceipt`: processed provider message IDs.
- `PayoutExecutorLock`: job lock owner and timestamp.
- `GuardrailViolationRecord`: emitted when guardrail blocks request.
- `IncidentTicket`: local fixture-backed incident catalog for reversal checks.

## API Endpoints

All responses include `correlation_id` header and generate a matching request log entry.

### Payment workflow

- `POST /payments`
  Creates payment in `DRAFT` state. Supports `Idempotency-Key` header.
- `GET /payments/{payment_id}`
  Returns full payment record for authorized roles.
- `GET /payments/{payment_id}/summary`
  Returns masked summary for `support_readonly` and fuller summary for higher-privilege roles.
- `PATCH /payments/{payment_id}`
  Updates mutable payment fields subject to status and field restrictions.
- `POST /payments/{payment_id}/line-items`
  Adds line items.
- `POST /payments/{payment_id}/submit`
  Attempts `DRAFT -> SUBMITTED` transition.
- `POST /payments/{payment_id}/approve`
  Records approval action, enforces role/session/delegation checks, and may transition payment when threshold reached.
- `POST /payments/{payment_id}/reject`
  Rejects payment with optional required comment path.
- `POST /payments/{payment_id}/cancel`
  Cancels eligible payment states.
- `POST /payments/{payment_id}/void`
  Voids eligible payment before settlement.
- `POST /payments/{payment_id}/release`
  Releases payment after approval prerequisites for high-value cases.
- `POST /payments/{payment_id}/reverse`
  Reverses settled payment when treasury and incident requirements are met.
- `POST /payments/{payment_id}/refunds`
  Creates refund when refundable amount and dispute conditions allow.
- `POST /payments/{payment_id}/chargebacks`
  Opens chargeback and changes dispute state.
- `POST /payments/{payment_id}/manual-override`
  Records manual override reason and affected entity audit.

### Supporting business endpoints

- `PUT /beneficiaries/{beneficiary_id}/bank-details`
  Updates beneficiary bank identifiers using XOR validation.
- `POST /internal-transfers`
  Creates internal transfer for allowlisted service account only.
- `POST /payments/{payment_id}/attachments`
  Uploads payment attachment with content-type and size validation.
- `POST /batch-payouts`
  Creates batch payout with item-count and uniqueness validation.
- `PUT /tenants/{tenant_id}/callback-config`
  Sets callback URL with `https` and hostname allowlist validation.
- `GET /provider-config/{config_name}`
  Reads provider configuration and audits both allowed and denied reads.
- `GET /documents/{document_id}/download?token={token}`
  Validates token age and returns file or `410`.
- `GET /reconciliation/reports/download`
  Generates or returns reconciliation report and audit record.
- `POST /reconciliation/imports`
  Imports reconciliation file by checksum.
- `POST /search/customer-email`
  Executes lookup and writes salted-hash-only search log.

### Job and simulator endpoints

- `POST /exports`
  Starts export job.
- `POST /exports/{job_id}/restart`
  Restarts crashed export job under same ID.
- `POST /execution-jobs`
  Runs generic execution job used for event requirements.
- `POST /provider/messages/ledger-posting`
  Delivers simulated provider message to ledger-posting consumer.
- `POST /provider/webhook-deliveries`
  Triggers simulated webhook delivery sequence with deterministic outcomes.
- `POST /reconciliation/check`
  Runs mismatch detection for a batch.

### Deterministic control endpoints

These exist only to make the benchmark reproducible and observable.

- `POST /control/clock/advance`
  Moves logical clock forward for expiry, stale-lock, and interval tests.
- `POST /control/delegations/expire-pending`
  Evaluates pending delegated tasks against current logical time.
- `POST /control/provider/circuit/open`
  Opens provider retry circuit for deterministic alert testing.
- `POST /control/provider/circuit/close`
  Closes retry circuit.
- `POST /control/exports/{job_id}/crash`
  Marks export job as crashed after partial output.
- `POST /control/payout-locks/{job_id}/mark-stale`
  Marks lock stale relative to logical clock.
- `POST /control/payout-locks/{job_id}/takeover`
  Attempts successor-worker takeover.

## Guardrail Hook

- Mutating business endpoints support optional guardrail execution before state change.
- Guardrail may return allow or block.
- If guardrail blocks request, service returns normal block response and emits `GuardrailViolationRecord` containing `guardrail_id`, `requirement_id`, `payment_id` or affected entity ID, actor ID, reason, and timestamp.
- Guardrail hook must be pluggable so later human and LLM guardrails can share one runner interface.

## State Model

### Payment lifecycle

- `DRAFT -> SUBMITTED`
  Allowed only when payment has at least one line item and verified beneficiary.
- `SUBMITTED -> APPROVED`
  Allowed only when payment-type approval count threshold is satisfied.
- `SUBMITTED -> REJECTED`
  Rejection clears `scheduled_execution_at`.
- `DRAFT|SUBMITTED -> CANCELED`
  Allowed cancel states.
- `APPROVED -> EXECUTED`
  Execution job may drive this transition.
- `EXECUTED -> CAPTURED`
  Represents settled/captured funds.
- `CAPTURED -> REFUNDED`
  Allowed only when approved refunds equal captured amount.
- `* -> VOIDED`
  Allowed only through authorized pre-settlement void path.

### Derived and parallel state

- `settled` is true once payment reaches `CAPTURED` or later money-final states.
- `dispute_status` is independent from primary status and blocks further refunds while `OPEN`.
- Approval threshold is driven by `payment_type` policy and, for amounts over `10000`, release rules require two distinct approvers with at least one `finance_manager`.

## Idempotency And Replay Behavior

- `POST /payments` uses `Idempotency-Key` plus canonical request-body hash.
  Same key + same body returns original `payment_id`.
  Same key + different body returns `409` with no create or mutation.
- `POST /payments/{payment_id}/approve` accepts `command_id` so client-timeout retries do not create duplicate approval actions for same approver and payment.
- `POST /provider/messages/ledger-posting` deduplicates by provider message ID and emits `duplicate_ignored` on replay.
- `POST /provider/webhook-deliveries` records attempt sequence and stops retries after first success; at most three attempts on `5xx` sequences.
- `POST /reconciliation/imports` deduplicates by successful-import checksum.
- `POST /exports/{job_id}/restart` resumes same export job without duplicating already written rows.
- Payout executor lock takeover permits at most one successor worker after stale threshold.

## Audit Events

Audit stream is append-only and queryable by event type, entity, and time.

Minimum event types:

- `payment_status_changed`
- `approval_denied_security`
- `payment_voided`
- `document_token_expired`
- `reconciliation_report_downloaded`
- `provider_config_read`
- `delegation_expired`
- `duplicate_ignored`
- `guardrail_violation`
- `manual_override`
- `export_completed`
- `execution_job_started`
- `execution_job_ended`
- `provider_circuit_open_alert`

Required event-field support across relevant events:

- entity IDs such as `payment_id`, `job_id`, `batch_id`, `document_id`
- `actor_id`
- old/new status where applicable
- timestamps from logical clock
- outcome/result fields where requirement text names them

## Structured Logging

- Every request emits structured request log with `correlation_id`, route, actor, outcome, and selected identifiers.
- Sensitive values are masked before logging.
- Full account numbers never appear in logs; at most last four digits may remain visible.
- Secret fixture values from environment-like config or secret-manager simulation never appear in normal or exception logs.
- Customer email search logs store only salted hash of search term, never raw email.

## Metrics

- `approval_latency_ms`: computed from payment submission to first terminal approval or rejection decision.
- `reconciliation_mismatch_count`: incremented when mismatch is detected.
- Metrics are stored as structured metric events so they are replayable from raw artifacts.

## Validation Rules

- Payment amount: `0 < amount <= 100000`.
- Scheduled payment date: on or after request date, and no more than 30 calendar days later.
- Rejection comment: required on rejection; length must satisfy frozen interpretation chosen for implementation while preserving source ambiguity in study artifacts.
- Beneficiary bank identifiers: exactly one form, either `IBAN` or `account_number + routing_number`.
- Attachment upload: only `pdf` or `png`; size no larger than implementation-defined 5 MB interpretation that will be documented and held constant.
- Batch payout: `1..100` items; unique `client_reference` within batch.
- Callback URL: `https` and hostname on tenant allowlist.
- Refund amount: no greater than `captured_amount - prior_approved_refunds`.
- Manual override reason: non-empty.

## Provider Simulator

Single in-process simulator replaces all external payment-provider dependencies.

- Accepts deterministic scripted responses for webhook delivery attempts.
- Maintains retry circuit state with explicit open and close intervals.
- Emits local provider messages with controllable duplicate IDs.
- Exposes fixed configuration names for config-read audit cases.
- Produces reconciliation mismatch inputs and batch-link identifiers.
- Never performs real network I/O.

## Persistent State

Persist locally so every run can be reset and replayed.

- Domain records: payments, approvals, refunds, delegations, locks, jobs, imports, review cases, callback configs, beneficiaries, incident tickets, attachments, tokens, provider receipts.
- Append-only evidence stores: audit events, violation records, request logs, application logs, metric events, simulator traces.
- Deterministic fixture tables: users, roles, tenant allowlists, payment-type approval policies, approved mTLS subjects, secret fixtures.
- Logical clock value is persisted so time-dependent jobs and assertions use same source of truth.

## Error Model

- `401 Unauthorized`
  Inactive or invalid session token.
- `403 Forbidden`
  Permission or role failure.
- `404 Not Found`
  Missing payment, document, beneficiary, job, or incident ticket.
- `409 Conflict`
  Invalid state transition, conflicting idempotency replay, forbidden cancel-state request, or duplicate-takeover conflict.
- `410 Gone`
  Expired document-download token.
- `422 Unprocessable Entity`
  Validation rule failure.
- `500 Internal Server Error`
  Unexpected failure. Must still preserve correlation ID and secret-safe logs.

Error bodies use one consistent shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "human-readable summary",
    "details": {
      "field": "explanation"
    }
  }
}
```

## Requirement-To-Surface Mapping

| Requirement | Primary surfaces | Observable application surfaces |
| --- | --- | --- |
| `R001` | `API`, `STATE`, `AUDIT` | `POST /payments/{id}/approve`, `ApprovalAction`, approval-denial audit |
| `R002` | `API`, `STATE`, `AUDIT` | `POST /payments/{id}/release`, approval history, approver role snapshots |
| `R003` | `API`, `STATE`, `AUDIT` | `POST /payments/{id}/void`, payment status, `payment_voided` audit |
| `R004` | `API`, `STATE`, `AUDIT` | `POST /payments/{id}/approve` with inactive token fixture, unchanged payment state, no approval record |
| `R005` | `API`, `LOG` | `GET /payments/{id}/summary`, masked summary payload, access/request log |
| `R007` | `API`, `STATE`, `AUDIT` | `POST /payments/{id}/approve`, `POST /delegations` logical behavior within delegated-authority checks, delegation records |
| `R008` | `API`, `STATE` | `POST /payments/{id}/reverse`, settled payment state, incident ticket reference lookup |
| `R010` | `API`, `STATE`, `LOG` | `POST /internal-transfers`, mTLS subject allowlist check, transfer record presence/absence |
| `R011` | `LOG` | structured application logs emitted during payment and beneficiary flows |
| `R012` | `STATE`, `AUDIT` | all payment status-changing endpoints, `payment_status_changed` audit payload |
| `R013` | `LOG` | normal logs and exception logs from secret-backed code paths |
| `R014` | `API`, `AUDIT` | insufficient-permission approval denial and `approval_denied_security` event |
| `R016` | `API`, `AUDIT`, `STATE` | `GET /documents/{id}/download`, token store, `document_token_expired` audit |
| `R018` | `API`, `AUDIT`, `STATE` | `GET /reconciliation/reports/download`, report metadata, audit payload |
| `R019` | `API`, `LOG` | `POST /search/customer-email`, salted search log entry |
| `R020` | `API`, `AUDIT` | `GET /provider-config/{name}` allowed and denied reads, `provider_config_read` events |
| `R021` | `API`, `STATE` | `POST /payments` validation and payment-create persistence result |
| `R024` | `API`, `STATE` | `POST /payments` or `PATCH /payments/{id}` scheduled date validation |
| `R025` | `API`, `STATE` | `POST /payments/{id}/reject` and `POST /payments/{id}/approve` comment behavior |
| `R026` | `API`, `STATE` | `PUT /beneficiaries/{id}/bank-details`, beneficiary record update result |
| `R027` | `API`, `STATE` | `POST /payments/{id}/attachments`, attachment metadata persistence |
| `R028` | `API`, `STATE` | `POST /batch-payouts`, batch record and duplicate-reference validation |
| `R029` | `API`, `STATE` | `PUT /tenants/{tenant_id}/callback-config`, tenant allowlist fixtures |
| `R030` | `API`, `STATE` | `POST /payments/{id}/refunds`, captured amount, prior approved refunds |
| `R031` | `API`, `STATE` | `POST /payments/{id}/submit`, line items, beneficiary verification flag |
| `R032` | `API`, `STATE`, `AUDIT` | approval endpoint and payment-type policy driving `SUBMITTED -> APPROVED` transition |
| `R033` | `API`, `STATE` | `PATCH /payments/{id}` after `EXECUTED`, field-level before/after diff |
| `R034` | `API`, `STATE`, `AUDIT` | reject endpoint, status change, cleared `scheduled_execution_at` |
| `R036` | `API`, `STATE` | cancel endpoint for allowed and forbidden states, `409` conflict behavior |
| `R037` | `STATE`, `AUDIT`, `JOB` | delegated task store, `POST /control/delegations/expire-pending`, expiration event |
| `R038` | `API`, `STATE` | `POST /payments/{id}/chargebacks`, refund-create path while dispute is open |
| `R040` | `STATE`, `API` | refund approvals, `approved_refund_total`, payment status history |
| `R041` | `API`, `STATE` | `POST /payments` with same `Idempotency-Key` and same body |
| `R042` | `API`, `STATE` | `POST /payments` with same `Idempotency-Key` and different body |
| `R043` | `API`, `STATE`, `LOG` | approval `command_id` replay after timeout, approval history deduplication |
| `R044` | `STATE`, `AUDIT`, `SIM` | `POST /provider/messages/ledger-posting`, provider message receipts, `duplicate_ignored` event |
| `R045` | `JOB`, `SIM`, `AUDIT` | `POST /provider/webhook-deliveries`, attempt log, stop-after-success sequence |
| `R046` | `JOB`, `STATE`, `LOG` | export job store, crash marker, restart under same job ID, output-row set |
| `R047` | `JOB`, `STATE` | stale lock record, logical clock, successor takeover attempts |
| `R049` | `API`, `STATE`, `SIM` | `POST /reconciliation/imports`, checksum history, duplicate import outcome |
| `R051` | `API`, `LOG` | every endpoint response header and matching request log entry |
| `R053` | `STATE`, `METRIC`, `AUDIT` | payment submission timestamp, first terminal decision timestamp, `approval_latency_ms` record |
| `R054` | `JOB`, `AUDIT` | `POST /execution-jobs`, structured start and end events |
| `R055` | `API`, `AUDIT` | guardrail hook block path and emitted `GuardrailViolationRecord` |
| `R057` | `SIM`, `AUDIT`, `JOB` | provider retry circuit open/close interval state and alert events |
| `R058` | `API`, `AUDIT`, `STATE` | `POST /payments/{id}/manual-override`, reason field, audit entity reference |
| `R059` | `API`, `STATE`, `METRIC` | `POST /reconciliation/check`, mismatch metric and linked review case |
| `R060` | `JOB`, `AUDIT`, `STATE` | export completion event with requester, row count, duration, success flag |

## Exit Condition For Step 17

Step 17 is complete when human confirms every one of the 48 frozen requirements is exercisable using one or more documented surfaces above, with no requirement depending on undocumented behavior or external infrastructure.
