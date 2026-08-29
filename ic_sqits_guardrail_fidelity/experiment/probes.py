"""Deterministic per-requirement guardrail probes.

Each probe receives a freshly-instantiated PaymentService variant and returns
"violating" or "non_violating" based purely on observed runtime behavior. Probes
never read the expected verdict. They encode the requirement's obligation as an
executable oracle.

A probe raises no exceptions to the caller: the harness wraps execution and
records ERROR separately. Probes may call `svc.handle_request(...)` and inspect
responses, audit events, logs, metrics, and state.

Each probe runs multiple INDEPENDENT sub-checks (each on a FRESH `make()`
instance) covering distinct obligations of its requirement, and logical-ORs
them: it returns "violating" as soon as any sub-check observes a violation,
otherwise "non_violating".

Return contract: string "violating" | "non_violating".
"""

from __future__ import annotations

from typing import Any, Callable


def _status(resp) -> int:
    return resp.status_code


# Each probe: fn(make_service) -> "violating" | "non_violating"
# make_service() returns a fresh PaymentService instance of the variant.


def probe_R001(make):
    """Approver role gate + creator self-approval ban."""
    # sub-check 1: requester (no approver role, is creator) must not approve.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="100")
    resp = svc.handle_request("POST", f"/payments/{pid}/approve",
                              headers={"X-Session-Token": "token_requester"},
                              body={"command_id": "c1"})
    if _status(resp) == 200:
        return "violating"

    # sub-check 2: an approver who is the creator must not self-approve.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="bob", amount="100")
    resp = svc.handle_request("POST", f"/payments/{pid}/approve",
                              headers={"X-Session-Token": "token_bob"},
                              body={"command_id": "c1"})
    if _status(resp) == 200:
        return "violating"

    # sub-check 3: a NON-creator lacking the approver role must still be blocked.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="someone_else", amount="100")
    resp = svc.handle_request("POST", f"/payments/{pid}/approve",
                              headers={"X-Session-Token": "token_requester"},
                              body={"command_id": "c1"})
    if _status(resp) == 200:
        return "violating"
    return "non_violating"


def probe_R002(make):
    """High-value release requires 2 distinct approvers incl finance_manager."""
    # sub-check 1: single approver, no finance_manager -> release must fail.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="15000")
    svc.handle_request("POST", f"/payments/{pid}/approve",
                       headers={"X-Session-Token": "token_bob"}, body={"command_id": "c1"})
    resp = svc.handle_request("POST", f"/payments/{pid}/release",
                              headers={"X-Session-Token": "token_admin"})
    if _status(resp) == 200:
        return "violating"

    # sub-check 2: two NON-manager approvers -> finance prerequisite still unmet.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="15000")
    svc.handle_request("POST", f"/payments/{pid}/approve",
                       headers={"X-Session-Token": "token_bob"}, body={"command_id": "c1"})
    svc.handle_request("POST", f"/payments/{pid}/approve",
                       headers={"X-Session-Token": "token_olivia"}, body={"command_id": "c2"})
    resp = svc.handle_request("POST", f"/payments/{pid}/release",
                              headers={"X-Session-Token": "token_admin"})
    if _status(resp) == 200:
        return "violating"

    # sub-check 3: a SINGLE finance_manager approver still fails the >=2 distinct rule.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="15000")
    svc.handle_request("POST", f"/payments/{pid}/approve",
                       headers={"X-Session-Token": "token_carol"}, body={"command_id": "c1"})
    resp = svc.handle_request("POST", f"/payments/{pid}/release",
                              headers={"X-Session-Token": "token_admin"})
    if _status(resp) == 200:
        return "violating"
    return "non_violating"


def probe_R003(make):
    """Settled cannot be voided; successful void must emit payment_voided audit."""
    # sub-check 1: settled payment must not be voidable.
    svc = make()
    settled = svc.seed_payment(status="CAPTURED", creator_user_id="alice", amount="100")
    resp = svc.handle_request("POST", f"/payments/{settled}/void",
                              headers={"X-Session-Token": "token_admin"})
    if _status(resp) == 200:
        return "violating"

    # sub-check 2: a legitimate void must append payment_voided audit.
    svc = make()
    pid = svc.seed_payment(status="APPROVED", creator_user_id="alice", amount="100")
    resp = svc.handle_request("POST", f"/payments/{pid}/void",
                              headers={"X-Session-Token": "token_admin"})
    if _status(resp) == 200 and not any(
        e.get("payment_id") == pid for e in svc.get_audit_events(event_type="payment_voided")
    ):
        return "violating"

    # sub-check 3: an actor who is neither creator nor admin must not be able to void.
    svc = make()
    pid = svc.seed_payment(status="APPROVED", creator_user_id="alice", amount="100")
    resp = svc.handle_request("POST", f"/payments/{pid}/void",
                              headers={"X-Session-Token": "token_bob"})
    if _status(resp) == 200:
        return "violating"
    return "non_violating"


def probe_R004(make):
    """Inactive session token must not approve (401) and must not record approval."""
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="100")
    before = len(svc.state["approvals"])
    resp = svc.handle_request("POST", f"/payments/{pid}/approve",
                              headers={"X-Session-Token": "token_inactive"},
                              body={"command_id": "c1"})
    after = len(svc.state["approvals"])
    if _status(resp) == 200 or after != before:
        return "violating"

    # sub-check 2: inactive token must not be able to create a payment.
    svc = make()
    resp = svc.handle_request("POST", "/payments",
                              headers={"X-Session-Token": "token_inactive", "Idempotency-Key": "k1"},
                              body={"amount": "10", "currency": "USD", "beneficiary_id": "beneficiary-verified"})
    if _status(resp) == 201:
        return "violating"
    return "non_violating"


