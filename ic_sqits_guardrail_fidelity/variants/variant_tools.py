import csv
import difflib
import json
import re
from pathlib import Path


APPROVED_STATUSES = {"A", "APPROVED", "Approved", "approved"}


def approved_rows(plan_path: str | Path) -> list[dict[str, str]]:
    plan_path = Path(plan_path)
    rows = _load_rows(plan_path)
    approved = [row for row in rows if row.get("Approval-Status") in APPROVED_STATUSES]
    _sync_variants(plan_path.parent, approved)
    return approved


def materialize_variant(manifest_path: str | Path, output_dir: str | Path) -> Path:
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    repo_root = manifest_path.parents[4]
    baseline_path = repo_root / manifest["source_file"]
    text = baseline_path.read_text()
    mutated = _apply_operations(text, manifest["operations"], manifest["mutation_id"])
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "service.py"
    output_path.write_text(mutated)
    return output_path


def _load_rows(plan_path: Path) -> list[dict[str, str]]:
    with plan_path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _sync_variants(repo_root: Path, rows: list[dict[str, str]]) -> None:
    baseline_path = repo_root / "application" / "reference" / "service.py"
    baseline_text = baseline_path.read_text()
    violating_root = repo_root / "variants" / "violating"

    for row in rows:
        variant_dir = violating_root / row["requirement_id"] / row["mutation_id"]
        variant_dir.mkdir(parents=True, exist_ok=True)
        operations = _operations_for_row(row)
        mutated_text = _apply_operations(baseline_text, operations, row["mutation_id"])
        manifest = {
            "mutation_id": row["mutation_id"],
            "requirement_id": row["requirement_id"],
            "target_obligation_id": row["target_obligation_id"],
            "code_area": row["code_area"],
            "expected_behavioral_difference": row["expected_behavioral_difference"],
            "possible_collateral_effects": row["possible_collateral_effects"],
            "difficulty": row["difficulty"],
            "variant_type": "violating",
            "source_file": "application/reference/service.py",
            "operations": operations,
        }
        (variant_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        (variant_dir / "service.py").write_text(mutated_text)
        diff_lines = difflib.unified_diff(
            baseline_text.splitlines(keepends=True),
            mutated_text.splitlines(keepends=True),
            fromfile="a/application/reference/service.py",
            tofile=f"b/variants/violating/{row['requirement_id']}/{row['mutation_id']}/service.py",
        )
        diff_text = "".join(diff_lines)
        if not diff_text.strip():
            raise ValueError(f"empty diff for {row['mutation_id']}")
        (variant_dir / "diff.patch").write_text(diff_text)


def _apply_operations(text: str, operations: list[dict[str, str]], mutation_id: str) -> str:
    for operation in operations:
        search = operation["search"]
        replace = operation["replace"]
        if search not in text:
            raise ValueError(f"missing search text for {mutation_id}: {operation['note']}")
        text = text.replace(search, replace, 1)
    return text


def _op(note: str, search: str, replace: str) -> dict[str, str]:
    return {"kind": "replace", "note": note, "search": search, "replace": _normalize_replace(search, replace)}


def _normalize_replace(search: str, replace: str) -> str:
    stripped = replace.strip()
    if not stripped.startswith("# mutation"):
        return replace
    indent_match = re.match(r"(\s*)", search)
    indent = indent_match.group(1) if indent_match else ""
    return f"{indent}pass  {stripped}\n"


def _operations_for_row(row: dict[str, str]) -> list[dict[str, str]]:
    mutation_id = row["mutation_id"]
    operations = MUTATION_OPERATIONS.get(mutation_id)
    if operations is None:
        raise KeyError(f"no operations configured for {mutation_id}")
    return operations


MUTATION_OPERATIONS = {
    "R001_M01": [
        _op(
            "remove approver role gate",
            """        if \"approver\" not in roles:\n            self._audit_permission_denial(actor[\"actor_id\"], payment_id, \"missing_approver_role\")\n            raise ServiceError(403, \"FORBIDDEN\", \"approver role required\")\n""",
            """        # mutation R001_M01: approver role gate removed\n""",
        )
    ],
    "R001_M02": [
        _op(
            "break self-approval comparison",
            '        if payment["creator_user_id"] == actor["actor_id"]:\n',
            '        if payment["payment_id"] == actor["actor_id"]:\n',
        )
    ],
    "R002_M01": [
        _op(
            "bypass distinct approver count",
            '            if len(distinct) < 2 or not finance:\n',
            '            if not finance:\n',
        )
    ],
    "R002_M03": [
        _op(
            "skip finance manager prerequisite",
            '            if len(distinct) < 2 or not finance:\n',
            '            if len(distinct) < 2:\n',
        )
    ],
    "R003_M01": [
        _op(
            "remove void actor authorization",
            """        if payment[\"creator_user_id\"] != actor[\"actor_id\"] and \"admin\" not in actor[\"roles\"]:\n            raise ServiceError(403, \"FORBIDDEN\", \"void not allowed\")\n""",
            """        # mutation R003_M01: void actor authorization removed\n""",
        )
    ],
    "R003_M03": [
        _op(
            "omit payment_voided audit event",
            '        self._append_audit({"event_type": "payment_voided", "payment_id": payment_id, "actor_id": actor["actor_id"]})\n',
            '        # mutation R003_M03: payment_voided audit omitted\n',
        )
    ],
    "R004_M01": [
        _op(
            "skip active-session guard",
            '        self._require_active_session(actor)\n',
            '',
        ),
        _op(
            "remove inline inactive-token rejection",
            """        if not actor[\"active\"]:\n            raise ServiceError(401, \"UNAUTHORIZED\", \"inactive session token\")\n""",
            """        # mutation R004_M01: inactive actor treated as active\n""",
        ),
    ],
    "R004_M02": [
        _op(
            "skip early active-session guard",
            '        self._require_active_session(actor)\n',
            '',
        ),
        _op(
            "remove pre-append inactive rejection",
            """        if not actor[\"active\"]:\n            raise ServiceError(401, \"UNAUTHORIZED\", \"inactive session token\")\n""",
            """        # mutation R004_M02: inactive rejection moved after approval append\n""",
        ),
        _op(
            "raise 401 after approval append",
            '        self.state["approvals"].append(approval)\n\n        required_count = self.state["payment_type_policies"].get(payment["payment_type"], 1)\n',
            '        self.state["approvals"].append(approval)\n\n        if not actor["active"]:\n            raise ServiceError(401, "UNAUTHORIZED", "inactive session token")\n\n        required_count = self.state["payment_type_policies"].get(payment["payment_type"], 1)\n',
        ),
    ],
    "R005_M01": [
        _op(
            "expose full account number in summary",
            '                "account_number": self._mask_account_number(beneficiary.get("account_number")),\n',
            '                "account_number": beneficiary.get("account_number"),\n',
        )
    ],
    "R005_M03": [
        _op(
            "return confidential comments",
            '            "approval_comments": [entry["text"] for entry in payment["approval_comments"] if not entry.get("confidential")],\n',
            '            "approval_comments": [entry["text"] for entry in payment["approval_comments"]],\n',
        )
    ],
    "R007_M01": [
        _op(
            "skip delegation end-time validation",
            '            if actor["actor_id"] != delegation["delegate_user_id"] or not (starts_at <= now <= ends_at):\n',
            '            if actor["actor_id"] != delegation["delegate_user_id"] or now < starts_at:\n',
        )
    ],
    "R007_M03": [
        _op(
            "allow chained delegation",
            '            if actor["actor_id"] == source["delegate_user_id"]:\n',
            '            if False and actor["actor_id"] == source["delegate_user_id"]:\n',
        )
    ],
    "R008_M01": [
        _op(
            "remove treasury role check",
            """        if \"treasury\" not in actor[\"roles\"]:\n            raise ServiceError(403, \"FORBIDDEN\", \"treasury role required\")\n""",
            """        # mutation R008_M01: treasury role check removed\n""",
        )
    ],
    "R008_M02": [
        _op(
            "skip incident ticket lookup",
            """        incident_ticket_id = body.get(\"incident_ticket_id\")\n        if incident_ticket_id not in self.state[\"incident_tickets\"]:\n            raise ServiceError(404, \"NOT_FOUND\", \"incident ticket not found\")\n""",
            """        incident_ticket_id = body.get(\"incident_ticket_id\")\n        # mutation R008_M02: incident ticket lookup skipped\n""",
        )
    ],
    "R010_M01": [
        _op(
            "remove mTLS allowlist check",
            '        if not service_account or subject not in self.state["approved_mtls_subjects"]:\n',
            '        if not service_account:\n',
        )
    ],
    "R010_M02": [
        _op(
            "trust service-account name instead of subject",
            '        if not service_account or subject not in self.state["approved_mtls_subjects"]:\n',
            '        if not service_account or service_account != "svc_ok":\n',
        )
    ],
    "R011_M01": [
        _op(
            "skip account-number masking in logs",
            '            return self._mask_account_number(str(value))\n',
            '            return str(value)\n',
        )
    ],
    "R011_M03": [
        _op(
            "log raw account number on exception path",
            '                    "message": f"internal error: {type(exc).__name__}",\n',
            '                    "message": f"internal error: {type(exc).__name__} 1111222233334444",\n',
        )
    ],
    "R012_M01": [
        _op(
            "remove status-change audit event",
            '        self._append_audit({"event_type": "payment_status_changed", "payment_id": payment["payment_id"], "old_status": old_status, "new_status": new_status, "actor_id": actor_id, "timestamp": self._now_iso()})\n',
            '        # mutation R012_M01: status-change audit omitted\n',
        )
    ],
    "R012_M02": [
        _op(
            "misattribute actor in status audit",
            '        self._append_audit({"event_type": "payment_status_changed", "payment_id": payment["payment_id"], "old_status": old_status, "new_status": new_status, "actor_id": actor_id, "timestamp": self._now_iso()})\n',
            '        self._append_audit({"event_type": "payment_status_changed", "payment_id": payment["payment_id"], "old_status": old_status, "new_status": new_status, "actor_id": payment["creator_user_id"], "timestamp": self._now_iso()})\n',
        )
    ],
    "R013_M01": [
        _op(
            "stop redacting secret in logs",
            '        value = value.replace(self.state["secrets"]["payment_api_key"], "[REDACTED_SECRET]")\n',
            '        value = value\n',
        )
    ],
    "R013_M02": [
        _op(
            "emit raw exception string containing secret",
            '                    "message": f"internal error: {type(exc).__name__}",\n',
            '                    "message": f"internal error: {exc}",\n',
        )
    ],
    "R014_M01": [
        _op(
            "drop security denial audit event",
            '        self._append_audit({"event_type": "approval_denied_security", "actor_id": actor_id, "payment_id": payment_id, "reason_code": reason_code, "timestamp": self._now_iso()})\n',
            '        # mutation R014_M01: denial audit omitted\n',
        )
    ],
    "R014_M02": [
        _op(
            "use wrong denial event type",
            '        self._append_audit({"event_type": "approval_denied_security", "actor_id": actor_id, "payment_id": payment_id, "reason_code": reason_code, "timestamp": self._now_iso()})\n',
            '        self._append_audit({"event_type": "security_denied", "actor_id": actor_id, "payment_id": payment_id, "reason_code": reason_code, "timestamp": self._now_iso()})\n',
        )
    ],
    "R016_M01": [
        _op(
            "shift document expiry by one minute",
            '        if self._now() > datetime.fromisoformat(token["expires_at"].replace("Z", "+00:00")):\n',
            '        if self._now() > datetime.fromisoformat(token["expires_at"].replace("Z", "+00:00")) + timedelta(minutes=1):\n',
        )
    ],
    "R016_M03": [
        _op(
            "omit document_token_expired audit event",
            '            self._append_audit({"event_type": "document_token_expired", "document_id": document_id, "token_id": token_id})\n',
            '            # mutation R016_M03: document_token_expired audit omitted\n',
        )
    ],
    "R018_M01": [
        _op(
            "omit reconciliation download audit",
            '        self._append_audit(event)\n',
            '        # mutation R018_M01: reconciliation download audit omitted\n',
        )
    ],
    "R018_M03": [
        _op(
            "use wrong requester identity in reconciliation audit",
            '            "actor_id": actor["actor_id"],\n',
            '            "actor_id": "report_owner",\n',
        )
    ],
    "R019_M01": [
        _op(
            "log raw email instead of hash",
            '        self._append_log({"log_type": "search", "correlation_id": correlation_id, "email_hash": salted_hash})\n',
            '        self._append_log({"log_type": "search", "correlation_id": correlation_id, "email": email})\n',
        )
    ],
    "R019_M02": [
        _op(
            "remove salt from email hash",
            '        salted_hash = hashlib.sha256(f"ic-sqits::{email}".encode()).hexdigest()\n',
            '        salted_hash = hashlib.sha256(email.encode()).hexdigest()\n',
        )
    ],
    "R020_M01": [
        _op(
            "audit only successful provider-config reads",
            '        self._append_audit({"event_type": "provider_config_read", "actor_id": actor["actor_id"], "outcome": outcome, "config_name": config_name})\n',
            '        if outcome == "allowed":\n            self._append_audit({"event_type": "provider_config_read", "actor_id": actor["actor_id"], "outcome": outcome, "config_name": config_name})\n',
        )
    ],
    "R020_M02": [
        _op(
            "force provider-config audit outcome to allowed",
            '        outcome = "allowed" if "provider_config_reader" in actor["roles"] else "denied"\n',
            '        outcome = "allowed"\n',
        )
    ],
    "R021_M01": [
        _op(
            "allow non-positive amounts",
            '        if amount <= 0 or amount > Decimal("100000"):\n',
            '        if amount > Decimal("100000"):\n',
        )
    ],
    "R021_M02": [
        _op(
            "remove upper bound check",
            '        if amount <= 0 or amount > Decimal("100000"):\n',
            '        if amount <= 0:\n',
        )
    ],
    "R024_M01": [
        _op(
            "remove lower bound on scheduled date",
            """        if scheduled.date() < request_time.date():\n            raise ServiceError(422, \"VALIDATION_ERROR\", \"scheduled date before request date\")\n""",
            """        # mutation R024_M01: lower schedule bound removed\n""",
        )
    ],
    "R024_M02": [
        _op(
            "remove upper bound on scheduled date",
            """        if scheduled.date() > (request_time + timedelta(days=30)).date():\n            raise ServiceError(422, \"VALIDATION_ERROR\", \"scheduled date more than 30 days after request date\")\n""",
            """        # mutation R024_M02: upper schedule bound removed\n""",
        )
    ],
    "R025_M01": [
        _op(
            "require comment on approvals",
            '                if approval["payment_id"] == payment_id and approval["actor_id"] == actor["actor_id"] and approval.get("command_id") == command_id:\n                    return Response(200, {"payment_id": payment_id, "status": payment["status"], "duplicate": True}, {"correlation_id": correlation_id})\n\n        delegate_for = None\n',
            '                if approval["payment_id"] == payment_id and approval["actor_id"] == actor["actor_id"] and approval.get("command_id") == command_id:\n                    return Response(200, {"payment_id": payment_id, "status": payment["status"], "duplicate": True}, {"correlation_id": correlation_id})\n\n        if not body.get("comment"):\n            raise ServiceError(422, "VALIDATION_ERROR", "approval comment required", {"comment": "required"})\n\n        delegate_for = None\n',
        )
    ],
    "R025_M02": [
        _op(
            "remove rejection comment minimum length",
            '        if not (10 <= len(comment) <= 500):\n',
            '        if len(comment) > 500:\n',
        )
    ],
    "R026_M01": [
        _op(
            "accept both IBAN and account/routing pair",
            '        if has_iban == has_pair:\n',
            '        if not has_iban and not has_pair:\n',
        )
    ],
    "R026_M02": [
        _op(
            "reject valid account/routing pair",
            '        if has_iban == has_pair:\n',
            '        if not has_iban:\n',
        )
    ],
    "R027_M01": [
        _op(
            "skip attachment content-type validation",
            """        if body.get(\"content_type\") not in {\"pdf\", \"png\"}:\n            raise ServiceError(422, \"VALIDATION_ERROR\", \"attachment type not allowed\")\n""",
            """        # mutation R027_M01: attachment content-type validation removed\n""",
        )
    ],
    "R027_M02": [
        _op(
            "skip attachment max-size check",
            """        if int(body.get(\"size_bytes\", 0)) > 5 * 1024 * 1024:\n            raise ServiceError(422, \"VALIDATION_ERROR\", \"attachment too large\")\n""",
            """        # mutation R027_M02: attachment max-size validation removed\n""",
        )
    ],
    "R028_M01": [
        _op(
            "allow empty batch",
            '        if not (1 <= len(items) <= 100):\n',
            '        if len(items) > 100:\n',
        )
    ],
    "R028_M03": [
        _op(
            "allow duplicate client references",
            """        refs = [item.get(\"client_reference\") for item in items]\n        if len(refs) != len(set(refs)):\n            raise ServiceError(422, \"VALIDATION_ERROR\", \"duplicate client_reference\")\n""",
            """        refs = [item.get(\"client_reference\") for item in items]\n        # mutation R028_M03: duplicate client_reference validation removed\n""",
        )
    ],
    "R029_M01": [
        _op(
            "accept non-allowlisted hostname",
            '        if parsed.scheme != "https" or parsed.hostname not in self.state["tenant_allowlists"].get(tenant_id, []):\n',
            '        if parsed.scheme != "https":\n',
        )
    ],
    "R029_M02": [
        _op(
            "accept http callback URL",
            '        if parsed.scheme != "https" or parsed.hostname not in self.state["tenant_allowlists"].get(tenant_id, []):\n',
            '        if parsed.hostname not in self.state["tenant_allowlists"].get(tenant_id, []):\n',
        )
    ],
    "R030_M01": [
        _op(
            "ignore prior approved refunds in remaining balance",
            '        remaining = Decimal(payment["captured_amount"]) - Decimal(payment["approved_refund_total"])\n',
            '        remaining = Decimal(payment["captured_amount"])\n',
        )
    ],
    "R030_M02": [
        _op(
            "double count prior refunds and over-reject",
            '        remaining = Decimal(payment["captured_amount"]) - Decimal(payment["approved_refund_total"])\n',
            '        remaining = Decimal(payment["captured_amount"]) - Decimal(payment["approved_refund_total"]) - sum(Decimal(entry["amount"]) for entry in payment.get("refunds", []))\n',
        )
    ],
    "R031_M01": [
        _op(
            "remove line-item submit precondition",
            '        if payment["status"] != "DRAFT" or not payment["line_items"] or not beneficiary["verified"]:\n',
            '        if payment["status"] != "DRAFT" or not beneficiary["verified"]:\n',
        )
    ],
    "R031_M02": [
        _op(
            "remove beneficiary verification submit precondition",
            '        if payment["status"] != "DRAFT" or not payment["line_items"] or not beneficiary["verified"]:\n',
            '        if payment["status"] != "DRAFT" or not payment["line_items"]:\n',
        )
    ],
    "R032_M01": [
        _op(
            "hardcode approval threshold to one",
            '        required_count = self.state["payment_type_policies"].get(payment["payment_type"], 1)\n',
            '        required_count = 1\n',
        )
    ],
    "R032_M03": [
        _op(
            "count duplicate approvals toward threshold",
            '        current_count = len({entry["actor_id"] for entry in self.state["approvals"] if entry["payment_id"] == payment_id and entry["decision"] == "APPROVE"})\n',
            '        current_count = len([entry for entry in self.state["approvals"] if entry["payment_id"] == payment_id and entry["decision"] == "APPROVE"])\n',
        )
    ],
    "R033_M01": [
        _op(
            "remove executed-payment mutable-field allowlist",
            """        if payment[\"status\"] == \"EXECUTED\":\n            disallowed = [key for key in body if key != \"reconciliation_note\"]\n            if disallowed:\n                raise ServiceError(409, \"STATE_CONFLICT\", \"only reconciliation_note may change after execution\")\n""",
            """        # mutation R033_M01: executed-payment field allowlist removed\n""",
        )
    ],
    "R033_M02": [
        _op(
            "reject reconciliation_note updates too",
            '            disallowed = [key for key in body if key != "reconciliation_note"]\n',
            '            disallowed = [key for key in body]\n',
        )
    ],
    "R034_M01": [
        _op(
            "leave scheduled execution time unchanged on reject",
            '        payment["scheduled_execution_at"] = None\n',
            '        # mutation R034_M01: scheduled_execution_at left unchanged\n',
        )
    ],
    "R034_M02": [
        _op(
            "skip REJECTED status transition",
            '        self._change_payment_status(payment, "REJECTED", actor["actor_id"])\n',
            '        payment["updated_at"] = self._now_iso()\n',
        )
    ],
    "R036_M01": [
        _op(
            "allow APPROVED payment cancellation",
            '        if payment["status"] not in {"DRAFT", "SUBMITTED"}:\n',
            '        if payment["status"] not in {"DRAFT", "SUBMITTED", "APPROVED"}:\n',
        )
    ],
    "R036_M02": [
        _op(
            "mutate canceled status before returning conflict",
            """        if payment[\"status\"] not in {\"DRAFT\", \"SUBMITTED\"}:\n            raise ServiceError(409, \"STATE_CONFLICT\", \"payment cannot be canceled\")\n""",
            """        if payment[\"status\"] not in {\"DRAFT\", \"SUBMITTED\"}:\n            self._change_payment_status(payment, \"CANCELED\", actor[\"actor_id\"])\n            raise ServiceError(409, \"STATE_CONFLICT\", \"payment cannot be canceled\")\n""",
        )
    ],
    "R037_M01": [
        _op(
            "skip delegated-task expiry invalidation",
            '            if task["status"] == "PENDING" and now > datetime.fromisoformat(task["expires_at"].replace("Z", "+00:00")):\n',
            '            if False and task["status"] == "PENDING" and now > datetime.fromisoformat(task["expires_at"].replace("Z", "+00:00")):\n',
        )
    ],
    "R037_M02": [
        _op(
            "omit delegation_expired event",
            '                self._append_audit({"event_type": "delegation_expired", "task_id": task["task_id"], "timestamp": self._now_iso()})\n',
            '                # mutation R037_M02: delegation_expired audit omitted\n',
        )
    ],
    "R038_M01": [
        _op(
            "do not set dispute OPEN on chargeback",
            '        payment["dispute_status"] = "OPEN"\n',
            '        payment["dispute_status"] = "NONE"\n',
        )
    ],
    "R038_M02": [
        _op(
            "ignore dispute status when creating refund",
            """        if payment[\"dispute_status\"] == \"OPEN\":\n            raise ServiceError(409, \"STATE_CONFLICT\", \"refund blocked during dispute\")\n""",
            """        # mutation R038_M02: dispute-status refund block removed\n""",
        )
    ],
    "R040_M01": [
        _op(
            "transition to REFUNDED after any positive refund",
            """        if Decimal(payment[\"approved_refund_total\"]) == Decimal(payment[\"captured_amount\"]):\n            self._change_payment_status(payment, \"REFUNDED\", \"system\")\n""",
            """        if amount > 0:\n            self._change_payment_status(payment, \"REFUNDED\", \"system\")\n""",
        )
    ],
    "R040_M02": [
        _op(
            "never transition to REFUNDED",
            """        if Decimal(payment[\"approved_refund_total\"]) == Decimal(payment[\"captured_amount\"]):\n            self._change_payment_status(payment, \"REFUNDED\", \"system\")\n""",
            """        # mutation R040_M02: full refund no longer changes status\n""",
        )
    ],
    "R041_M01": [
        _op(
            "skip idempotency key lookup",
            """        existing = self.state[\"idempotency_keys\"].get(idem_key)\n        if existing is not None:\n            if existing[\"body_hash\"] != body_hash:\n                raise ServiceError(409, \"IDEMPOTENCY_CONFLICT\", \"idempotency key reused with different body\")\n            payment = self.state[\"payments\"][existing[\"payment_id\"]]\n            return Response(200, {\"payment_id\": payment[\"payment_id\"], \"status\": payment[\"status\"]}, {\"correlation_id\": correlation_id})\n""",
            """        existing = None\n""",
        )
    ],
    "R041_M03": [
        _op(
            "use unstable JSON serialization for idempotency hash",
            '        canonical_body = json.dumps(body, sort_keys=True)\n',
            '        canonical_body = json.dumps(body)\n',
        )
    ],
    "R042_M01": [
        _op(
            "allow reused idempotency key with different body to create second payment",
            """        existing = self.state[\"idempotency_keys\"].get(idem_key)\n        if existing is not None:\n            if existing[\"body_hash\"] != body_hash:\n                raise ServiceError(409, \"IDEMPOTENCY_CONFLICT\", \"idempotency key reused with different body\")\n            payment = self.state[\"payments\"][existing[\"payment_id\"]]\n            return Response(200, {\"payment_id\": payment[\"payment_id\"], \"status\": payment[\"status\"]}, {\"correlation_id\": correlation_id})\n""",
            """        existing = self.state[\"idempotency_keys\"].get(idem_key)\n        if existing is not None and existing[\"body_hash\"] == body_hash:\n            payment = self.state[\"payments\"][existing[\"payment_id\"]]\n            return Response(200, {\"payment_id\": payment[\"payment_id\"], \"status\": payment[\"status\"]}, {\"correlation_id\": correlation_id})\n""",
        )
    ],
    "R042_M02": [
        _op(
            "treat different-body reuse as identical replay",
            '            if existing["body_hash"] != body_hash:\n                raise ServiceError(409, "IDEMPOTENCY_CONFLICT", "idempotency key reused with different body")\n',
            '            if existing["body_hash"] != body_hash:\n                payment = self.state["payments"][existing["payment_id"]]\n                return Response(200, {"payment_id": payment["payment_id"], "status": payment["status"]}, {"correlation_id": correlation_id})\n',
        )
    ],
    "R043_M01": [
        _op(
            "remove approval command dedupe",
            """        if command_id:\n            for approval in self.state[\"approvals\"]:\n                if approval[\"payment_id\"] == payment_id and approval[\"actor_id\"] == actor[\"actor_id\"] and approval.get(\"command_id\") == command_id:\n                    return Response(200, {\"payment_id\": payment_id, \"status\": payment[\"status\"], \"duplicate\": True}, {\"correlation_id\": correlation_id})\n""",
            """        # mutation R043_M01: approval command dedupe removed\n""",
        )
    ],
    "R043_M03": [
        _op(
            "clear stored command_id so later retries look new",
            '            "command_id": command_id,\n',
            '            "command_id": None,\n',
        )
    ],
    "R044_M01": [
        _op(
            "skip provider receipt dedupe check",
            """        if message_id in self.state[\"provider_receipts\"]:\n            self._append_audit({\"event_type\": \"duplicate_ignored\", \"message_id\": message_id, \"timestamp\": self._now_iso()})\n            return Response(200, {\"duplicate\": True}, {\"correlation_id\": correlation_id})\n""",
            """        # mutation R044_M01: provider receipt dedupe removed\n""",
        )
    ],
    "R044_M02": [
        _op(
            "omit duplicate_ignored event",
            '            self._append_audit({"event_type": "duplicate_ignored", "message_id": message_id, "timestamp": self._now_iso()})\n',
            '            # mutation R044_M02: duplicate_ignored audit omitted\n',
        )
    ],
    "R045_M01": [
        _op(
            "broaden retry window beyond baseline slice",
            '        for index, status_code in enumerate(responses[:3], start=1):\n',
            '        for index, status_code in enumerate(responses[:4], start=1):\n',
        )
    ],
    "R045_M03": [
        _op(
            "keep retrying after first success",
            """            if 200 <= int(status_code) < 300:\n                break\n""",
            """            if 200 <= int(status_code) < 300:\n                continue\n""",
        )
    ],
    "R046_M01": [
        _op(
            "allocate new job_id on export restart",
            """    def _restart_export(self, job_id: str, correlation_id: str) -> Response:\n        job = self.state[\"export_jobs\"].get(job_id)\n""",
            """    def _restart_export(self, job_id: str, correlation_id: str) -> Response:\n        original_job_id = job_id\n        job = self.state[\"export_jobs\"].get(original_job_id)\n        job_id = self._next_id(\"job\", \"export\")\n        if job is not None:\n            self.state[\"export_jobs\"][job_id] = job\n""",
        )
    ],
    "R046_M02": [
        _op(
            "replay already written rows on restart",
            """        written_set = set(job[\"written_rows\"])\n        for row in job[\"rows\"]:\n            if row not in written_set:\n                job[\"written_rows\"].append(row)\n                written_set.add(row)\n""",
            """        for row in job[\"rows\"]:\n            job[\"written_rows\"].append(row)\n""",
        )
    ],
    "R047_M01": [
        _op(
            "loosen stale-lock threshold to one minute",
            '        stale_cutoff = self._now() - timedelta(minutes=5)\n',
            '        stale_cutoff = self._now() - timedelta(minutes=1)\n',
        )
    ],
    "R047_M02": [
        _op(
            "remove single-successor lock gate",
            """        if lock[\"successor\"] is not None:\n            raise ServiceError(409, \"STATE_CONFLICT\", \"successor already acquired\")\n""",
            """        # mutation R047_M02: successor exclusivity removed\n""",
        )
    ],
    "R049_M01": [
        _op(
            "compare wrong field for duplicate import detection",
            '        successful = next((entry for entry in self.state["reconciliation_imports"] if entry["checksum"] == checksum and entry["duplicate"] is False), None)\n',
            '        successful = next((entry for entry in self.state["reconciliation_imports"] if entry.get("import_id") == body.get("import_id") and entry["duplicate"] is False), None)\n',
        )
    ],
    "R049_M02": [
        _op(
            "apply repeated checksum a second time",
            """        if successful is not None:\n            record = {\"checksum\": checksum, \"duplicate\": True, \"applied\": False}\n            self.state[\"reconciliation_imports\"].append(record)\n            return Response(200, record, {\"correlation_id\": correlation_id})\n""",
            """        if successful is not None:\n            record = {\"checksum\": checksum, \"duplicate\": False, \"applied\": True}\n            self.state[\"reconciliation_imports\"].append(record)\n            return Response(201, record, {\"correlation_id\": correlation_id})\n""",
        )
    ],
    "R051_M01": [
        _op(
            "drop correlation_id header on error responses",
            '        return Response(status_code, {"error": {"code": code, "message": message, "details": details or {}}}, {"correlation_id": correlation_id})\n',
            '        return Response(status_code, {"error": {"code": code, "message": message, "details": details or {}}}, {})\n',
        )
    ],
    "R051_M02": [
        _op(
            "log request with different correlation_id than response",
            '                "correlation_id": context["correlation_id"],\n',
            '                "correlation_id": self._next_id("request", "corr"),\n',
        )
    ],
    "R053_M01": [
        _op(
            "measure approval latency from creation time",
            '        submitted_at = payment.get("submitted_at")\n',
            '        submitted_at = payment.get("created_at")\n',
        )
    ],
    "R053_M03": [
        _op(
            "record approval latency on first approval attempt",
            '        self.state["approvals"].append(approval)\n\n        required_count = self.state["payment_type_policies"].get(payment["payment_type"], 1)\n',
            '        self.state["approvals"].append(approval)\n        self._record_approval_latency_if_needed(payment, actor["actor_id"])\n\n        required_count = self.state["payment_type_policies"].get(payment["payment_type"], 1)\n',
        )
    ],
    "R054_M01": [
        _op(
            "omit execution_job_started event",
            '        self._append_audit(start)\n',
            '        # mutation R054_M01: execution_job_started omitted\n',
        )
    ],
    "R054_M03": [
        _op(
            "emit wrong job_id in end event",
            '        end = {"event_type": "execution_job_ended", "job_id": job_id, "result": result, "timestamp": self._now_iso()}\n',
            '        end = {"event_type": "execution_job_ended", "job_id": "wrong-job", "result": result, "timestamp": self._now_iso()}\n',
        )
    ],
    "R055_M01": [
        _op(
            "remove requirement_id from guardrail record",
            '            "requirement_id": decision.get("requirement_id"),\n',
            '            "requirement_id": None,\n',
        )
    ],
    "R055_M03": [
        _op(
            "log guardrail violation without persisting record",
            """        self.state[\"guardrail_violations\"].append(record)\n        self._append_audit({\"event_type\": \"guardrail_violation\", **record})\n""",
            """        self._append_log({\"log_type\": \"guardrail_violation\", **record})\n""",
        )
    ],
    "R057_M01": [
        _op(
            "emit provider-circuit alert on every open call",
            '        if not circuit["is_open"]:\n',
            '        if True:\n',
        )
    ],
    "R057_M02": [
        _op(
            "fail to reset open flag on close",
            '        self.state["provider_circuit"]["is_open"] = False\n',
            '        self.state["provider_circuit"]["is_open"] = True\n',
        )
    ],
    "R058_M01": [
        _op(
            "remove manual override reason validation",
            """        if not reason:\n            raise ServiceError(422, \"VALIDATION_ERROR\", \"manual override reason required\")\n""",
            """        # mutation R058_M01: manual override reason may be empty\n""",
        )
    ],
    "R058_M02": [
        _op(
            "omit affected entity ID from manual override audit",
            '        self._append_audit({"event_type": "manual_override", "actor_id": actor["actor_id"], "affected_entity_id": payment_id, "reason": reason, "timestamp": self._now_iso()})\n',
            '        self._append_audit({"event_type": "manual_override", "actor_id": actor["actor_id"], "affected_entity_id": None, "reason": reason, "timestamp": self._now_iso()})\n',
        )
    ],
    "R059_M01": [
        _op(
            "skip reconciliation mismatch metric",
            '            metric = {"name": "reconciliation_mismatch_count", "value": 1, "batch_id": batch_id, "timestamp": self._now_iso()}\n            self.state["metrics"].append(metric)\n',
            '            # mutation R059_M01: reconciliation mismatch metric omitted\n',
        )
    ],
    "R059_M02": [
        _op(
            "skip review case creation on mismatch",
            '            case_id = self._next_id("review_case", "review")\n            self.state["review_cases"][case_id] = {"review_case_id": case_id, "batch_id": batch_id}\n',
            '            # mutation R059_M02: review case omitted\n',
        )
    ],
    "R060_M01": [
        _op(
            "omit export_completed event",
            '        self._append_audit({"event_type": "export_completed", "job_id": job_id, "requester_id": job["requester_id"], "row_count": len(job["written_rows"]), "duration_ms": duration_ms, "success": True, "timestamp": ended_at})\n',
            '        # mutation R060_M01: export_completed event omitted\n',
        )
    ],
    "R060_M03": [
        _op(
            "record worker identity instead of requester_id",
            '        self._append_audit({"event_type": "export_completed", "job_id": job_id, "requester_id": job["requester_id"], "row_count": len(job["written_rows"]), "duration_ms": duration_ms, "success": True, "timestamp": ended_at})\n',
            '        self._append_audit({"event_type": "export_completed", "job_id": job_id, "requester_id": "worker-1", "row_count": len(job["written_rows"]), "duration_ms": duration_ms, "success": True, "timestamp": ended_at})\n',
        )
    ],
}
