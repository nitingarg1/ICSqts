import tempfile
import unittest

from application.reference import PaymentService


def new_service():
    return PaymentService(storage_dir=tempfile.mkdtemp(prefix="ic-sqits-ref-"))


class ReferenceAcceptanceTests(unittest.TestCase):
    def test_authorization_and_release_rules(self):
        service = new_service()
        payment_id = service.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="15000")

        denied = service.handle_request(
            "POST",
            f"/payments/{payment_id}/approve",
            headers={"X-Session-Token": "token_requester"},
            body={"command_id": "cmd-1"},
        )
        self.assertEqual(403, denied.status_code)
        self.assertEqual("approval_denied_security", service.get_audit_events()[-1]["event_type"])

        approved_one = service.handle_request(
            "POST",
            f"/payments/{payment_id}/approve",
            headers={"X-Session-Token": "token_bob"},
            body={"command_id": "cmd-2"},
        )
        self.assertEqual(200, approved_one.status_code)

        release_denied = service.handle_request(
            "POST",
            f"/payments/{payment_id}/release",
            headers={"X-Session-Token": "token_admin"},
        )
        self.assertEqual(409, release_denied.status_code)

        approved_two = service.handle_request(
            "POST",
            f"/payments/{payment_id}/approve",
            headers={"X-Session-Token": "token_carol"},
            body={"command_id": "cmd-3"},
        )
        self.assertEqual(200, approved_two.status_code)
        released = service.handle_request(
            "POST",
            f"/payments/{payment_id}/release",
            headers={"X-Session-Token": "token_admin"},
        )
        self.assertEqual(200, released.status_code)

        inactive_before = len(service.state["approvals"])
        inactive = service.handle_request(
            "POST",
            f"/payments/{payment_id}/approve",
            headers={"X-Session-Token": "token_inactive"},
            body={"command_id": "cmd-4"},
        )
        self.assertEqual(401, inactive.status_code)
        self.assertEqual(inactive_before, len(service.state["approvals"]))

        void_payment_id = service.seed_payment(status="APPROVED", creator_user_id="alice", amount="25")
        voided = service.handle_request(
            "POST",
            f"/payments/{void_payment_id}/void",
            headers={"X-Session-Token": "token_admin"},
        )
        self.assertEqual(200, voided.status_code)
        self.assertEqual("VOIDED", service.state["payments"][void_payment_id]["status"])
        self.assertEqual("payment_voided", service.get_audit_events()[-1]["event_type"])

    def test_summary_delegation_and_reversal_rules(self):
        service = new_service()
        payment_id = service.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="50")
        service.state["payments"][payment_id]["approval_comments"] = [
            {"text": "hide this", "confidential": True},
            {"text": "show this", "confidential": False},
        ]

        summary = service.handle_request(
            "GET",
            f"/payments/{payment_id}/summary",
            headers={"X-Session-Token": "token_support"},
        )
        self.assertEqual(200, summary.status_code)
        self.assertNotIn("1111222233334444", str(summary.body))
        self.assertNotIn("999000111", str(summary.body))
        self.assertNotIn("hide this", str(summary.body))

        delegation_id = service.seed_delegation_window("bob", "olivia", start_offset_minutes=-5, end_offset_minutes=5)
        delegated = service.handle_request(
            "POST",
            f"/payments/{payment_id}/approve",
            headers={"X-Session-Token": "token_olivia"},
            body={"delegation_id": delegation_id, "command_id": "cmd-delegated"},
        )
        self.assertEqual(200, delegated.status_code)

        chained = service.handle_request(
            "POST",
            "/delegations",
            headers={"X-Session-Token": "token_olivia"},
            body={"delegation_id": delegation_id, "delegate_user_id": "erin"},
        )
        self.assertEqual(403, chained.status_code)

        service.handle_request("POST", "/control/clock/advance", body={"minutes": 10})
        expired = service.handle_request(
            "POST",
            f"/payments/{payment_id}/approve",
            headers={"X-Session-Token": "token_olivia"},
            body={"delegation_id": delegation_id, "command_id": "cmd-expired"},
        )
        self.assertEqual(403, expired.status_code)

        settled_payment_id = service.seed_payment(status="CAPTURED", creator_user_id="alice", amount="100")
        ok_reverse = service.handle_request(
            "POST",
            f"/payments/{settled_payment_id}/reverse",
            headers={"X-Session-Token": "token_treasury"},
            body={"incident_ticket_id": "inc-1"},
        )
        self.assertEqual(200, ok_reverse.status_code)

        bad_reverse = service.handle_request(
            "POST",
            f"/payments/{settled_payment_id}/reverse",
            headers={"X-Session-Token": "token_bob"},
            body={"incident_ticket_id": "missing"},
        )
        self.assertEqual(403, bad_reverse.status_code)

    def test_internal_transfer_and_log_safety(self):
        service = new_service()
        allowed = service.handle_request(
            "POST",
            "/internal-transfers",
            headers={"X-Service-Account": "svc_ok", "X-mTLS-Subject": "subject-ok"},
            body={"amount": "25.00"},
        )
        self.assertEqual(201, allowed.status_code)

        denied = service.handle_request(
            "POST",
            "/internal-transfers",
            headers={"X-Service-Account": "svc_bad", "X-mTLS-Subject": "subject-bad"},
            body={"amount": "25.00"},
        )
        self.assertEqual(403, denied.status_code)
        self.assertEqual(1, len(service.state["internal_transfers"]))

        payment_id = service.seed_payment(status="DRAFT", creator_user_id="alice", amount="20")
        service.handle_request(
            "GET",
            f"/payments/{payment_id}/summary",
            headers={"X-Session-Token": "token_support"},
        )
        log_blob = str(service.get_logs())
        self.assertNotIn("1111222233334444", log_blob)
        self.assertNotIn("top-secret-value", log_blob)
        self.assertIn("correlation_id", log_blob)

        failure = service.handle_request(
            "POST",
            "/control/cause-error",
            headers={"X-Session-Token": "token_admin"},
        )
        self.assertEqual(500, failure.status_code)
        self.assertNotIn("top-secret-value", str(service.get_logs()))

    def test_audit_document_report_search_and_provider_config(self):
        service = new_service()
        payment_id = service.seed_payment(status="DRAFT", creator_user_id="alice", amount="10")
        service.handle_request(
            "POST",
            f"/payments/{payment_id}/cancel",
            headers={"X-Session-Token": "token_requester"},
        )
        status_event = service.get_audit_events(event_type="payment_status_changed")[-1]
        self.assertEqual(payment_id, status_event["payment_id"])
        self.assertEqual("alice", status_event["actor_id"])

        token = service.seed_document_token(document_id="doc-1", age_minutes=16)
        expired = service.handle_request("GET", "/documents/doc-1/download", query={"token": token})
        self.assertEqual(410, expired.status_code)
        self.assertEqual("document_token_expired", service.get_audit_events()[-1]["event_type"])

        report = service.handle_request(
            "GET",
            "/reconciliation/reports/download",
            headers={"X-Session-Token": "token_admin"},
            query={"status": "OPEN"},
        )
        self.assertEqual(200, report.status_code)
        report_event = service.get_audit_events(event_type="reconciliation_report_downloaded")[-1]
        self.assertEqual("admin_user", report_event["actor_id"])
        self.assertEqual({"status": "OPEN"}, report_event["applied_filters"])

        search = service.handle_request(
            "POST",
            "/search/customer-email",
            headers={"X-Session-Token": "token_admin"},
            body={"email": "customer@example.com"},
        )
        self.assertEqual(200, search.status_code)
        self.assertNotIn("customer@example.com", str(service.get_logs()))

        config_ok = service.handle_request(
            "GET",
            "/provider-config/primary",
            headers={"X-Session-Token": "token_config"},
        )
        config_denied = service.handle_request(
            "GET",
            "/provider-config/primary",
            headers={"X-Session-Token": "token_requester"},
        )
        self.assertEqual(200, config_ok.status_code)
        self.assertEqual(403, config_denied.status_code)
        config_events = service.get_audit_events(event_type="provider_config_read")
        self.assertEqual({"allowed", "denied"}, {event["outcome"] for event in config_events})

    def test_create_payment_validation_schedule_and_idempotency(self):
        service = new_service()
        invalid_amount = service.handle_request(
            "POST",
            "/payments",
            headers={"X-Session-Token": "token_requester", "Idempotency-Key": "idem-1"},
            body={"amount": "0", "currency": "USD", "beneficiary_id": "beneficiary-verified"},
        )
        self.assertEqual(422, invalid_amount.status_code)

        invalid_schedule = service.handle_request(
            "POST",
            "/payments",
            headers={"X-Session-Token": "token_requester", "Idempotency-Key": "idem-2"},
            body={
                "amount": "10",
                "currency": "USD",
                "beneficiary_id": "beneficiary-verified",
                "scheduled_execution_at": "2026-08-01T00:00:00Z",
            },
        )
        self.assertEqual(422, invalid_schedule.status_code)

        created = service.handle_request(
            "POST",
            "/payments",
            headers={"X-Session-Token": "token_requester", "Idempotency-Key": "idem-3"},
            body={"amount": "10", "currency": "USD", "beneficiary_id": "beneficiary-verified"},
        )
        replay = service.handle_request(
            "POST",
            "/payments",
            headers={"X-Session-Token": "token_requester", "Idempotency-Key": "idem-3"},
            body={"amount": "10", "currency": "USD", "beneficiary_id": "beneficiary-verified"},
        )
        conflict = service.handle_request(
            "POST",
            "/payments",
            headers={"X-Session-Token": "token_requester", "Idempotency-Key": "idem-3"},
            body={"amount": "11", "currency": "USD", "beneficiary_id": "beneficiary-verified"},
        )
        self.assertEqual(201, created.status_code)
        self.assertEqual(created.body["payment_id"], replay.body["payment_id"])
        self.assertEqual(409, conflict.status_code)

    def test_validation_branches(self):
        service = new_service()
        payment_id = service.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="30")

        short_comment = service.handle_request(
            "POST",
            f"/payments/{payment_id}/reject",
            headers={"X-Session-Token": "token_bob"},
            body={"comment": "short"},
        )
        self.assertEqual(422, short_comment.status_code)
        good_reject = service.handle_request(
            "POST",
            f"/payments/{payment_id}/reject",
            headers={"X-Session-Token": "token_bob"},
            body={"comment": "valid rejection note"},
        )
        self.assertEqual(200, good_reject.status_code)

        approval_without_comment = service.handle_request(
            "POST",
            f"/payments/{service.seed_payment(status='SUBMITTED', creator_user_id='alice', amount='31')}/approve",
            headers={"X-Session-Token": "token_bob"},
            body={"command_id": "cmd-no-comment"},
        )
        self.assertEqual(200, approval_without_comment.status_code)

        iban_ok = service.handle_request(
            "PUT",
            "/beneficiaries/beneficiary-verified/bank-details",
            headers={"X-Session-Token": "token_admin"},
            body={"iban": "DE89370400440532013000"},
        )
        both_forms = service.handle_request(
            "PUT",
            "/beneficiaries/beneficiary-verified/bank-details",
            headers={"X-Session-Token": "token_admin"},
            body={"iban": "DE89370400440532013000", "account_number": "123", "routing_number": "456"},
        )
        self.assertEqual(200, iban_ok.status_code)
        self.assertEqual(422, both_forms.status_code)

        attach_ok = service.handle_request(
            "POST",
            f"/payments/{payment_id}/attachments",
            headers={"X-Session-Token": "token_requester"},
            body={"filename": "receipt.pdf", "content_type": "pdf", "size_bytes": 1000},
        )
        attach_bad = service.handle_request(
            "POST",
            f"/payments/{payment_id}/attachments",
            headers={"X-Session-Token": "token_requester"},
            body={"filename": "bad.txt", "content_type": "txt", "size_bytes": 1000},
        )
        self.assertEqual(201, attach_ok.status_code)
        self.assertEqual(422, attach_bad.status_code)

        batch_bad = service.handle_request(
            "POST",
            "/batch-payouts",
            headers={"X-Session-Token": "token_admin"},
            body={"items": [{"client_reference": "dup"}, {"client_reference": "dup"}]},
        )
        batch_ok = service.handle_request(
            "POST",
            "/batch-payouts",
            headers={"X-Session-Token": "token_admin"},
            body={"items": [{"client_reference": "a"}, {"client_reference": "b"}]},
        )
        self.assertEqual(422, batch_bad.status_code)
        self.assertEqual(201, batch_ok.status_code)

        callback_bad = service.handle_request(
            "PUT",
            "/tenants/tenant-a/callback-config",
            headers={"X-Session-Token": "token_admin"},
            body={"callback_url": "http://bad.example.com/cb"},
        )
        callback_ok = service.handle_request(
            "PUT",
            "/tenants/tenant-a/callback-config",
            headers={"X-Session-Token": "token_admin"},
            body={"callback_url": "https://allowed.example.com/cb"},
        )
        self.assertEqual(422, callback_bad.status_code)
        self.assertEqual(200, callback_ok.status_code)

    def test_payment_state_and_metric_rules(self):
        service = new_service()
        payment_id = service.handle_request(
            "POST",
            "/payments",
            headers={"X-Session-Token": "token_requester", "Idempotency-Key": "idem-submit"},
            body={"amount": "50", "currency": "USD", "beneficiary_id": "beneficiary-verified"},
        ).body["payment_id"]

        submit_denied = service.handle_request(
            "POST",
            f"/payments/{payment_id}/submit",
            headers={"X-Session-Token": "token_requester"},
        )
        self.assertEqual(409, submit_denied.status_code)

        service.handle_request(
            "POST",
            f"/payments/{payment_id}/line-items",
            headers={"X-Session-Token": "token_requester"},
            body={"items": [{"amount": "50", "description": "line"}]},
        )
        submit_ok = service.handle_request(
            "POST",
            f"/payments/{payment_id}/submit",
            headers={"X-Session-Token": "token_requester"},
        )
        self.assertEqual(200, submit_ok.status_code)

        early_approve = service.handle_request(
            "POST",
            f"/payments/{payment_id}/approve",
            headers={"X-Session-Token": "token_bob"},
            body={"command_id": "cmd-early"},
        )
        self.assertEqual(200, early_approve.status_code)

        service.state["payment_type_policies"][service.state["payments"][payment_id]["payment_type"]] = 2
        payment_id_two = service.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="60")
        service.state["payments"][payment_id_two]["line_items"] = [{"amount": "60"}]
        one_approval = service.handle_request(
            "POST",
            f"/payments/{payment_id_two}/approve",
            headers={"X-Session-Token": "token_bob"},
            body={"command_id": "cmd-one"},
        )
        self.assertEqual(200, one_approval.status_code)
        self.assertEqual("SUBMITTED", service.state["payments"][payment_id_two]["status"])
        second_approval = service.handle_request(
            "POST",
            f"/payments/{payment_id_two}/approve",
            headers={"X-Session-Token": "token_carol"},
            body={"command_id": "cmd-two"},
        )
        self.assertEqual(200, second_approval.status_code)
        self.assertEqual("APPROVED", service.state["payments"][payment_id_two]["status"])

        executed_id = service.seed_payment(status="EXECUTED", creator_user_id="alice", amount="80")
        patch_denied = service.handle_request(
            "PATCH",
            f"/payments/{executed_id}",
            headers={"X-Session-Token": "token_admin"},
            body={"amount": "90"},
        )
        patch_ok = service.handle_request(
            "PATCH",
            f"/payments/{executed_id}",
            headers={"X-Session-Token": "token_admin"},
            body={"reconciliation_note": "checked"},
        )
        self.assertEqual(409, patch_denied.status_code)
        self.assertEqual(200, patch_ok.status_code)

        scheduled_id = service.seed_payment(status="SUBMITTED", creator_user_id="alice", amount="90", scheduled_execution_at="2026-09-01T12:00:00Z")
        rejected = service.handle_request(
            "POST",
            f"/payments/{scheduled_id}/reject",
            headers={"X-Session-Token": "token_bob"},
            body={"comment": "this payment is invalid today"},
        )
        self.assertEqual(200, rejected.status_code)
        self.assertIsNone(service.state["payments"][scheduled_id]["scheduled_execution_at"])

        approved_id = service.seed_payment(status="APPROVED", creator_user_id="alice", amount="100")
        cancel_denied = service.handle_request(
            "POST",
            f"/payments/{approved_id}/cancel",
            headers={"X-Session-Token": "token_requester"},
        )
        self.assertEqual(409, cancel_denied.status_code)

        captured_id = service.seed_payment(status="CAPTURED", creator_user_id="alice", amount="100", captured_amount="100")
        service.handle_request(
            "POST",
            f"/payments/{captured_id}/chargebacks",
            headers={"X-Session-Token": "token_admin"},
            body={"chargeback_id": "cb-1"},
        )
        blocked_refund = service.handle_request(
            "POST",
            f"/payments/{captured_id}/refunds",
            headers={"X-Session-Token": "token_admin"},
            body={"amount": "10"},
        )
        self.assertEqual(409, blocked_refund.status_code)

        refund_id = service.seed_payment(status="CAPTURED", creator_user_id="alice", amount="100", captured_amount="100")
        partial_refund = service.handle_request(
            "POST",
            f"/payments/{refund_id}/refunds",
            headers={"X-Session-Token": "token_admin"},
            body={"amount": "40"},
        )
        self.assertEqual("CAPTURED", service.state["payments"][refund_id]["status"])
        full_refund = service.handle_request(
            "POST",
            f"/payments/{refund_id}/refunds",
            headers={"X-Session-Token": "token_admin"},
            body={"amount": "60"},
        )
        self.assertEqual(201, partial_refund.status_code)
        self.assertEqual(201, full_refund.status_code)
        self.assertEqual("REFUNDED", service.state["payments"][refund_id]["status"])

        approval_latency = service.get_metrics(name="approval_latency_ms")
        self.assertTrue(any(metric["value"] >= 0 for metric in approval_latency))

    def test_reliability_and_export_rules(self):
        service = new_service()
        delegated_task_id = service.seed_delegated_task(expired_minutes=1)
        service.handle_request("POST", "/control/delegations/expire-pending")
        self.assertEqual("INVALID", service.state["delegated_tasks"][delegated_task_id]["status"])
        self.assertEqual("delegation_expired", service.get_audit_events()[-1]["event_type"])

        first = service.handle_request(
            "POST",
            "/provider/messages/ledger-posting",
            body={"message_id": "msg-1", "amount": "5"},
        )
        dup = service.handle_request(
            "POST",
            "/provider/messages/ledger-posting",
            body={"message_id": "msg-1", "amount": "5"},
        )
        self.assertEqual(200, first.status_code)
        self.assertEqual(200, dup.status_code)
        self.assertEqual("duplicate_ignored", service.get_audit_events()[-1]["event_type"])

        webhook = service.handle_request(
            "POST",
            "/provider/webhook-deliveries",
            body={"delivery_id": "wh-1", "responses": [500, 502, 200, 500]},
        )
        self.assertEqual(200, webhook.status_code)
        attempts = service.state["webhook_deliveries"]["wh-1"]["attempts"]
        self.assertEqual([500, 502, 200], [attempt["status_code"] for attempt in attempts])

        export = service.handle_request(
            "POST",
            "/exports",
            headers={"X-Session-Token": "token_admin"},
            body={"rows": ["r1", "r2", "r3"]},
        )
        job_id = export.body["job_id"]
        service.handle_request("POST", f"/control/exports/{job_id}/crash", body={"written_rows": 2})
        restarted = service.handle_request(
            "POST",
            f"/exports/{job_id}/restart",
            headers={"X-Session-Token": "token_admin"},
        )
        self.assertEqual(200, restarted.status_code)
        self.assertEqual(["r1", "r2", "r3"], service.state["export_jobs"][job_id]["written_rows"])

        lock_job = service.seed_payout_lock(stale_minutes=6)
        first_takeover = service.handle_request("POST", f"/control/payout-locks/{lock_job}/takeover", body={"worker_id": "worker-b"})
        second_takeover = service.handle_request("POST", f"/control/payout-locks/{lock_job}/takeover", body={"worker_id": "worker-c"})
        self.assertEqual(200, first_takeover.status_code)
        self.assertEqual(409, second_takeover.status_code)

        imported = service.handle_request("POST", "/reconciliation/imports", body={"checksum": "abc", "content_rows": [1, 2]})
        duplicate_import = service.handle_request("POST", "/reconciliation/imports", body={"checksum": "abc", "content_rows": [1, 2]})
        self.assertEqual(201, imported.status_code)
        self.assertEqual(True, duplicate_import.body["duplicate"])

        export_event = service.get_audit_events(event_type="export_completed")[-1]
        self.assertIn("row_count", export_event)
        self.assertIn("duration_ms", export_event)
        self.assertIn("success", export_event)

    def test_execution_guardrail_circuit_override_and_reconciliation(self):
        service = new_service()
        job = service.handle_request("POST", "/execution-jobs", body={"job_id": "exec-1", "result": "SUCCEEDED"})
        self.assertEqual(200, job.status_code)
        events = service.get_audit_events()
        self.assertIn("execution_job_started", [event["event_type"] for event in events])
        self.assertIn("execution_job_ended", [event["event_type"] for event in events])

        service.set_guardrail_hook(
            lambda ctx: {
                "allow": False,
                "guardrail_id": "g-1",
                "requirement_id": "R055",
                "reason": "blocked by test",
            }
        )
        blocked = service.handle_request(
            "POST",
            "/payments",
            headers={"X-Session-Token": "token_requester", "Idempotency-Key": "idem-blocked"},
            body={"amount": "12", "currency": "USD", "beneficiary_id": "beneficiary-verified"},
        )
        self.assertEqual(409, blocked.status_code)
        self.assertEqual("R055", service.state["guardrail_violations"][-1]["requirement_id"])
        service.set_guardrail_hook(None)

        first_open = service.handle_request("POST", "/control/provider/circuit/open")
        second_open = service.handle_request("POST", "/control/provider/circuit/open")
        service.handle_request("POST", "/control/provider/circuit/close")
        service.handle_request("POST", "/control/provider/circuit/open")
        self.assertEqual(200, first_open.status_code)
        self.assertEqual(200, second_open.status_code)
        alert_events = service.get_audit_events(event_type="provider_circuit_open_alert")
        self.assertEqual(2, len(alert_events))

        override_payment = service.seed_payment(status="APPROVED", creator_user_id="alice", amount="22")
        empty_reason = service.handle_request(
            "POST",
            f"/payments/{override_payment}/manual-override",
            headers={"X-Session-Token": "token_admin"},
            body={"reason": ""},
        )
        good_reason = service.handle_request(
            "POST",
            f"/payments/{override_payment}/manual-override",
            headers={"X-Session-Token": "token_admin"},
            body={"reason": "operator approved exception"},
        )
        self.assertEqual(422, empty_reason.status_code)
        self.assertEqual(200, good_reason.status_code)
        self.assertEqual("manual_override", service.get_audit_events()[-1]["event_type"])

        batch = service.handle_request(
            "POST",
            "/batch-payouts",
            headers={"X-Session-Token": "token_admin"},
            body={"items": [{"client_reference": "x"}]},
        )
        batch_id = batch.body["batch_id"]
        mismatch = service.handle_request(
            "POST",
            "/reconciliation/check",
            headers={"X-Session-Token": "token_admin"},
            body={"batch_id": batch_id, "mismatch": True},
        )
        self.assertEqual(200, mismatch.status_code)
        self.assertTrue(any(case["batch_id"] == batch_id for case in service.state["review_cases"].values()))
        self.assertTrue(any(metric["name"] == "reconciliation_mismatch_count" for metric in service.get_metrics()))


if __name__ == "__main__":
    unittest.main()