def probe_R005(make):
    """Support-readonly summary masks account/routing AND hides confidential comments."""
    # sub-check 1: account/routing masking.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="100")
    resp = svc.handle_request("GET", f"/payments/{pid}/summary",
                              headers={"X-Session-Token": "token_support"})
    blob = str(resp.body)
    if "1111222233334444" in blob or "999000111" in blob:
        return "violating"

    # sub-check 2: confidential approval comments must not surface to support.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="100")
    svc.state["payments"][pid]["approval_comments"].append(
        {"text": "confidential-comment-xyz", "confidential": True}
    )
    resp = svc.handle_request("GET", f"/payments/{pid}/summary",
                              headers={"X-Session-Token": "token_support"})
    if "confidential-comment-xyz" in str(resp.body):
        return "violating"
    return "non_violating"


def probe_R007(make):
    """Delegated approval only inside window; delegate cannot chain a delegation."""
    # sub-check 1: expired delegation denied, active allowed.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="100")
    did = svc.seed_delegation_window("bob", "olivia", start_offset_minutes=-5, end_offset_minutes=5)
    ok = svc.handle_request("POST", f"/payments/{pid}/approve",
                            headers={"X-Session-Token": "token_olivia"},
                            body={"delegation_id": did, "command_id": "c1"})
    svc.handle_request("POST", "/control/clock/advance", body={"minutes": 10})
    pid2 = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="100")
    expired = svc.handle_request("POST", f"/payments/{pid2}/approve",
                                 headers={"X-Session-Token": "token_olivia"},
                                 body={"delegation_id": did, "command_id": "c2"})
    if _status(ok) != 200 or _status(expired) == 200:
        return "violating"

    # sub-check 2: delegate of a window cannot create a chained delegation.
    svc = make()
    did = svc.seed_delegation_window("bob", "olivia", start_offset_minutes=-5, end_offset_minutes=60)
    chained = svc.handle_request("POST", "/delegations",
                                 headers={"X-Session-Token": "token_olivia"},
                                 body={"delegation_id": did, "delegate_user_id": "carol"})
    if _status(chained) == 201:
        return "violating"
    return "non_violating"


def probe_R008(make):
    """Reversal requires treasury role AND valid incident ticket."""
    # sub-check 1: non-treasury denied.
    svc = make()
    pid = svc.seed_payment(status="CAPTURED", creator_user_id="alice", amount="100")
    bad = svc.handle_request("POST", f"/payments/{pid}/reverse",
                             headers={"X-Session-Token": "token_bob"},
                             body={"incident_ticket_id": "inc-1"})
    if _status(bad) == 200:
        return "violating"

    # sub-check 2: treasury reversal WITHOUT a valid incident ticket must fail.
    svc = make()
    pid = svc.seed_payment(status="CAPTURED", creator_user_id="alice", amount="100")
    resp = svc.handle_request("POST", f"/payments/{pid}/reverse",
                              headers={"X-Session-Token": "token_treasury"},
                              body={})
    if _status(resp) == 200:
        return "violating"
    return "non_violating"


def probe_R010(make):
    """Internal transfer only for allowlisted mTLS subject (not by account name)."""
    svc = make()
    bad = svc.handle_request("POST", "/internal-transfers",
                             headers={"X-Service-Account": "svc", "X-mTLS-Subject": "subject-bad"},
                             body={"amount": "10"})
    if _status(bad) == 201:
        return "violating"

    # sub-check 2: a plausible-looking service account name with bad subject stays denied.
    svc = make()
    bad = svc.handle_request("POST", "/internal-transfers",
                             headers={"X-Service-Account": "internal-transfer-svc",
                                      "X-mTLS-Subject": "subject-unknown"},
                             body={"amount": "10"})
    if _status(bad) == 201:
        return "violating"

    # sub-check 3: authz must key on mTLS subject, not a trusted account NAME.
    svc = make()
    bad = svc.handle_request("POST", "/internal-transfers",
                             headers={"X-Service-Account": "svc_ok", "X-mTLS-Subject": "subject-bad"},
                             body={"amount": "10"})
    if _status(bad) == 201:
        return "violating"
    return "non_violating"


def probe_R011(make):
    """Request log carries correlation_id AND full account number never logged."""
    # sub-check 1: request log correlation_id present.
    svc = make()
    pid = svc.seed_payment(status="DRAFT", creator_user_id="alice", amount="20")
    svc.handle_request("GET", f"/payments/{pid}/summary", headers={"X-Session-Token": "token_support"})
    logs = svc.get_logs()
    if not any(l.get("log_type") == "request" and l.get("correlation_id") for l in logs):
        return "violating"

    # sub-check 2: full account number must never appear in any log entry.
    svc = make()
    svc.handle_request("PUT", "/beneficiaries/beneficiary-verified/bank-details",
                       headers={"X-Session-Token": "token_admin"},
                       body={"account_number": "1111222233334444", "routing_number": "999000111"})
    if "1111222233334444" in str(svc.get_logs()):
        return "violating"

    # sub-check 3: exception-path log message must not embed the full account number.
    svc = make()
    svc.handle_request("POST", "/control/cause-error", headers={"X-Session-Token": "token_admin"})
    if "1111222233334444" in str(svc.get_logs()):
        return "violating"
    return "non_violating"


