# REFERENCE_FREEZE

Status: APPROVED
Date prepared: 2026-08-29

Step 19 procedure checklist:
- [x] Ran reference test suite: `python3 -m unittest application.tests.reference_acceptance.test_reference_acceptance -v`
- [x] Manually inspected at least one requirement from each category
- [x] Inspected all observable effects for 12 multi-obligation requirements
- [x] Confirmed no violation variant exists inside `application/reference/`
- [x] Approved reference tree as freeze candidate for next phase

Suggested human inspection anchors:
- Category 1 authorization/access control: `R001` via approval path and `R005` via masked summary path
- Category 2 audit/logging/privacy: `R012` via payment status audit and `R019` via hashed email search log
- Category 3 input validation: `R021` via payment create validation and `R029` via callback allowlist validation
- Category 4 state/consistency: `R031` via submit preconditions and `R040` via refund-state transition behavior
- Category 5 idempotency/replay/reliability: `R041` via create replay and `R046` via export restart behavior
- Category 6 operations/guardrail/monitoring: `R054` via execution job events and `R059` via reconciliation mismatch review-case creation

Requirement-by-requirement findings:

R001 (auth/security - approval):
  PASS. service.py:487 checks approver role; service.py:491-493 blocks self-approval.
  Denied path calls _audit_permission_denial and raises 403 before any approval record is created.
  Test confirms 403 on non-approver attempt, audit event logged, 200 on valid approver.

R005 (auth/security - support_readonly masking):
  PASS. service.py:543 masks account number via _mask_account_number.
  service.py:544 sets routing_number to None for support_readonly role.
  service.py:546 filters confidential comments. Test asserts raw strings absent from response.

R012 (data-protection/logging - status change audit):
  PASS. service.py:852-856 _change_payment_status appends audit event with payment_id,
  old_status, new_status, actor_id, timestamp on every status change.
  Test confirms event fields present after cancel operation.

R019 (data-protection/logging - email hash):
  PASS. service.py:604 hashes email with sha256 and salt prefix "ic-sqits::".
  service.py:605 logs only email_hash field. Test confirms raw email string absent from logs.

R021 (validation/input - amount bounds):
  PASS. service.py:405 rejects amount <= 0 or > 100000 with 422 before creating payment.
  Idempotency key not stored on failure so no payment record created.
  Test confirms amount=0 → 422.

R029 (validation/input - callback URL):
  PASS. service.py:665-667 parses URL, rejects if scheme != "https" or hostname not in
  tenant allowlist. Test confirms http → 422, https+allowed → 200.

R031 (state-transition - DRAFT->SUBMITTED):
  PASS. service.py:452 single compound guard: status must be DRAFT, line_items must be
  non-empty, beneficiary must be verified. All three must hold. Test confirms no-line-item
  → 409, with line items + verified beneficiary → 200.

R040 (state-transition - refund):
  PASS. service.py:703-705: partial refund (total < captured) leaves status CAPTURED;
  full refund (total == captured) transitions to REFUNDED. Test confirms 40 partial → CAPTURED,
  60 remainder → REFUNDED.

R041 (reliability/idempotency - create payment):
  PASS. service.py:397-402 stores body hash with idempotency key, returns original payment_id
  on replay with same body. Different body → 409. Test confirms replay returns same payment_id,
  no duplicate record.

R046 (reliability/idempotency - export restart):
  PASS. service.py:760-774 _restart_export uses existing job_id, builds written_set,
  only appends rows not already written. Test confirms restart with 2 pre-written rows
  results in ["r1","r2","r3"] without duplication.

R054 (observability/audit - execution job events):
  PASS. service.py:803-806 emits execution_job_started and execution_job_ended events,
  each containing job_id, result, timestamp. Test confirms both event types in audit stream.

R059 (observability/audit - reconciliation mismatch):
  PASS. service.py:835-838 on mismatch=True: appends reconciliation_mismatch_count metric
  and creates review_case with batch_id link. Test confirms case linked to batch_id and
  metric present.

Violation variant check:
  application/reference/: __init__.py, service.py, .gitkeep, __pycache__/ only. No violation variant.
  application/tests/reference_acceptance/: __init__.py, test_reference_acceptance.py, __pycache__/ only. No violation variant.
  PASS. No intentionally broken or alternate-path implementation found.

Human sign-off:
- Name: Nitin Garg
- Date: 2026-08-29
- Approval note: I completed Step 19 human review, ran the reference tests, inspected the required requirement surfaces, confirmed no violation variant exists in application/reference, and approve audit/REFERENCE_FREEZE.md.

Approval effect:
- Step 19 complete
- `REFERENCE_FREEZE.md` status changed from `PENDING_HUMAN_APPROVAL` to `APPROVED`
