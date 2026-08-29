import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


TERMINAL_DECISION_STATES = {"APPROVED", "REJECTED"}
SETTLED_STATES = {"CAPTURED", "REFUNDED"}


@dataclass
class Response:
    status_code: int
    body: dict[str, Any]
    headers: dict[str, str] = field(default_factory=dict)


class ServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


class PaymentService:
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.storage_dir / "state.json"
        self.guardrail_hook = None
        self.state = self._load_or_seed_state()

    def _load_or_seed_state(self) -> dict[str, Any]:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())

        logical_clock = "2026-08-28T12:00:00Z"
        state = {
            "logical_clock": logical_clock,
            "sequence": {"request": 0, "payment": 0, "approval": 0, "attachment": 0, "batch": 0, "job": 0, "refund": 0, "delegation": 0, "review_case": 0, "token": 0},
            "payments": {},
            "approvals": [],
            "audit_events": [],
            "logs": [],
            "metrics": [],
            "internal_transfers": [],
            "beneficiaries": {
                "beneficiary-verified": {
                    "beneficiary_id": "beneficiary-verified",
                    "tenant_id": "tenant-a",
                    "verified": True,
                    "account_number": "1111222233334444",
                    "routing_number": "999000111",
                    "iban": None,
                },
                "beneficiary-unverified": {
                    "beneficiary_id": "beneficiary-unverified",
                    "tenant_id": "tenant-a",
                    "verified": False,
                    "account_number": "4444333322221111",
                    "routing_number": "111000999",
                    "iban": None,
                },
            },
            "delegations": {},
            "delegated_tasks": {},
            "attachments": {},
            "batch_payouts": {},
            "callback_configs": {},
            "provider_receipts": {},
            "provider_config": {"primary": {"name": "primary", "kind": "simulated"}},
            "provider_circuit": {"is_open": False, "open_interval": 0, "alert_emitted_for_interval": []},
            "document_tokens": {},
            "reconciliation_reports": [],
            "reconciliation_imports": [],
            "review_cases": {},
            "export_jobs": {},
            "execution_jobs": {},
            "webhook_deliveries": {},
            "payout_locks": {},
            "guardrail_violations": [],
            "incident_tickets": {"inc-1": {"incident_ticket_id": "inc-1", "status": "OPEN"}},
            "payment_type_policies": {"STANDARD": 1},
            "idempotency_keys": {},
            "users": {
                "token_requester": {"actor_id": "alice", "roles": ["requester"], "tenant_id": "tenant-a", "active": True},
                "token_bob": {"actor_id": "bob", "roles": ["approver"], "tenant_id": "tenant-a", "active": True},
                "token_carol": {"actor_id": "carol", "roles": ["approver", "finance_manager"], "tenant_id": "tenant-a", "active": True},
                "token_admin": {"actor_id": "admin_user", "roles": ["admin", "finance_manager"], "tenant_id": "tenant-a", "active": True},
                "token_support": {"actor_id": "support_user", "roles": ["support_readonly"], "tenant_id": "tenant-a", "active": True},
                "token_treasury": {"actor_id": "treasury_user", "roles": ["treasury"], "tenant_id": "tenant-a", "active": True},
                "token_config": {"actor_id": "config_user", "roles": ["provider_config_reader"], "tenant_id": "tenant-a", "active": True},
                "token_olivia": {"actor_id": "olivia", "roles": ["approver"], "tenant_id": "tenant-a", "active": True},
                "token_inactive": {"actor_id": "inactive_user", "roles": ["approver"], "tenant_id": "tenant-a", "active": False},
            },
            "approved_mtls_subjects": ["subject-ok"],
            "tenant_allowlists": {"tenant-a": ["allowed.example.com"]},
            "secrets": {"payment_api_key": "top-secret-value"},
        }
        self._persist(state)
        return state

    def _persist(self, state: dict[str, Any] | None = None) -> None:
        if state is not None:
            self.state = state
        self.state_file.write_text(json.dumps(self.state, indent=2, sort_keys=True))

    def _next_id(self, name: str, prefix: str) -> str:
        self.state["sequence"][name] += 1
        return f"{prefix}-{self.state['sequence'][name]:04d}"

    def _now(self) -> datetime:
        return datetime.fromisoformat(self.state["logical_clock"].replace("Z", "+00:00"))

    def _now_iso(self) -> str:
        return self._now().astimezone(UTC).isoformat().replace("+00:00", "Z")

    def _advance_clock(self, *, minutes: int = 0) -> None:
        self.state["logical_clock"] = (self._now() + timedelta(minutes=minutes)).astimezone(UTC).isoformat().replace("+00:00", "Z")

    def seed_payment(
        self,
        *,
        status: str,
        creator_user_id: str,
        amount: str,
        scheduled_execution_at: str | None = None,
        captured_amount: str | None = None,
    ) -> str:
        payment_id = self._next_id("payment", "pay")
        self.state["payments"][payment_id] = {
            "payment_id": payment_id,
            "tenant_id": "tenant-a",
            "payment_type": "STANDARD",
            "creator_user_id": creator_user_id,
            "beneficiary_id": "beneficiary-verified",
            "amount": str(amount),
            "currency": "USD",
            "status": status,
            "scheduled_execution_at": scheduled_execution_at,
            "captured_amount": str(captured_amount or amount),
            "approved_refund_total": "0",
            "dispute_status": "NONE",
            "reconciliation_note": None,
            "incident_ticket_id": None,
            "line_items": [],
            "approval_comments": [],
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
            "submitted_at": self._now_iso() if status in {"SUBMITTED", "APPROVED", "REJECTED", "EXECUTED", "CAPTURED", "REFUNDED"} else None,
            "terminal_decision_recorded": status in TERMINAL_DECISION_STATES,
        }
        self._persist()
        return payment_id

    def seed_delegation_window(self, delegator_user_id: str, delegate_user_id: str, *, start_offset_minutes: int, end_offset_minutes: int) -> str:
        delegation_id = self._next_id("delegation", "del")
        self.state["delegations"][delegation_id] = {
            "delegation_id": delegation_id,
            "delegator_user_id": delegator_user_id,
            "delegate_user_id": delegate_user_id,
            "starts_at": (self._now() + timedelta(minutes=start_offset_minutes)).astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "ends_at": (self._now() + timedelta(minutes=end_offset_minutes)).astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "status": "ACTIVE",
        }
        self._persist()
        return delegation_id

    def seed_document_token(self, *, document_id: str, age_minutes: int) -> str:
        token_id = self._next_id("token", "doc")
        issued_at = (self._now() - timedelta(minutes=age_minutes)).astimezone(UTC).isoformat().replace("+00:00", "Z")
        self.state["document_tokens"][token_id] = {"token_id": token_id, "document_id": document_id, "issued_at": issued_at, "expires_at": (datetime.fromisoformat(issued_at.replace("Z", "+00:00")) + timedelta(minutes=15)).astimezone(UTC).isoformat().replace("+00:00", "Z")}
        self._persist()
        return token_id

    def seed_delegated_task(self, *, expired_minutes: int) -> str:
        delegation_id = self.seed_delegation_window("bob", "olivia", start_offset_minutes=-10, end_offset_minutes=-expired_minutes)
        task_id = self._next_id("job", "delegated-task")
        self.state["delegated_tasks"][task_id] = {
            "task_id": task_id,
            "delegation_id": delegation_id,
            "status": "PENDING",
            "expires_at": self.state["delegations"][delegation_id]["ends_at"],
        }
        self._persist()
        return task_id

    def seed_payout_lock(self, *, stale_minutes: int) -> str:
        job_id = self._next_id("job", "lock-job")
        self.state["payout_locks"][job_id] = {
            "job_id": job_id,
            "owner": "worker-a",
            "acquired_at": (self._now() - timedelta(minutes=stale_minutes)).astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "successor": None,
        }
        self._persist()
        return job_id

    def set_guardrail_hook(self, hook: Any) -> None:
        self.guardrail_hook = hook

    def get_audit_events(self, *, event_type: str | None = None) -> list[dict[str, Any]]:
        if event_type is None:
            return copy.deepcopy(self.state["audit_events"])
        return [copy.deepcopy(event) for event in self.state["audit_events"] if event["event_type"] == event_type]

    def get_logs(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.state["logs"])

    def get_metrics(self, *, name: str | None = None) -> list[dict[str, Any]]:
        if name is None:
            return copy.deepcopy(self.state["metrics"])
        return [copy.deepcopy(metric) for metric in self.state["metrics"] if metric["name"] == name]

    def handle_request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> Response:
        headers = headers or {}
        body = body or {}
        query = query or {}
        correlation_id = self._next_id("request", "corr")
        context = {
            "method": method,
            "path": path,
            "headers": headers,
            "body": body,
            "query": query,
            "correlation_id": correlation_id,
            "actor": self._resolve_actor(headers),
        }

        try:
            if self._is_mutating(method, path) and self.guardrail_hook is not None and not path.startswith("/control/"):
                decision = self.guardrail_hook(context)
                if not decision.get("allow", True):
                    self._record_guardrail_block(context, decision)
                    response = self._response(409, "GUARDRAIL_BLOCKED", decision.get("reason", "guardrail blocked request"), correlation_id, details={"requirement_id": decision.get("requirement_id")})
                    self._log_request(context, response)
                    self._persist()
                    return response

            response = self._dispatch(context)
            self._log_request(context, response)
            self._persist()
            return response
        except ServiceError as exc:
            response = self._response(exc.status_code, exc.code, exc.message, correlation_id, exc.details)
            self._log_request(context, response)
            self._persist()
            return response
        except Exception as exc:  # pragma: no cover - exercised by acceptance case
            self._append_log(
                {
                    "log_type": "exception",
                    "correlation_id": correlation_id,
                    "path": path,
                    "message": f"internal error: {type(exc).__name__}",
                }
            )
            response = self._response(500, "INTERNAL_ERROR", "unexpected failure", correlation_id)
            self._log_request(context, response)
            self._persist()
            return response

    def _dispatch(self, context: dict[str, Any]) -> Response:
        method = context["method"]
        path = context["path"]
        body = context["body"]
        query = context["query"]
        actor = context["actor"]

        if path == "/control/cause-error":
            raise RuntimeError(self.state["secrets"]["payment_api_key"])

        if method == "POST" and path == "/payments":
            self._require_active_session(actor)
            return self._create_payment(actor, context["headers"], body, context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/payments/[^/]+/line-items", path):
            self._require_active_session(actor)
            return self._add_line_items(self._path_id(path), body, context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/payments/[^/]+/submit", path):
            self._require_active_session(actor)
            return self._submit_payment(self._path_id(path), actor, context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/payments/[^/]+/approve", path):
            return self._approve_payment(self._path_id(path), actor, body, context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/payments/[^/]+/release", path):
            self._require_active_session(actor)
            return self._release_payment(self._path_id(path), context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/payments/[^/]+/void", path):
            self._require_active_session(actor)
            return self._void_payment(self._path_id(path), actor, context["correlation_id"])
        if method == "GET" and re.fullmatch(r"/payments/[^/]+/summary", path):
            self._require_active_session(actor)
            return self._payment_summary(self._path_id(path), actor, context["correlation_id"])
        if method == "POST" and path == "/delegations":
            self._require_active_session(actor)
            return self._create_delegation(actor, body, context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/payments/[^/]+/reverse", path):
            self._require_active_session(actor)
            return self._reverse_payment(self._path_id(path), actor, body, context["correlation_id"])
        if method == "POST" and path == "/internal-transfers":
            return self._create_internal_transfer(context["headers"], body, context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/payments/[^/]+/cancel", path):
            self._require_active_session(actor)
            return self._cancel_payment(self._path_id(path), actor, context["correlation_id"])
        if method == "GET" and re.fullmatch(r"/documents/[^/]+/download", path):
            return self._download_document(self._path_id(path), query, context["correlation_id"])
        if method == "GET" and path == "/reconciliation/reports/download":
            self._require_active_session(actor)
            return self._download_reconciliation_report(actor, query, context["correlation_id"])
        if method == "POST" and path == "/search/customer-email":
            self._require_active_session(actor)
            return self._search_customer_email(body, context["correlation_id"])
        if method == "GET" and re.fullmatch(r"/provider-config/[^/]+", path):
            self._require_active_session(actor)
            return self._get_provider_config(path.split("/")[-1], actor, context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/payments/[^/]+/reject", path):
            self._require_active_session(actor)
            return self._reject_payment(self._path_id(path), actor, body, context["correlation_id"])
        if method == "PUT" and re.fullmatch(r"/beneficiaries/[^/]+/bank-details", path):
            self._require_active_session(actor)
            return self._update_beneficiary(self._path_id(path), body, context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/payments/[^/]+/attachments", path):
            self._require_active_session(actor)
            return self._add_attachment(self._path_id(path), body, context["correlation_id"])
        if method == "POST" and path == "/batch-payouts":
            self._require_active_session(actor)
            return self._create_batch(body, context["correlation_id"])
        if method == "PUT" and re.fullmatch(r"/tenants/[^/]+/callback-config", path):
            self._require_active_session(actor)
            return self._set_callback_config(path.split("/")[2], body, context["correlation_id"])
        if method == "PATCH" and re.fullmatch(r"/payments/[^/]+", path):
            self._require_active_session(actor)
            return self._patch_payment(self._path_id(path), body, context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/payments/[^/]+/chargebacks", path):
            self._require_active_session(actor)
            return self._open_chargeback(self._path_id(path), body, context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/payments/[^/]+/refunds", path):
            self._require_active_session(actor)
            return self._create_refund(self._path_id(path), body, context["correlation_id"])
        if method == "POST" and path == "/control/delegations/expire-pending":
            return self._expire_delegated_tasks(context["correlation_id"])
        if method == "POST" and path == "/provider/messages/ledger-posting":
            return self._provider_message(body, context["correlation_id"])
        if method == "POST" and path == "/provider/webhook-deliveries":
            return self._webhook_delivery(body, context["correlation_id"])
        if method == "POST" and path == "/exports":
            self._require_active_session(actor)
            return self._start_export(actor, body, context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/control/exports/[^/]+/crash", path):
            return self._crash_export(self._control_resource_id(path), body, context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/exports/[^/]+/restart", path):
            self._require_active_session(actor)
            return self._restart_export(self._path_id(path), context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/control/payout-locks/[^/]+/takeover", path):
            return self._takeover_lock(self._control_resource_id(path), body, context["correlation_id"])
        if method == "POST" and path == "/reconciliation/imports":
            return self._reconciliation_import(body, context["correlation_id"])
        if method == "POST" and path == "/execution-jobs":
            return self._execution_job(body, context["correlation_id"])
        if method == "POST" and path == "/control/provider/circuit/open":
            return self._open_circuit(context["correlation_id"])
        if method == "POST" and path == "/control/provider/circuit/close":
            return self._close_circuit(context["correlation_id"])
        if method == "POST" and re.fullmatch(r"/payments/[^/]+/manual-override", path):
            self._require_active_session(actor)
            return self._manual_override(self._path_id(path), actor, body, context["correlation_id"])
        if method == "POST" and path == "/reconciliation/check":
            self._require_active_session(actor)
            return self._reconciliation_check(body, context["correlation_id"])
        if method == "POST" and path == "/control/clock/advance":
            self._advance_clock(minutes=int(body.get("minutes", 0)))
            return Response(200, {"logical_clock": self.state["logical_clock"]}, {"correlation_id": context["correlation_id"]})

        raise ServiceError(404, "NOT_FOUND", f"unknown route: {path}")

    def _create_payment(self, actor: dict[str, Any], headers: dict[str, str], body: dict[str, Any], correlation_id: str) -> Response:
        idem_key = headers.get("Idempotency-Key")
        if not idem_key:
            raise ServiceError(422, "VALIDATION_ERROR", "Idempotency-Key is required", {"field": "Idempotency-Key"})
        canonical_body = json.dumps(body, sort_keys=True)
        body_hash = hashlib.sha256(canonical_body.encode()).hexdigest()
        existing = self.state["idempotency_keys"].get(idem_key)
        if existing is not None:
            if existing["body_hash"] != body_hash:
                raise ServiceError(409, "IDEMPOTENCY_CONFLICT", "idempotency key reused with different body")
            payment = self.state["payments"][existing["payment_id"]]
            return Response(200, {"payment_id": payment["payment_id"], "status": payment["status"]}, {"correlation_id": correlation_id})

        amount = Decimal(str(body.get("amount", "0")))
        if amount <= 0 or amount > Decimal("100000"):
            raise ServiceError(422, "VALIDATION_ERROR", "invalid payment amount", {"amount": "must be > 0 and <= 100000"})

        scheduled_execution_at = body.get("scheduled_execution_at")
        if scheduled_execution_at is not None:
            self._validate_schedule(scheduled_execution_at)

        beneficiary_id = body.get("beneficiary_id")
        if beneficiary_id not in self.state["beneficiaries"]:
            raise ServiceError(404, "NOT_FOUND", "beneficiary not found")

        payment_id = self._next_id("payment", "pay")
        payment = {
            "payment_id": payment_id,
            "tenant_id": actor["tenant_id"],
            "payment_type": body.get("payment_type", "STANDARD"),
            "creator_user_id": actor["actor_id"],
            "beneficiary_id": beneficiary_id,
            "amount": str(amount),
            "currency": body.get("currency", "USD"),
            "status": "DRAFT",
            "scheduled_execution_at": scheduled_execution_at,
            "captured_amount": str(amount),
            "approved_refund_total": "0",
            "dispute_status": "NONE",
            "reconciliation_note": None,
            "incident_ticket_id": None,
            "line_items": [],
            "approval_comments": [],
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
            "submitted_at": None,
            "terminal_decision_recorded": False,
        }
        self.state["payments"][payment_id] = payment
        self.state["idempotency_keys"][idem_key] = {"payment_id": payment_id, "body_hash": body_hash}
        return Response(201, {"payment_id": payment_id, "status": payment["status"]}, {"correlation_id": correlation_id})

    def _add_line_items(self, payment_id: str, body: dict[str, Any], correlation_id: str) -> Response:
        payment = self._payment(payment_id)
        payment["line_items"].extend(body.get("items", []))
        payment["updated_at"] = self._now_iso()
        return Response(201, {"payment_id": payment_id, "line_item_count": len(payment["line_items"])}, {"correlation_id": correlation_id})

    def _submit_payment(self, payment_id: str, actor: dict[str, Any], correlation_id: str) -> Response:
        payment = self._payment(payment_id)
        beneficiary = self.state["beneficiaries"][payment["beneficiary_id"]]
        if payment["status"] != "DRAFT" or not payment["line_items"] or not beneficiary["verified"]:
            raise ServiceError(409, "STATE_CONFLICT", "payment cannot be submitted")
        self._change_payment_status(payment, "SUBMITTED", actor["actor_id"])
        payment["submitted_at"] = self._now_iso()
        return Response(200, {"payment_id": payment_id, "status": payment["status"]}, {"correlation_id": correlation_id})

    def _approve_payment(self, payment_id: str, actor: dict[str, Any], body: dict[str, Any], correlation_id: str) -> Response:
        self._require_active_session(actor)
        payment = self._payment(payment_id)
        command_id = body.get("command_id")
        if command_id:
            for approval in self.state["approvals"]:
                if approval["payment_id"] == payment_id and approval["actor_id"] == actor["actor_id"] and approval.get("command_id") == command_id:
                    return Response(200, {"payment_id": payment_id, "status": payment["status"], "duplicate": True}, {"correlation_id": correlation_id})

        delegate_for = None
        delegation_id = body.get("delegation_id")
        roles = set(actor["roles"])
        if delegation_id is not None:
            delegation = self.state["delegations"].get(delegation_id)
            if delegation is None:
                self._audit_permission_denial(actor["actor_id"], payment_id, "delegation_not_found")
                raise ServiceError(403, "FORBIDDEN", "delegation not found")
            now = self._now()
            starts_at = datetime.fromisoformat(delegation["starts_at"].replace("Z", "+00:00"))
            ends_at = datetime.fromisoformat(delegation["ends_at"].replace("Z", "+00:00"))
            if actor["actor_id"] != delegation["delegate_user_id"] or not (starts_at <= now <= ends_at):
                self._audit_permission_denial(actor["actor_id"], payment_id, "delegation_inactive")
                raise ServiceError(403, "FORBIDDEN", "delegation inactive")
            roles.add("approver")
            delegate_for = delegation["delegator_user_id"]

        if not actor["active"]:
            raise ServiceError(401, "UNAUTHORIZED", "inactive session token")

        if "approver" not in roles:
            self._audit_permission_denial(actor["actor_id"], payment_id, "missing_approver_role")
            raise ServiceError(403, "FORBIDDEN", "approver role required")

        if payment["creator_user_id"] == actor["actor_id"]:
            self._audit_permission_denial(actor["actor_id"], payment_id, "creator_cannot_self_approve")
            raise ServiceError(403, "FORBIDDEN", "creator cannot approve own payment")

        approval = {
            "approval_id": self._next_id("approval", "approval"),
            "payment_id": payment_id,
            "actor_id": actor["actor_id"],
            "roles_at_time": sorted(roles),
            "delegated_for_user_id": delegate_for,
            "command_id": command_id,
            "created_at": self._now_iso(),
            "decision": "APPROVE",
        }
        self.state["approvals"].append(approval)

        required_count = self.state["payment_type_policies"].get(payment["payment_type"], 1)
        current_count = len({entry["actor_id"] for entry in self.state["approvals"] if entry["payment_id"] == payment_id and entry["decision"] == "APPROVE"})
        if payment["status"] == "SUBMITTED" and current_count >= required_count:
            self._change_payment_status(payment, "APPROVED", actor["actor_id"])
            self._record_approval_latency_if_needed(payment, actor["actor_id"])

        return Response(200, {"payment_id": payment_id, "status": payment["status"]}, {"correlation_id": correlation_id})

    def _release_payment(self, payment_id: str, correlation_id: str) -> Response:
        payment = self._payment(payment_id)
        if Decimal(payment["amount"]) > Decimal("10000"):
            approvals = [entry for entry in self.state["approvals"] if entry["payment_id"] == payment_id and entry["decision"] == "APPROVE"]
            distinct = {entry["actor_id"] for entry in approvals}
            finance = any("finance_manager" in entry["roles_at_time"] for entry in approvals)
            if len(distinct) < 2 or not finance:
                raise ServiceError(409, "STATE_CONFLICT", "release prerequisites not met")
        return Response(200, {"payment_id": payment_id, "released": True}, {"correlation_id": correlation_id})

    def _void_payment(self, payment_id: str, actor: dict[str, Any], correlation_id: str) -> Response:
        payment = self._payment(payment_id)
        if payment["creator_user_id"] != actor["actor_id"] and "admin" not in actor["roles"]:
            raise ServiceError(403, "FORBIDDEN", "void not allowed")
        if payment["status"] in SETTLED_STATES:
            raise ServiceError(409, "STATE_CONFLICT", "payment already settled")
        self._change_payment_status(payment, "VOIDED", actor["actor_id"])
        pass  # mutation R003_M03: payment_voided audit omitted
        return Response(200, {"payment_id": payment_id, "status": payment["status"]}, {"correlation_id": correlation_id})

    def _payment_summary(self, payment_id: str, actor: dict[str, Any], correlation_id: str) -> Response:
        payment = self._payment(payment_id)
        beneficiary = self.state["beneficiaries"][payment["beneficiary_id"]]
        body = {
            "payment_id": payment_id,
            "status": payment["status"],
            "amount": payment["amount"],
            "beneficiary": {
                "account_number": self._mask_account_number(beneficiary.get("account_number")),
                "routing_number": None if "support_readonly" in actor["roles"] else beneficiary.get("routing_number"),
            },
            "approval_comments": [entry["text"] for entry in payment["approval_comments"] if not entry.get("confidential")],
        }
        return Response(200, body, {"correlation_id": correlation_id})

    def _create_delegation(self, actor: dict[str, Any], body: dict[str, Any], correlation_id: str) -> Response:
        source_id = body.get("delegation_id")
        if source_id and source_id in self.state["delegations"]:
            source = self.state["delegations"][source_id]
            if actor["actor_id"] == source["delegate_user_id"]:
                raise ServiceError(403, "FORBIDDEN", "delegate cannot chain delegation")
        delegation_id = self.seed_delegation_window(actor["actor_id"], body.get("delegate_user_id", "unknown"), start_offset_minutes=0, end_offset_minutes=60)
        return Response(201, {"delegation_id": delegation_id}, {"correlation_id": correlation_id})

    def _reverse_payment(self, payment_id: str, actor: dict[str, Any], body: dict[str, Any], correlation_id: str) -> Response:
        payment = self._payment(payment_id)
        if "treasury" not in actor["roles"]:
            raise ServiceError(403, "FORBIDDEN", "treasury role required")
        if payment["status"] not in SETTLED_STATES:
            raise ServiceError(409, "STATE_CONFLICT", "payment not settled")
        incident_ticket_id = body.get("incident_ticket_id")
        if incident_ticket_id not in self.state["incident_tickets"]:
            raise ServiceError(404, "NOT_FOUND", "incident ticket not found")
        payment["incident_ticket_id"] = incident_ticket_id
        return Response(200, {"payment_id": payment_id, "reversed": True}, {"correlation_id": correlation_id})

    def _create_internal_transfer(self, headers: dict[str, str], body: dict[str, Any], correlation_id: str) -> Response:
        subject = headers.get("X-mTLS-Subject")
        service_account = headers.get("X-Service-Account")
        if not service_account or subject not in self.state["approved_mtls_subjects"]:
            raise ServiceError(403, "FORBIDDEN", "mTLS subject not allowlisted")
        transfer_id = self._next_id("job", "transfer")
        self.state["internal_transfers"].append({"transfer_id": transfer_id, "amount": body.get("amount")})
        return Response(201, {"transfer_id": transfer_id}, {"correlation_id": correlation_id})

    def _download_document(self, document_id: str, query: dict[str, Any], correlation_id: str) -> Response:
        token_id = query.get("token")
        token = self.state["document_tokens"].get(token_id)
        if token is None or token["document_id"] != document_id:
            raise ServiceError(404, "NOT_FOUND", "download token not found")
        if self._now() > datetime.fromisoformat(token["expires_at"].replace("Z", "+00:00")):
            self._append_audit({"event_type": "document_token_expired", "document_id": document_id, "token_id": token_id})
            raise ServiceError(410, "GONE", "download token expired")
        return Response(200, {"document_id": document_id}, {"correlation_id": correlation_id})

    def _download_reconciliation_report(self, actor: dict[str, Any], query: dict[str, Any], correlation_id: str) -> Response:
        event = {
            "event_type": "reconciliation_report_downloaded",
            "actor_id": actor["actor_id"],
            "applied_filters": copy.deepcopy(query),
            "row_count": 0,
            "generation_timestamp": self._now_iso(),
        }
        self._append_audit(event)
        self.state["reconciliation_reports"].append(event)
        return Response(200, {"report": []}, {"correlation_id": correlation_id})

    def _search_customer_email(self, body: dict[str, Any], correlation_id: str) -> Response:
        email = body.get("email", "")
        salted_hash = hashlib.sha256(f"ic-sqits::{email}".encode()).hexdigest()
        self._append_log({"log_type": "search", "correlation_id": correlation_id, "email_hash": salted_hash})
        return Response(200, {"matched": False}, {"correlation_id": correlation_id})

    def _get_provider_config(self, config_name: str, actor: dict[str, Any], correlation_id: str) -> Response:
        outcome = "allowed" if "provider_config_reader" in actor["roles"] else "denied"
        self._append_audit({"event_type": "provider_config_read", "actor_id": actor["actor_id"], "outcome": outcome, "config_name": config_name})
        if outcome == "denied":
            raise ServiceError(403, "FORBIDDEN", "provider config read denied")
        return Response(200, self.state["provider_config"].get(config_name, {}), {"correlation_id": correlation_id})

    def _reject_payment(self, payment_id: str, actor: dict[str, Any], body: dict[str, Any], correlation_id: str) -> Response:
        comment = body.get("comment", "")
        if not (10 <= len(comment) <= 500):
            raise ServiceError(422, "VALIDATION_ERROR", "rejection comment length invalid", {"comment": "must be 10..500 characters"})
        payment = self._payment(payment_id)
        payment["approval_comments"].append({"text": comment, "confidential": False})
        payment["scheduled_execution_at"] = None
        self._change_payment_status(payment, "REJECTED", actor["actor_id"])
        self._record_approval_latency_if_needed(payment, actor["actor_id"])
        return Response(200, {"payment_id": payment_id, "status": payment["status"]}, {"correlation_id": correlation_id})

    def _update_beneficiary(self, beneficiary_id: str, body: dict[str, Any], correlation_id: str) -> Response:
        beneficiary = self.state["beneficiaries"].get(beneficiary_id)
        if beneficiary is None:
            raise ServiceError(404, "NOT_FOUND", "beneficiary not found")
        iban = body.get("iban")
        account_number = body.get("account_number")
        routing_number = body.get("routing_number")
        has_iban = bool(iban)
        has_pair = bool(account_number and routing_number)
        if has_iban == has_pair:
            raise ServiceError(422, "VALIDATION_ERROR", "invalid bank detail form")
        beneficiary["iban"] = iban if has_iban else None
        beneficiary["account_number"] = account_number if has_pair else beneficiary.get("account_number")
        beneficiary["routing_number"] = routing_number if has_pair else beneficiary.get("routing_number")
        return Response(200, {"beneficiary_id": beneficiary_id}, {"correlation_id": correlation_id})

    def _add_attachment(self, payment_id: str, body: dict[str, Any], correlation_id: str) -> Response:
        self._payment(payment_id)
        if body.get("content_type") not in {"pdf", "png"}:
            raise ServiceError(422, "VALIDATION_ERROR", "attachment type not allowed")
        if int(body.get("size_bytes", 0)) > 5 * 1024 * 1024:
            raise ServiceError(422, "VALIDATION_ERROR", "attachment too large")
        attachment_id = self._next_id("attachment", "attachment")
        self.state["attachments"][attachment_id] = {"attachment_id": attachment_id, "payment_id": payment_id, **body}
        return Response(201, {"attachment_id": attachment_id}, {"correlation_id": correlation_id})

    def _create_batch(self, body: dict[str, Any], correlation_id: str) -> Response:
        items = body.get("items", [])
        if not (1 <= len(items) <= 100):
            raise ServiceError(422, "VALIDATION_ERROR", "invalid batch size")
        refs = [item.get("client_reference") for item in items]
        if len(refs) != len(set(refs)):
            raise ServiceError(422, "VALIDATION_ERROR", "duplicate client_reference")
        batch_id = self._next_id("batch", "batch")
        self.state["batch_payouts"][batch_id] = {"batch_id": batch_id, "items": copy.deepcopy(items)}
        return Response(201, {"batch_id": batch_id}, {"correlation_id": correlation_id})

    def _set_callback_config(self, tenant_id: str, body: dict[str, Any], correlation_id: str) -> Response:
        callback_url = body.get("callback_url", "")
        parsed = urlparse(callback_url)
        if parsed.scheme != "https" or parsed.hostname not in self.state["tenant_allowlists"].get(tenant_id, []):
            raise ServiceError(422, "VALIDATION_ERROR", "callback URL invalid")
        self.state["callback_configs"][tenant_id] = {"callback_url": callback_url}
        return Response(200, {"tenant_id": tenant_id, "callback_url": callback_url}, {"correlation_id": correlation_id})

    def _patch_payment(self, payment_id: str, body: dict[str, Any], correlation_id: str) -> Response:
        payment = self._payment(payment_id)
        if payment["status"] == "EXECUTED":
            disallowed = [key for key in body if key != "reconciliation_note"]
            if disallowed:
                raise ServiceError(409, "STATE_CONFLICT", "only reconciliation_note may change after execution")
        payment.update(body)
        payment["updated_at"] = self._now_iso()
        return Response(200, {"payment_id": payment_id, "status": payment["status"]}, {"correlation_id": correlation_id})

    def _cancel_payment(self, payment_id: str, actor: dict[str, Any], correlation_id: str) -> Response:
        payment = self._payment(payment_id)
        if payment["status"] not in {"DRAFT", "SUBMITTED"}:
            raise ServiceError(409, "STATE_CONFLICT", "payment cannot be canceled")
        self._change_payment_status(payment, "CANCELED", actor["actor_id"])
        return Response(200, {"payment_id": payment_id, "status": payment["status"]}, {"correlation_id": correlation_id})

    def _open_chargeback(self, payment_id: str, body: dict[str, Any], correlation_id: str) -> Response:
        payment = self._payment(payment_id)
        payment["dispute_status"] = "OPEN"
        payment["updated_at"] = self._now_iso()
        return Response(201, {"chargeback_id": body.get("chargeback_id")}, {"correlation_id": correlation_id})

    def _create_refund(self, payment_id: str, body: dict[str, Any], correlation_id: str) -> Response:
        payment = self._payment(payment_id)
        if payment["dispute_status"] == "OPEN":
            raise ServiceError(409, "STATE_CONFLICT", "refund blocked during dispute")
        remaining = Decimal(payment["captured_amount"]) - Decimal(payment["approved_refund_total"])
        amount = Decimal(str(body.get("amount", "0")))
        if amount > remaining:
            raise ServiceError(422, "VALIDATION_ERROR", "refund exceeds captured remaining amount")
        refund_id = self._next_id("refund", "refund")
        payment["approved_refund_total"] = str(Decimal(payment["approved_refund_total"]) + amount)
        if Decimal(payment["approved_refund_total"]) == Decimal(payment["captured_amount"]):
            self._change_payment_status(payment, "REFUNDED", "system")
        payment.setdefault("refunds", []).append({"refund_id": refund_id, "amount": str(amount), "status": "APPROVED"})
        return Response(201, {"refund_id": refund_id}, {"correlation_id": correlation_id})

    def _expire_delegated_tasks(self, correlation_id: str) -> Response:
        expired = []
        now = self._now()
        for task in self.state["delegated_tasks"].values():
            if task["status"] == "PENDING" and now > datetime.fromisoformat(task["expires_at"].replace("Z", "+00:00")):
                task["status"] = "INVALID"
                expired.append(task["task_id"])
                self._append_audit({"event_type": "delegation_expired", "task_id": task["task_id"], "timestamp": self._now_iso()})
        return Response(200, {"expired_tasks": expired}, {"correlation_id": correlation_id})

    def _provider_message(self, body: dict[str, Any], correlation_id: str) -> Response:
        message_id = body.get("message_id")
        if message_id in self.state["provider_receipts"]:
            self._append_audit({"event_type": "duplicate_ignored", "message_id": message_id, "timestamp": self._now_iso()})
            return Response(200, {"duplicate": True}, {"correlation_id": correlation_id})
        self.state["provider_receipts"][message_id] = copy.deepcopy(body)
        return Response(200, {"duplicate": False}, {"correlation_id": correlation_id})

    def _webhook_delivery(self, body: dict[str, Any], correlation_id: str) -> Response:
        delivery_id = body.get("delivery_id")
        responses = body.get("responses", [])
        attempts = []
        for index, status_code in enumerate(responses[:3], start=1):
            attempts.append({"attempt": index, "status_code": status_code})
            if 200 <= int(status_code) < 300:
                break
        self.state["webhook_deliveries"][delivery_id] = {"attempts": attempts}
        return Response(200, {"delivery_id": delivery_id, "attempt_count": len(attempts)}, {"correlation_id": correlation_id})

    def _start_export(self, actor: dict[str, Any], body: dict[str, Any], correlation_id: str) -> Response:
        job_id = self._next_id("job", "export")
        self.state["export_jobs"][job_id] = {
            "job_id": job_id,
            "requester_id": actor["actor_id"],
            "rows": copy.deepcopy(body.get("rows", [])),
            "written_rows": [],
            "started_at": self._now_iso(),
            "crashed": False,
            "success": False,
        }
        return Response(201, {"job_id": job_id}, {"correlation_id": correlation_id})

    def _crash_export(self, job_id: str, body: dict[str, Any], correlation_id: str) -> Response:
        job = self.state["export_jobs"].get(job_id)
        if job is None:
            raise ServiceError(404, "NOT_FOUND", "export job not found")
        written = int(body.get("written_rows", 0))
        job["written_rows"] = copy.deepcopy(job["rows"][:written])
        job["crashed"] = True
        return Response(200, {"job_id": job_id, "crashed": True}, {"correlation_id": correlation_id})

    def _restart_export(self, job_id: str, correlation_id: str) -> Response:
        job = self.state["export_jobs"].get(job_id)
        if job is None:
            raise ServiceError(404, "NOT_FOUND", "export job not found")
        written_set = set(job["written_rows"])
        for row in job["rows"]:
            if row not in written_set:
                job["written_rows"].append(row)
                written_set.add(row)
        job["crashed"] = False
        job["success"] = True
        ended_at = self._now_iso()
        duration_ms = int((datetime.fromisoformat(ended_at.replace("Z", "+00:00")) - datetime.fromisoformat(job["started_at"].replace("Z", "+00:00"))).total_seconds() * 1000)
        self._append_audit({"event_type": "export_completed", "job_id": job_id, "requester_id": job["requester_id"], "row_count": len(job["written_rows"]), "duration_ms": duration_ms, "success": True, "timestamp": ended_at})
        return Response(200, {"job_id": job_id, "written_rows": len(job["written_rows"])}, {"correlation_id": correlation_id})

    def _takeover_lock(self, job_id: str, body: dict[str, Any], correlation_id: str) -> Response:
        lock = self.state["payout_locks"].get(job_id)
        if lock is None:
            raise ServiceError(404, "NOT_FOUND", "lock not found")
        stale_cutoff = self._now() - timedelta(minutes=5)
        acquired_at = datetime.fromisoformat(lock["acquired_at"].replace("Z", "+00:00"))
        if acquired_at >= stale_cutoff:
            raise ServiceError(409, "STATE_CONFLICT", "lock not stale")
        if lock["successor"] is not None:
            raise ServiceError(409, "STATE_CONFLICT", "successor already acquired")
        lock["successor"] = body.get("worker_id")
        return Response(200, {"job_id": job_id, "worker_id": lock["successor"]}, {"correlation_id": correlation_id})

    def _reconciliation_import(self, body: dict[str, Any], correlation_id: str) -> Response:
        checksum = body.get("checksum")
        successful = next((entry for entry in self.state["reconciliation_imports"] if entry["checksum"] == checksum and entry["duplicate"] is False), None)
        if successful is not None:
            record = {"checksum": checksum, "duplicate": True, "applied": False}
            self.state["reconciliation_imports"].append(record)
            return Response(200, record, {"correlation_id": correlation_id})
        record = {"checksum": checksum, "duplicate": False, "applied": True}
        self.state["reconciliation_imports"].append(record)
        return Response(201, record, {"correlation_id": correlation_id})

    def _execution_job(self, body: dict[str, Any], correlation_id: str) -> Response:
        job_id = body.get("job_id") or self._next_id("job", "exec")
        result = body.get("result", "SUCCEEDED")
        start = {"event_type": "execution_job_started", "job_id": job_id, "result": result, "timestamp": self._now_iso()}
        end = {"event_type": "execution_job_ended", "job_id": job_id, "result": result, "timestamp": self._now_iso()}
        self._append_audit(start)
        self._append_audit(end)
        self.state["execution_jobs"][job_id] = {"job_id": job_id, "result": result}
        return Response(200, {"job_id": job_id, "result": result}, {"correlation_id": correlation_id})

    def _open_circuit(self, correlation_id: str) -> Response:
        circuit = self.state["provider_circuit"]
        if not circuit["is_open"]:
            circuit["is_open"] = True
            circuit["open_interval"] += 1
            interval = circuit["open_interval"]
            self._append_audit({"event_type": "provider_circuit_open_alert", "open_interval": interval, "timestamp": self._now_iso()})
            circuit["alert_emitted_for_interval"].append(interval)
        return Response(200, {"is_open": True}, {"correlation_id": correlation_id})

    def _close_circuit(self, correlation_id: str) -> Response:
        self.state["provider_circuit"]["is_open"] = False
        return Response(200, {"is_open": False}, {"correlation_id": correlation_id})

    def _manual_override(self, payment_id: str, actor: dict[str, Any], body: dict[str, Any], correlation_id: str) -> Response:
        reason = body.get("reason", "")
        if not reason:
            raise ServiceError(422, "VALIDATION_ERROR", "manual override reason required")
        self._payment(payment_id)
        self._append_audit({"event_type": "manual_override", "actor_id": actor["actor_id"], "affected_entity_id": payment_id, "reason": reason, "timestamp": self._now_iso()})
        return Response(200, {"payment_id": payment_id}, {"correlation_id": correlation_id})

    def _reconciliation_check(self, body: dict[str, Any], correlation_id: str) -> Response:
        batch_id = body.get("batch_id")
        if body.get("mismatch"):
            metric = {"name": "reconciliation_mismatch_count", "value": 1, "batch_id": batch_id, "timestamp": self._now_iso()}
            self.state["metrics"].append(metric)
            case_id = self._next_id("review_case", "review")
            self.state["review_cases"][case_id] = {"review_case_id": case_id, "batch_id": batch_id}
        return Response(200, {"batch_id": batch_id}, {"correlation_id": correlation_id})

    def _record_guardrail_block(self, context: dict[str, Any], decision: dict[str, Any]) -> None:
        record = {
            "guardrail_id": decision.get("guardrail_id"),
            "requirement_id": decision.get("requirement_id"),
            "actor_id": context["actor"].get("actor_id"),
            "reason": decision.get("reason"),
            "timestamp": self._now_iso(),
        }
        self.state["guardrail_violations"].append(record)
        self._append_audit({"event_type": "guardrail_violation", **record})

    def _change_payment_status(self, payment: dict[str, Any], new_status: str, actor_id: str) -> None:
        old_status = payment["status"]
        payment["status"] = new_status
        payment["updated_at"] = self._now_iso()
        self._append_audit({"event_type": "payment_status_changed", "payment_id": payment["payment_id"], "old_status": old_status, "new_status": new_status, "actor_id": actor_id, "timestamp": self._now_iso()})

    def _record_approval_latency_if_needed(self, payment: dict[str, Any], actor_id: str) -> None:
        if payment.get("terminal_decision_recorded"):
            return
        submitted_at = payment.get("submitted_at")
        if submitted_at is None:
            return
        start = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        duration_ms = int((self._now() - start).total_seconds() * 1000)
        self.state["metrics"].append({"name": "approval_latency_ms", "payment_id": payment["payment_id"], "value": duration_ms, "actor_id": actor_id, "timestamp": self._now_iso()})
        payment["terminal_decision_recorded"] = True

    def _audit_permission_denial(self, actor_id: str, payment_id: str, reason_code: str) -> None:
        self._append_audit({"event_type": "approval_denied_security", "actor_id": actor_id, "payment_id": payment_id, "reason_code": reason_code, "timestamp": self._now_iso()})

    def _append_audit(self, event: dict[str, Any]) -> None:
        self.state["audit_events"].append(copy.deepcopy(event))

    def _append_log(self, log_entry: dict[str, Any]) -> None:
        self.state["logs"].append(self._sanitize(copy.deepcopy(log_entry)))

    def _log_request(self, context: dict[str, Any], response: Response) -> None:
        self._append_log(
            {
                "log_type": "request",
                "correlation_id": context["correlation_id"],
                "method": context["method"],
                "path": context["path"],
                "actor_id": context["actor"].get("actor_id"),
                "outcome": response.status_code,
                "headers": context["headers"],
                "body": context["body"],
                "query": context["query"],
            }
        )

    def _resolve_actor(self, headers: dict[str, str]) -> dict[str, Any]:
        token = headers.get("X-Session-Token")
        if token is not None:
            actor = self.state["users"].get(token)
            if actor is None:
                return {"actor_id": "unknown", "roles": [], "tenant_id": "tenant-a", "active": False}
            return copy.deepcopy(actor)
        if headers.get("X-Service-Account"):
            return {"actor_id": headers.get("X-Service-Account"), "roles": ["service_account"], "tenant_id": "tenant-a", "active": True}
        return {"actor_id": "anonymous", "roles": [], "tenant_id": "tenant-a", "active": False}

    def _require_active_session(self, actor: dict[str, Any]) -> None:
        if not actor.get("active", False):
            raise ServiceError(401, "UNAUTHORIZED", "inactive session token")

    def _payment(self, payment_id: str) -> dict[str, Any]:
        payment = self.state["payments"].get(payment_id)
        if payment is None:
            raise ServiceError(404, "NOT_FOUND", "payment not found")
        return payment

    def _response(self, status_code: int, code: str, message: str, correlation_id: str, details: dict[str, Any] | None = None) -> Response:
        return Response(status_code, {"error": {"code": code, "message": message, "details": details or {}}}, {"correlation_id": correlation_id})

    def _sanitize(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._sanitize_field(key, inner) for key, inner in value.items()}
        if isinstance(value, list):
            return [self._sanitize(item) for item in value]
        if isinstance(value, str):
            return self._sanitize_string(value)
        return value

    def _sanitize_field(self, key: str, value: Any) -> Any:
        if key == "email" and isinstance(value, str):
            return hashlib.sha256(f"ic-sqits::{value}".encode()).hexdigest()
        if key == "account_number":
            return self._mask_account_number(str(value))
        if key == "routing_number":
            return "***MASKED***"
        return self._sanitize(value)

    def _sanitize_string(self, value: str) -> str:
        value = value.replace(self.state["secrets"]["payment_api_key"], "[REDACTED_SECRET]")
        if re.fullmatch(r"\d{16}", value):
            return self._mask_account_number(value)
        return value

    def _mask_account_number(self, value: str | None) -> str | None:
        if value is None:
            return None
        digits = re.sub(r"\D", "", value)
        if len(digits) < 4:
            return "***"
        return f"****{digits[-4:]}"

    def _validate_schedule(self, scheduled_execution_at: str) -> None:
        scheduled = datetime.fromisoformat(scheduled_execution_at.replace("Z", "+00:00"))
        request_time = self._now()
        if scheduled.date() < request_time.date():
            raise ServiceError(422, "VALIDATION_ERROR", "scheduled date before request date")
        if scheduled.date() > (request_time + timedelta(days=30)).date():
            raise ServiceError(422, "VALIDATION_ERROR", "scheduled date more than 30 days after request date")

    def _is_mutating(self, method: str, path: str) -> bool:
        return method in {"POST", "PUT", "PATCH", "DELETE"}

    def _path_id(self, path: str) -> str:
        return path.split("/")[2]

    def _control_resource_id(self, path: str) -> str:
        return path.split("/")[3]