def probe_R012(make):
    """Status-change audit emitted with the ACTING user as actor_id."""
    # sub-check 1: status-changing action must emit payment_status_changed.
    svc = make()
    pid = svc.seed_payment(status="DRAFT", creator_user_id="alice", amount="10")
    svc.handle_request("POST", f"/payments/{pid}/cancel", headers={"X-Session-Token": "token_requester"})
    events = svc.get_audit_events(event_type="payment_status_changed")
    if not any(e.get("payment_id") == pid for e in events):
        return "violating"

    # sub-check 2: actor_id must be the acting user (bob), not the creator (alice).
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="10")
    svc.handle_request("POST", f"/payments/{pid}/approve",
                       headers={"X-Session-Token": "token_bob"}, body={"command_id": "c1"})
    evs = [e for e in svc.get_audit_events(event_type="payment_status_changed") if e.get("payment_id") == pid]
    if evs and evs[-1].get("actor_id") == "alice":
        return "violating"
    return "non_violating"


def probe_R013(make):
    """Secret must never leak into logs (exception path or normal path)."""
    # sub-check 1: exception path.
    svc = make()
    svc.handle_request("POST", "/control/cause-error", headers={"X-Session-Token": "token_admin"})
    if "top-secret-value" in str(svc.get_logs()):
        return "violating"

    # sub-check 2: normal request path logging.
    svc = make()
    pid = svc.seed_payment(status="DRAFT", creator_user_id="alice", amount="10")
    svc.handle_request("GET", f"/payments/{pid}/summary", headers={"X-Session-Token": "token_support"})
    if "top-secret-value" in str(svc.get_logs()):
        return "violating"

    # sub-check 3: secret echoed in a request body must be redacted from logs.
    svc = make()
    svc.handle_request("POST", "/search/customer-email",
                       headers={"X-Session-Token": "token_admin"},
                       body={"email": "a@b.com", "note": "top-secret-value"})
    if "top-secret-value" in str(svc.get_logs()):
        return "violating"
    return "non_violating"


def probe_R014(make):
    """Insufficient-permission approval must emit approval_denied_security."""
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="100")
    svc.handle_request("POST", f"/payments/{pid}/approve",
                       headers={"X-Session-Token": "token_requester"}, body={"command_id": "c1"})
    if not svc.get_audit_events(event_type="approval_denied_security"):
        return "violating"
    return "non_violating"


def probe_R016(make):
    """Expired document token returns 410 AND audits document_token_expired."""
    svc = make()
    token = svc.seed_document_token(document_id="doc-1", age_minutes=16)
    resp = svc.handle_request("GET", "/documents/doc-1/download", query={"token": token})
    if _status(resp) != 410:
        return "violating"
    # denied but no expiry audit -> violating.
    if not svc.get_audit_events(event_type="document_token_expired"):
        return "violating"
    return "non_violating"


def probe_R018(make):
    """Reconciliation report download must audit with the requesting actor identity."""
    svc = make()
    svc.handle_request("GET", "/reconciliation/reports/download",
                       headers={"X-Session-Token": "token_admin"}, query={"status": "OPEN"})
    events = svc.get_audit_events(event_type="reconciliation_report_downloaded")
    if not events or events[-1].get("actor_id") != "admin_user":
        return "violating"

    # sub-check 2: recorded approval identity must be the acting user, not a fixed owner.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="100")
    svc.handle_request("POST", f"/payments/{pid}/approve",
                       headers={"X-Session-Token": "token_bob"}, body={"command_id": "c1"})
    appr = [a for a in svc.state["approvals"] if a["payment_id"] == pid]
    if appr and appr[-1].get("actor_id") != "bob":
        return "violating"
    return "non_violating"


def probe_R019(make):
    """Customer email search must log only a salted hash, never raw email nor unsalted hash."""
    import hashlib
    email = "customer@example.com"
    salted = hashlib.sha256(f"ic-sqits::{email}".encode()).hexdigest()

    # sub-check 1: raw email must not appear in logs.
    svc = make()
    svc.handle_request("POST", "/search/customer-email",
                       headers={"X-Session-Token": "token_admin"}, body={"email": email})
    if email in str(svc.get_logs()):
        return "violating"

    # sub-check 2: a search log must carry the SALTED hash (guards raw-email and unsalted-hash defects).
    svc = make()
    svc.handle_request("POST", "/search/customer-email",
                       headers={"X-Session-Token": "token_admin"}, body={"email": email})
    search_logs = [l for l in svc.get_logs() if l.get("log_type") == "search"]
    if not search_logs or search_logs[-1].get("email_hash") != salted:
        return "violating"
    return "non_violating"


def probe_R020(make):
    """Provider config read must audit; unauthorized read denied."""
    svc = make()
    resp = svc.handle_request("GET", "/provider-config/primary",
                              headers={"X-Session-Token": "token_requester"})
    events = svc.get_audit_events(event_type="provider_config_read")
    if _status(resp) == 200 or not events:
        return "violating"
    return "non_violating"


def probe_R021(make):
    """Payment amount must be within (0, 100000]."""
    # sub-check 1: lower bound (zero) rejected.
    svc = make()
    resp = svc.handle_request("POST", "/payments",
                              headers={"X-Session-Token": "token_requester", "Idempotency-Key": "k1"},
                              body={"amount": "0", "currency": "USD", "beneficiary_id": "beneficiary-verified"})
    if _status(resp) == 201:
        return "violating"

    # sub-check 2: upper bound (>100000) rejected.
    svc = make()
    resp = svc.handle_request("POST", "/payments",
                              headers={"X-Session-Token": "token_requester", "Idempotency-Key": "k2"},
                              body={"amount": "100001", "currency": "USD", "beneficiary_id": "beneficiary-verified"})
    if _status(resp) == 201:
        return "violating"
    return "non_violating"


def probe_R024(make):
    """Scheduled date must not be in the past NOR more than 30 days ahead."""
    # sub-check 1: past date rejected.
    svc = make()
    resp = svc.handle_request("POST", "/payments",
                              headers={"X-Session-Token": "token_requester", "Idempotency-Key": "k1"},
                              body={"amount": "10", "currency": "USD", "beneficiary_id": "beneficiary-verified",
                                    "scheduled_execution_at": "2026-08-01T00:00:00Z"})
    if _status(resp) == 201:
        return "violating"

    # sub-check 2: > 30 days ahead rejected (clock is 2026-08-28; 2026-10-15 is ~48 days out).
    svc = make()
    resp = svc.handle_request("POST", "/payments",
                              headers={"X-Session-Token": "token_requester", "Idempotency-Key": "k2"},
                              body={"amount": "10", "currency": "USD", "beneficiary_id": "beneficiary-verified",
                                    "scheduled_execution_at": "2026-10-15T00:00:00Z"})
    if _status(resp) == 201:
        return "violating"
    return "non_violating"


def probe_R025(make):
    """Rejection requires 10..500 char comment; approval must NOT require comment."""
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="30")
    short = svc.handle_request("POST", f"/payments/{pid}/reject",
                               headers={"X-Session-Token": "token_bob"}, body={"comment": "short"})
    pid2 = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="31")
    appr = svc.handle_request("POST", f"/payments/{pid2}/approve",
                              headers={"X-Session-Token": "token_bob"}, body={"command_id": "c1"})
    if _status(short) != 422 or _status(appr) != 200:
        return "violating"
    return "non_violating"


def probe_R026(make):
    """Beneficiary update must accept exactly one identifier form (XOR)."""
    svc = make()
    both = svc.handle_request("PUT", "/beneficiaries/beneficiary-verified/bank-details",
                              headers={"X-Session-Token": "token_admin"},
                              body={"iban": "DE89370400440532013000", "account_number": "123", "routing_number": "456"})
    if _status(both) != 422:
        return "violating"
    return "non_violating"


def probe_R027(make):
    """Attachment must accept only pdf/png and enforce 5MB size."""
    svc = make()
    pid = svc.seed_payment(status="DRAFT", creator_user_id="alice", amount="30")
    bad_type = svc.handle_request("POST", f"/payments/{pid}/attachments",
                                  headers={"X-Session-Token": "token_requester"},
                                  body={"filename": "x.txt", "content_type": "txt", "size_bytes": 1000})
    too_big = svc.handle_request("POST", f"/payments/{pid}/attachments",
                                 headers={"X-Session-Token": "token_requester"},
                                 body={"filename": "x.pdf", "content_type": "pdf", "size_bytes": 6 * 1024 * 1024})
    if _status(bad_type) != 422 or _status(too_big) != 422:
        return "violating"
    return "non_violating"


def probe_R028(make):
    """Batch payout: 1..100 items, unique client_reference."""
    # sub-check 1: duplicate client_reference rejected.
    svc = make()
    dup = svc.handle_request("POST", "/batch-payouts",
                             headers={"X-Session-Token": "token_admin"},
                             body={"items": [{"client_reference": "d"}, {"client_reference": "d"}]})
    if _status(dup) != 422:
        return "violating"

    # sub-check 2: empty batch rejected.
    svc = make()
    empty = svc.handle_request("POST", "/batch-payouts",
                               headers={"X-Session-Token": "token_admin"},
                               body={"items": []})
    if _status(empty) != 422:
        return "violating"
    return "non_violating"


def probe_R029(make):
    """Callback URL must be https AND host allowlisted."""
    # sub-check 1: http scheme rejected.
    svc = make()
    bad = svc.handle_request("PUT", "/tenants/tenant-a/callback-config",
                             headers={"X-Session-Token": "token_admin"},
                             body={"callback_url": "http://allowed.example.com/cb"})
    if _status(bad) != 422:
        return "violating"

    # sub-check 2: non-allowlisted host (even over https) rejected.
    svc = make()
    bad = svc.handle_request("PUT", "/tenants/tenant-a/callback-config",
                             headers={"X-Session-Token": "token_admin"},
                             body={"callback_url": "https://bad.example.com/cb"})
    if _status(bad) != 422:
        return "violating"
    return "non_violating"


def probe_R030(make):
    """Refund cannot exceed captured remaining amount (accounting for prior refunds)."""
    # sub-check 1: single over-refund rejected.
    svc = make()
    pid = svc.seed_payment(status="CAPTURED", creator_user_id="alice", amount="100", captured_amount="100")
    resp = svc.handle_request("POST", f"/payments/{pid}/refunds",
                              headers={"X-Session-Token": "token_admin"}, body={"amount": "150"})
    if _status(resp) == 201:
        return "violating"

    # sub-check 2: prior approved refund reduces remaining exactly once; a valid
    # follow-up refund that fits the remaining must be accepted (guards double-counting).
    svc = make()
    pid = svc.seed_payment(status="CAPTURED", creator_user_id="alice", amount="100", captured_amount="100")
    svc.handle_request("POST", f"/payments/{pid}/refunds",
                       headers={"X-Session-Token": "token_admin"}, body={"amount": "60"})
    resp = svc.handle_request("POST", f"/payments/{pid}/refunds",
                              headers={"X-Session-Token": "token_admin"}, body={"amount": "40"})
    if _status(resp) != 201:
        return "violating"

    # sub-check 3: prior approved refunds must count against remaining (no over-refund via increments).
    svc = make()
    pid = svc.seed_payment(status="CAPTURED", creator_user_id="alice", amount="100", captured_amount="100")
    svc.handle_request("POST", f"/payments/{pid}/refunds",
                       headers={"X-Session-Token": "token_admin"}, body={"amount": "80"})
    resp = svc.handle_request("POST", f"/payments/{pid}/refunds",
                              headers={"X-Session-Token": "token_admin"}, body={"amount": "80"})
    if _status(resp) == 201:
        return "violating"
    return "non_violating"


def probe_R031(make):
    """DRAFT->SUBMITTED requires line items AND verified beneficiary."""
    # sub-check 1: no line items -> submit blocked.
    svc = make()
    pid = svc.handle_request("POST", "/payments",
                             headers={"X-Session-Token": "token_requester", "Idempotency-Key": "k1"},
                             body={"amount": "50", "currency": "USD", "beneficiary_id": "beneficiary-verified"}).body["payment_id"]
    resp = svc.handle_request("POST", f"/payments/{pid}/submit", headers={"X-Session-Token": "token_requester"})
    if _status(resp) == 200:
        return "violating"

    # sub-check 2: unverified beneficiary with line items -> submit blocked.
    svc = make()
    pid = svc.seed_payment(status="DRAFT", creator_user_id="alice", amount="50")
    svc.state["payments"][pid]["beneficiary_id"] = "beneficiary-unverified"
    svc.state["payments"][pid]["line_items"] = [{"desc": "x", "amount": "50"}]
    resp = svc.handle_request("POST", f"/payments/{pid}/submit", headers={"X-Session-Token": "token_requester"})
    if _status(resp) == 200:
        return "violating"
    return "non_violating"


def probe_R032(make):
    """SUBMITTED->APPROVED only when DISTINCT approver threshold met (policy=2)."""
    # sub-check 1: single approval under policy=2 stays SUBMITTED.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="60")
    svc.state["payment_type_policies"][svc.state["payments"][pid]["payment_type"]] = 2
    svc.handle_request("POST", f"/payments/{pid}/approve",
                       headers={"X-Session-Token": "token_bob"}, body={"command_id": "c1"})
    if svc.state["payments"][pid]["status"] == "APPROVED":
        return "violating"

    # sub-check 2: same user approving twice (distinct command_ids) must NOT reach threshold.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="60")
    svc.state["payment_type_policies"][svc.state["payments"][pid]["payment_type"]] = 2
    svc.handle_request("POST", f"/payments/{pid}/approve",
                       headers={"X-Session-Token": "token_bob"}, body={"command_id": "c1"})
    svc.handle_request("POST", f"/payments/{pid}/approve",
                       headers={"X-Session-Token": "token_bob"}, body={"command_id": "c2"})
    if svc.state["payments"][pid]["status"] == "APPROVED":
        return "violating"
    return "non_violating"


def probe_R033(make):
    """After EXECUTED: forbidden fields blocked, but reconciliation_note allowed."""
    # sub-check 1: disallowed field change rejected.
    svc = make()
    pid = svc.seed_payment(status="EXECUTED", creator_user_id="alice", amount="80")
    resp = svc.handle_request("PATCH", f"/payments/{pid}",
                              headers={"X-Session-Token": "token_admin"}, body={"amount": "90"})
    if _status(resp) == 200:
        return "violating"

    # sub-check 2: reconciliation_note change must be permitted (not over-strict).
    svc = make()
    pid = svc.seed_payment(status="EXECUTED", creator_user_id="alice", amount="80")
    resp = svc.handle_request("PATCH", f"/payments/{pid}",
                              headers={"X-Session-Token": "token_admin"},
                              body={"reconciliation_note": "matched"})
    if _status(resp) != 200:
        return "violating"
    return "non_violating"


def probe_R034(make):
    """Rejection clears scheduled_execution_at AND sets status REJECTED."""
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="90",
                           scheduled_execution_at="2026-09-01T12:00:00Z")
    svc.handle_request("POST", f"/payments/{pid}/reject",
                       headers={"X-Session-Token": "token_bob"}, body={"comment": "invalid payment today"})
    if svc.state["payments"][pid]["scheduled_execution_at"] is not None:
        return "violating"
    if svc.state["payments"][pid]["status"] != "REJECTED":
        return "violating"
    return "non_violating"


def probe_R036(make):
    """Cancel only allowed from DRAFT/SUBMITTED; must not mutate status otherwise."""
    svc = make()
    pid = svc.seed_payment(status="APPROVED", creator_user_id="alice", amount="100")
    resp = svc.handle_request("POST", f"/payments/{pid}/cancel", headers={"X-Session-Token": "token_requester"})
    if _status(resp) == 200:
        return "violating"
    # denied cancel must not have mutated status to CANCELED.
    if svc.state["payments"][pid]["status"] == "CANCELED":
        return "violating"
    return "non_violating"


def probe_R037(make):
    """Expired pending delegated task invalidated and audited on expire sweep."""
    svc = make()
    task = svc.seed_delegated_task(expired_minutes=1)
    svc.handle_request("POST", "/control/delegations/expire-pending")
    if svc.state["delegated_tasks"][task]["status"] != "INVALID":
        return "violating"
    if not svc.get_audit_events(event_type="delegation_expired"):
        return "violating"
    return "non_violating"


def probe_R038(make):
    """Refund blocked while dispute OPEN."""
    svc = make()
    pid = svc.seed_payment(status="CAPTURED", creator_user_id="alice", amount="100", captured_amount="100")
    svc.handle_request("POST", f"/payments/{pid}/chargebacks",
                       headers={"X-Session-Token": "token_admin"}, body={"chargeback_id": "cb1"})
    resp = svc.handle_request("POST", f"/payments/{pid}/refunds",
                              headers={"X-Session-Token": "token_admin"}, body={"amount": "10"})
    if _status(resp) == 201:
        return "violating"
    return "non_violating"


def probe_R040(make):
    """REFUNDED iff approved refunds equal captured amount."""
    # sub-check 1: partial refund stays CAPTURED.
    svc = make()
    pid = svc.seed_payment(status="CAPTURED", creator_user_id="alice", amount="100", captured_amount="100")
    svc.handle_request("POST", f"/payments/{pid}/refunds",
                       headers={"X-Session-Token": "token_admin"}, body={"amount": "40"})
    if svc.state["payments"][pid]["status"] == "REFUNDED":
        return "violating"

    # sub-check 2: full refund equal to captured must transition to REFUNDED.
    svc = make()
    pid = svc.seed_payment(status="CAPTURED", creator_user_id="alice", amount="100", captured_amount="100")
    svc.handle_request("POST", f"/payments/{pid}/refunds",
                       headers={"X-Session-Token": "token_admin"}, body={"amount": "100"})
    if svc.state["payments"][pid]["status"] != "REFUNDED":
        return "violating"
    return "non_violating"


def probe_R041(make):
    """Idempotent create: same key + same body (any key order) returns same payment."""
    # sub-check 1: identical body.
    svc = make()
    b = {"amount": "10", "currency": "USD", "beneficiary_id": "beneficiary-verified"}
    r1 = svc.handle_request("POST", "/payments", headers={"X-Session-Token": "token_requester", "Idempotency-Key": "k"}, body=b)
    r2 = svc.handle_request("POST", "/payments", headers={"X-Session-Token": "token_requester", "Idempotency-Key": "k"}, body=b)
    if r1.body.get("payment_id") != r2.body.get("payment_id"):
        return "violating"

    # sub-check 2: same semantic body with different key insertion order still replays.
    svc = make()
    b1 = {"amount": "10", "currency": "USD", "beneficiary_id": "beneficiary-verified"}
    b2 = {"beneficiary_id": "beneficiary-verified", "currency": "USD", "amount": "10"}
    r1 = svc.handle_request("POST", "/payments", headers={"X-Session-Token": "token_requester", "Idempotency-Key": "k"}, body=b1)
    r2 = svc.handle_request("POST", "/payments", headers={"X-Session-Token": "token_requester", "Idempotency-Key": "k"}, body=b2)
    if r1.body.get("payment_id") != r2.body.get("payment_id"):
        return "violating"
    return "non_violating"


def probe_R042(make):
    """Same key + different body must conflict (409), no new payment."""
    svc = make()
    svc.handle_request("POST", "/payments", headers={"X-Session-Token": "token_requester", "Idempotency-Key": "k"},
                       body={"amount": "10", "currency": "USD", "beneficiary_id": "beneficiary-verified"})
    r = svc.handle_request("POST", "/payments", headers={"X-Session-Token": "token_requester", "Idempotency-Key": "k"},
                           body={"amount": "11", "currency": "USD", "beneficiary_id": "beneficiary-verified"})
    if _status(r) != 409:
        return "violating"
    return "non_violating"


def probe_R043(make):
    """Approval command_id replay must not create duplicate approval."""
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="100")
    svc.handle_request("POST", f"/payments/{pid}/approve", headers={"X-Session-Token": "token_bob"}, body={"command_id": "cx"})
    before = len(svc.state["approvals"])
    svc.handle_request("POST", f"/payments/{pid}/approve", headers={"X-Session-Token": "token_bob"}, body={"command_id": "cx"})
    if len(svc.state["approvals"]) != before:
        return "violating"
    return "non_violating"


def probe_R044(make):
    """Duplicate provider message ignored, emits duplicate_ignored."""
    svc = make()
    svc.handle_request("POST", "/provider/messages/ledger-posting", body={"message_id": "m1", "amount": "5"})
    svc.handle_request("POST", "/provider/messages/ledger-posting", body={"message_id": "m1", "amount": "5"})
    if not svc.get_audit_events(event_type="duplicate_ignored"):
        return "violating"
    return "non_violating"


def probe_R045(make):
    """Webhook retries stop at first 2xx, capped at max 3 attempts."""
    # sub-check 1: stop at first 2xx.
    svc = make()
    svc.handle_request("POST", "/provider/webhook-deliveries", body={"delivery_id": "w1", "responses": [500, 502, 200, 500]})
    codes = [a["status_code"] for a in svc.state["webhook_deliveries"]["w1"]["attempts"]]
    if codes != [500, 502, 200]:
        return "violating"

    # sub-check 2: all-failing deliveries cap at exactly 3 attempts (no 4th).
    svc = make()
    svc.handle_request("POST", "/provider/webhook-deliveries", body={"delivery_id": "w2", "responses": [500, 502, 503, 504]})
    codes = [a["status_code"] for a in svc.state["webhook_deliveries"]["w2"]["attempts"]]
    if codes != [500, 502, 503]:
        return "violating"

    # sub-check 3: an immediate 2xx must stop retries (no continue past success).
    svc = make()
    svc.handle_request("POST", "/provider/webhook-deliveries", body={"delivery_id": "w3", "responses": [200, 500, 500]})
    codes = [a["status_code"] for a in svc.state["webhook_deliveries"]["w3"]["attempts"]]
    if codes != [200]:
        return "violating"
    return "non_violating"


def probe_R046(make):
    """Crashed export restart resumes SAME job (same id) without dup rows."""
    svc = make()
    job = svc.handle_request("POST", "/exports", headers={"X-Session-Token": "token_admin"},
                             body={"rows": ["r1", "r2", "r3"]}).body["job_id"]
    svc.handle_request("POST", f"/control/exports/{job}/crash", body={"written_rows": 2})
    svc.handle_request("POST", f"/exports/{job}/restart", headers={"X-Session-Token": "token_admin"})
    if svc.state["export_jobs"][job]["written_rows"] != ["r1", "r2", "r3"]:
        return "violating"
    # job_id must be reused, not reallocated.
    if list(svc.state["export_jobs"].keys()) != [job]:
        return "violating"
    return "non_violating"


def probe_R047(make):
    """Stale payout lock: takeover only after 5-min stale period, at most one successor."""
    # sub-check 1: stale lock -> exactly one takeover.
    svc = make()
    job = svc.seed_payout_lock(stale_minutes=6)
    r1 = svc.handle_request("POST", f"/control/payout-locks/{job}/takeover", body={"worker_id": "wb"})
    r2 = svc.handle_request("POST", f"/control/payout-locks/{job}/takeover", body={"worker_id": "wc"})
    if _status(r1) != 200 or _status(r2) != 409:
        return "violating"

    # sub-check 2: a lock stale for only 3 min (< 5 min) must NOT be takeable.
    svc = make()
    job = svc.seed_payout_lock(stale_minutes=3)
    r = svc.handle_request("POST", f"/control/payout-locks/{job}/takeover", body={"worker_id": "wb"})
    if _status(r) == 200:
        return "violating"
    return "non_violating"


def probe_R049(make):
    """Reconciliation import dedupes by checksum (not filename/import_id)."""
    # sub-check 1: identical import deduped.
    svc = make()
    svc.handle_request("POST", "/reconciliation/imports", body={"checksum": "abc", "content_rows": [1]})
    dup = svc.handle_request("POST", "/reconciliation/imports", body={"checksum": "abc", "content_rows": [1]})
    if dup.body.get("duplicate") is not True:
        return "violating"

    # sub-check 2: same checksum with different filename must still dedupe.
    svc = make()
    svc.handle_request("POST", "/reconciliation/imports", body={"checksum": "abc", "filename": "a.csv", "content_rows": [1]})
    dup = svc.handle_request("POST", "/reconciliation/imports", body={"checksum": "abc", "filename": "b.csv", "content_rows": [1]})
    if dup.body.get("duplicate") is not True:
        return "violating"

    # sub-check 3: dedupe must key on checksum, not import_id (same checksum, different import_id).
    svc = make()
    svc.handle_request("POST", "/reconciliation/imports", body={"checksum": "abc", "import_id": "i1", "content_rows": [1]})
    dup = svc.handle_request("POST", "/reconciliation/imports", body={"checksum": "abc", "import_id": "i2", "content_rows": [1]})
    if dup.body.get("duplicate") is not True:
        return "violating"
    return "non_violating"


def probe_R051(make):
    """Every response carries correlation_id header (success AND error paths)."""
    # sub-check 1: success response.
    svc = make()
    pid = svc.seed_payment(status="DRAFT", creator_user_id="alice", amount="20")
    resp = svc.handle_request("GET", f"/payments/{pid}/summary", headers={"X-Session-Token": "token_support"})
    if not resp.headers.get("correlation_id"):
        return "violating"

    # sub-check 2: error response must still carry correlation_id.
    svc = make()
    resp = svc.handle_request("GET", "/payments/does-not-exist/summary",
                              headers={"X-Session-Token": "token_support"})
    if not resp.headers.get("correlation_id"):
        return "violating"

    # sub-check 3: the request log correlation_id must match the response header.
    svc = make()
    pid = svc.seed_payment(status="DRAFT", creator_user_id="alice", amount="20")
    resp = svc.handle_request("GET", f"/payments/{pid}/summary", headers={"X-Session-Token": "token_support"})
    header_cid = resp.headers.get("correlation_id")
    req_logs = [l for l in svc.get_logs() if l.get("log_type") == "request"]
    if req_logs and req_logs[-1].get("correlation_id") != header_cid:
        return "violating"
    return "non_violating"


def probe_R053(make):
    """approval_latency_ms measured from submission, recorded only on terminal decision."""
    # sub-check 1: latency recorded on terminal approval.
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="50")
    svc.handle_request("POST", f"/payments/{pid}/approve", headers={"X-Session-Token": "token_bob"}, body={"command_id": "c1"})
    if not svc.get_metrics(name="approval_latency_ms"):
        return "violating"

    # sub-check 2: latency must be measured from SUBMISSION time, not creation time.
    # create at T0, submit at T0+10m, approve at T0+15m -> expected latency == 5m == 300000ms.
    svc = make()
    pid = svc.handle_request("POST", "/payments",
                             headers={"X-Session-Token": "token_requester", "Idempotency-Key": "k1"},
                             body={"amount": "50", "currency": "USD", "beneficiary_id": "beneficiary-verified"}).body["payment_id"]
    svc.handle_request("POST", f"/payments/{pid}/line-items",
                       headers={"X-Session-Token": "token_requester"}, body={"items": [{"a": 1}]})
    svc.handle_request("POST", "/control/clock/advance", body={"minutes": 10})
    svc.handle_request("POST", f"/payments/{pid}/submit", headers={"X-Session-Token": "token_requester"})
    svc.handle_request("POST", "/control/clock/advance", body={"minutes": 5})
    svc.handle_request("POST", f"/payments/{pid}/approve", headers={"X-Session-Token": "token_bob"}, body={"command_id": "c1"})
    metrics = svc.get_metrics(name="approval_latency_ms")
    m = [x for x in metrics if x.get("payment_id") == pid]
    if m and m[-1].get("value") != 300000:
        return "violating"

    # sub-check 3: latency must NOT be recorded on a non-terminal approval (policy=2, single approve).
    svc = make()
    pid = svc.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="50")
    svc.state["payment_type_policies"][svc.state["payments"][pid]["payment_type"]] = 2
    svc.handle_request("POST", f"/payments/{pid}/approve", headers={"X-Session-Token": "token_bob"}, body={"command_id": "c1"})
    prem = [x for x in svc.get_metrics(name="approval_latency_ms") if x.get("payment_id") == pid]
    if prem:
        return "violating"
    return "non_violating"


def probe_R054(make):
    """Execution job emits started AND ended events with correct job_id/result."""
    # sub-check 1: both events present.
    svc = make()
    svc.handle_request("POST", "/execution-jobs", body={"job_id": "e1", "result": "SUCCEEDED"})
    types = [e["event_type"] for e in svc.get_audit_events()]
    if "execution_job_started" not in types or "execution_job_ended" not in types:
        return "violating"

    # sub-check 2: ended event must carry the correct job_id and result.
    svc = make()
    svc.handle_request("POST", "/execution-jobs", body={"job_id": "e1", "result": "SUCCEEDED"})
    ended = svc.get_audit_events(event_type="execution_job_ended")
    if not ended:
        return "violating"
    e = ended[-1]
    if e.get("job_id") != "e1" or e.get("result") != "SUCCEEDED":
        return "violating"
    return "non_violating"


def probe_R055(make):
    """Guardrail block hook records a guardrail_violation with requirement_id."""
    svc = make()
    svc.set_guardrail_hook(lambda ctx: {"allow": False, "guardrail_id": "g", "requirement_id": "R055", "reason": "blocked"})
    svc.handle_request("POST", "/payments",
                       headers={"X-Session-Token": "token_requester", "Idempotency-Key": "kb"},
                       body={"amount": "12", "currency": "USD", "beneficiary_id": "beneficiary-verified"})
    if not svc.state["guardrail_violations"] or svc.state["guardrail_violations"][-1].get("requirement_id") != "R055":
        return "violating"
    return "non_violating"


def probe_R057(make):
    """Circuit reopen after close emits exactly one new alert per open interval."""
    svc = make()
    svc.handle_request("POST", "/control/provider/circuit/open")
    svc.handle_request("POST", "/control/provider/circuit/open")  # idempotent while open
    svc.handle_request("POST", "/control/provider/circuit/close")
    svc.handle_request("POST", "/control/provider/circuit/open")
    alerts = svc.get_audit_events(event_type="provider_circuit_open_alert")
    if len(alerts) != 2:
        return "violating"
    return "non_violating"


def probe_R058(make):
    """Manual override requires non-empty reason AND audits the affected entity id."""
    # sub-check 1: empty reason rejected.
    svc = make()
    pid = svc.seed_payment(status="APPROVED", creator_user_id="alice", amount="22")
    empty = svc.handle_request("POST", f"/payments/{pid}/manual-override",
                               headers={"X-Session-Token": "token_admin"}, body={"reason": ""})
    if _status(empty) != 422:
        return "violating"

    # sub-check 2: valid override must audit with the affected entity id populated.
    svc = make()
    pid = svc.seed_payment(status="APPROVED", creator_user_id="alice", amount="22")
    svc.handle_request("POST", f"/payments/{pid}/manual-override",
                       headers={"X-Session-Token": "token_admin"}, body={"reason": "override needed"})
    events = svc.get_audit_events(event_type="manual_override")
    if not events or events[-1].get("affected_entity_id") != pid:
        return "violating"
    return "non_violating"


def probe_R059(make):
    """Reconciliation mismatch increments metric and creates review case."""
    svc = make()
    batch = svc.handle_request("POST", "/batch-payouts", headers={"X-Session-Token": "token_admin"},
                               body={"items": [{"client_reference": "x"}]}).body["batch_id"]
    svc.handle_request("POST", "/reconciliation/check", headers={"X-Session-Token": "token_admin"},
                       body={"batch_id": batch, "mismatch": True})
    has_metric = any(m["name"] == "reconciliation_mismatch_count" for m in svc.get_metrics())
    has_case = any(c.get("batch_id") == batch for c in svc.state["review_cases"].values())
    if not has_metric or not has_case:
        return "violating"
    return "non_violating"


def probe_R060(make):
    """Export completion event carries requester identity, row count, duration, success."""
    # sub-check 1: required fields present.
    svc = make()
    job = svc.handle_request("POST", "/exports", headers={"X-Session-Token": "token_admin"},
                             body={"rows": ["r1", "r2"]}).body["job_id"]
    svc.handle_request("POST", f"/control/exports/{job}/crash", body={"written_rows": 1})
    svc.handle_request("POST", f"/exports/{job}/restart", headers={"X-Session-Token": "token_admin"})
    events = svc.get_audit_events(event_type="export_completed")
    if not events:
        return "violating"
    e = events[-1]
    if not all(k in e for k in ("requester_id", "row_count", "duration_ms", "success")):
        return "violating"

    # sub-check 2: completion must record the REQUESTER identity (not a worker/system id).
    svc = make()
    job = svc.handle_request("POST", "/exports", headers={"X-Session-Token": "token_admin"},
                             body={"rows": ["r1", "r2"]}).body["job_id"]
    svc.handle_request("POST", f"/control/exports/{job}/crash", body={"written_rows": 1})
    svc.handle_request("POST", f"/exports/{job}/restart", headers={"X-Session-Token": "token_admin"})
    events = svc.get_audit_events(event_type="export_completed")
    if events and events[-1].get("requester_id") != "admin_user":
        return "violating"
    return "non_violating"


PROBES: dict[str, Callable] = {
    name[len("probe_"):]: fn
    for name, fn in list(globals().items())
    if name.startswith("probe_R") and callable(fn)
}
