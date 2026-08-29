from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from textwrap import dedent

import yaml

from variants.variant_tools import approved_rows


ASSUMPTION_STATUS = "ASSUMPTION_BASED_DRAFT"
ASSUMPTION_APPROVER = "ASSUMED_HUMAN_PER_USER_INSTRUCTION"
ASSUMPTION_DATE = "2026-08-29"
ASSUMPTION_BASIS = "assumption_mode_user_instruction"
NOT_PROTOCOL_VALID = "Not protocol-valid final results"

BOUNDARY_CASES = [
    ("R007", "R007_B01", "delegation_window_edge", "Delegated approval exactly at active-window boundary scenario."),
    ("R016", "R016_B01", "token_expiry_threshold", "Document token scenario pinned at exact 15-minute expiry threshold."),
    ("R021", "R021_B01", "max_amount_threshold", "Payment amount accepted at exact upper bound 100000."),
    ("R024", "R024_B01", "schedule_upper_bound", "Scheduled execution accepted exactly 30 days ahead."),
    ("R026", "R026_B01", "xor_identifier_boundary", "Exactly one valid beneficiary identifier form provided."),
    ("R028", "R028_B01", "batch_size_upper_bound", "Batch payout accepted at exactly 100 unique items."),
    ("R033", "R033_B01", "allowed_field_only", "Executed payment update limited to reconciliation_note only."),
    ("R036", "R036_B01", "forbidden_cancel_no_mutation", "Disallowed cancel path leaves payment status unchanged."),
    ("R040", "R040_B01", "full_refund_boundary", "Refund total exactly equals captured amount and reaches terminal refunded state."),
    ("R045", "R045_B01", "retry_stop_on_success", "Webhook retry sequence stops immediately after first success."),
    ("R047", "R047_B01", "stale_lock_threshold", "Payout lock takeover occurs just beyond stale threshold."),
    ("R057", "R057_B01", "reopen_after_close", "Provider retry circuit reopen emits exactly one fresh alert after close."),
]

STEP_REPORTS = {
    23: ["MUTATION_VALIDATION.csv"],
    24: ["variants/valid_alternatives/VALID_ALTERNATIVE_CORPUS.csv"],
    25: ["variants/boundary/BOUNDARY_CORPUS.csv"],
    26: ["variants/EXPECTED_VERDICTS.csv"],
    27: [
        "experiment/GUARDRAIL_INTERFACE.md",
        "experiment/schema/guardrail_context.schema.json",
        "experiment/schema/guardrail_result.schema.json",
        "experiment/schema/guardrail_artifact_manifest.schema.json",
        "experiment/schema/structured_extraction.schema.json",
        "experiment/schema/l2_validation_record.schema.json",
        "experiment/schema/raw_generation_record.schema.json",
    ],
    28: ["guardrails/human/WORKSHEET_TEMPLATE.yaml", "guardrails/human/worksheet_index.csv", "guardrails/human/worksheets/**"],
    29: ["guardrails/human/H_GUARDRAIL_FREEZE.csv"],
    30: ["prompts/guardrail_generation/L0_PROMPT_v1.md", "prompts/prompt_versions.json"],
    31: ["prompts/structured_extraction/L1_PROMPT_v1.md", "prompts/prompt_versions.json"],
    32: ["prompts/L2_VALIDATION_SPEC.md"],
    33: ["freeze/MODEL_CONFIG_FREEZE.yaml"],
    34: ["pilot/README.md", "pilot/PILOT_SCOPE.yaml", "pilot/PILOT_REQUIREMENTS.csv", "pilot/raw/**"],
    35: ["pilot/PILOT_REPORT.md"],
    36: ["freeze/EXPERIMENT_FREEZE.md", "freeze/hashes.sha256"],
    37: ["raw/generations/L0/index.csv"],
    38: ["raw/generations/L1/index.csv"],
    39: ["guardrails/llm_validated/index.csv"],
    40: ["raw/execution/README.md"],
    41: ["processed/guardrail_level_results.csv"],
    42: ["processed/obligation_level_results.csv"],
    43: ["processed/implementation_level_results.csv"],
    44: ["processed/paraphrase_consistency.csv"],
    45: ["processed/failure_labels.csv"],
    46: ["processed/metrics.json"],
    47: ["final_results/VERIFIED_RESULTS.csv", "final_results/VERIFIED_RESULTS.md", "final_results/NUMBER_PROVENANCE.csv"],
    48: [
        "final_results/RQ1_RESULTS.md",
        "final_results/RQ2_RESULTS.md",
        "final_results/RQ3_RESULTS.md",
        "final_results/RQ4_RESULTS.md",
        "final_results/FAILURE_ANALYSIS.md",
        "final_results/PARAPHRASE_ANALYSIS.md",
        "final_results/VALIDATION_YIELD.md",
        "final_results/LIMITATIONS_FACTS.md",
        "final_results/REPRODUCIBILITY.md",
        "final_results/FINAL_EXPERIMENT_REPORT.md",
    ],
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def assumption_banner() -> str:
    return (
        f"STATUS: {ASSUMPTION_STATUS}\n"
        f"{NOT_PROTOCOL_VALID}.\n"
        "Human-only and unfrozen later-phase decisions were filled under explicit user instruction to assume completion.\n"
        "Use for package assembly and review only, not as protocol-valid final science."
    )


def load_approved_mutations(plan_path: str | Path) -> list[dict[str, str]]:
    return approved_rows(plan_path)


def build_mutation_validation_rows(approved: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for row in approved:
        rows.append(
            {
                "mutation_id": row["mutation_id"],
                "requirement_id": row["requirement_id"],
                "target_obligation_id": row["target_obligation_id"],
                "validation_status": "ASSUMED_VALID_MUTATION",
                "rationale": row["expected_behavioral_difference"],
                "validation_basis": ASSUMPTION_BASIS,
                "human_approved_by": ASSUMPTION_APPROVER,
                "approval_date": ASSUMPTION_DATE,
            }
        )
    return rows


def build_valid_alternative_rows(approved: list[dict[str, str]]) -> list[dict[str, str]]:
    requirement_map = _requirements_by_id()
    rows = []
    for requirement_id in sorted({row["requirement_id"] for row in approved}):
        requirement = requirement_map[requirement_id]
        rows.append(
            {
                "implementation_id": f"{requirement_id}_A01",
                "requirement_id": requirement_id,
                "variant_type": "valid_alternative",
                "base_implementation_id": "REFERENCE",
                "realization_kind": "proposal_only",
                "rationale": f"Assumed compliant alternative for {requirement_id} within current single-service architecture.",
                "review_status": "ASSUMED_APPROVED_COMPLIANT",
                "human_approved_by": ASSUMPTION_APPROVER,
                "approval_date": ASSUMPTION_DATE,
                "category": requirement["category"],
            }
        )
    return rows


def build_boundary_rows() -> list[dict[str, str]]:
    requirement_map = _requirements_by_id()
    rows = []
    for requirement_id, implementation_id, boundary_kind, rationale in BOUNDARY_CASES:
        rows.append(
            {
                "implementation_id": implementation_id,
                "requirement_id": requirement_id,
                "variant_type": "boundary",
                "base_implementation_id": "REFERENCE",
                "boundary_kind": boundary_kind,
                "rationale": rationale,
                "review_status": "ASSUMED_APPROVED_VALID_BOUNDARY",
                "human_approved_by": ASSUMPTION_APPROVER,
                "approval_date": ASSUMPTION_DATE,
                "category": requirement_map[requirement_id]["category"],
            }
        )
    return rows


def build_expected_verdict_rows(
    approved: list[dict[str, str]],
    valid_alternative_rows: list[dict[str, str]],
    boundary_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    requirement_map = _requirements_by_id()
    obligation_map = _obligations_by_requirement()
    rows: list[dict[str, str]] = []

    for requirement_id in sorted(requirement_map):
        rows.append(
            {
                "implementation_id": f"{requirement_id}_REFERENCE",
                "requirement_id": requirement_id,
                "variant_type": "compliant",
                "expected_guardrail_verdict": "non_violating",
                "target_obligation_ids": ";".join(_eligible_obligation_ids(obligation_map[requirement_id])),
                "rationale": f"Reference implementation row for {requirement_id} under assumption-mode package.",
                "human_approved_by": ASSUMPTION_APPROVER,
                "approval_date": ASSUMPTION_DATE,
            }
        )

    for row in approved:
        rows.append(
            {
                "implementation_id": row["mutation_id"],
                "requirement_id": row["requirement_id"],
                "variant_type": "violating",
                "expected_guardrail_verdict": "violating",
                "target_obligation_ids": row["target_obligation_id"],
                "rationale": row["expected_behavioral_difference"],
                "human_approved_by": ASSUMPTION_APPROVER,
                "approval_date": ASSUMPTION_DATE,
            }
        )

    for row in valid_alternative_rows:
        rows.append(
            {
                "implementation_id": row["implementation_id"],
                "requirement_id": row["requirement_id"],
                "variant_type": row["variant_type"],
                "expected_guardrail_verdict": "non_violating",
                "target_obligation_ids": ";".join(_eligible_obligation_ids(obligation_map[row["requirement_id"]])),
                "rationale": row["rationale"],
                "human_approved_by": ASSUMPTION_APPROVER,
                "approval_date": ASSUMPTION_DATE,
            }
        )

    for row in boundary_rows:
        rows.append(
            {
                "implementation_id": row["implementation_id"],
                "requirement_id": row["requirement_id"],
                "variant_type": row["variant_type"],
                "expected_guardrail_verdict": "non_violating",
                "target_obligation_ids": ";".join(_eligible_obligation_ids(obligation_map[row["requirement_id"]])),
                "rationale": row["rationale"],
                "human_approved_by": ASSUMPTION_APPROVER,
                "approval_date": ASSUMPTION_DATE,
            }
        )

    return rows


def write_assumption_artifacts(repo_root: str | Path | None = None) -> dict[str, int]:
    repo_root = Path(repo_root) if repo_root else _repo_root()
    approved = load_approved_mutations(repo_root / "MUTATION_PLAN.csv")
    mutation_validation_rows = build_mutation_validation_rows(approved)
    valid_alternative_rows = build_valid_alternative_rows(approved)
    boundary_rows = build_boundary_rows()
    expected_verdict_rows = build_expected_verdict_rows(approved, valid_alternative_rows, boundary_rows)
    requirements = _load_requirements(repo_root)
    obligations = _obligations_by_requirement(repo_root)

    _write_csv(
        repo_root / "MUTATION_VALIDATION.csv",
        [
            "mutation_id",
            "requirement_id",
            "target_obligation_id",
            "validation_status",
            "rationale",
            "validation_basis",
            "human_approved_by",
            "approval_date",
        ],
        mutation_validation_rows,
    )
    _write_csv(
        repo_root / "variants" / "valid_alternatives" / "VALID_ALTERNATIVE_CORPUS.csv",
        [
            "implementation_id",
            "requirement_id",
            "variant_type",
            "base_implementation_id",
            "realization_kind",
            "rationale",
            "review_status",
            "human_approved_by",
            "approval_date",
        ],
        valid_alternative_rows,
    )
    _write_csv(
        repo_root / "variants" / "boundary" / "BOUNDARY_CORPUS.csv",
        [
            "implementation_id",
            "requirement_id",
            "variant_type",
            "base_implementation_id",
            "boundary_kind",
            "rationale",
            "review_status",
            "human_approved_by",
            "approval_date",
        ],
        boundary_rows,
    )
    _write_csv(
        repo_root / "variants" / "EXPECTED_VERDICTS.csv",
        [
            "implementation_id",
            "requirement_id",
            "variant_type",
            "expected_guardrail_verdict",
            "target_obligation_ids",
            "rationale",
            "human_approved_by",
            "approval_date",
        ],
        expected_verdict_rows,
    )

    _write_variant_manifests(repo_root, valid_alternative_rows, "valid_alternatives", "realization_kind")
    _write_variant_manifests(repo_root, boundary_rows, "boundary", "boundary_kind")
    _write_experiment_contracts(repo_root)
    _write_experiment_stubs(repo_root)
    _write_human_guardrail_artifacts(repo_root, requirements, obligations)
    _write_prompt_artifacts(repo_root)
    _write_pilot_artifacts(repo_root, requirements)
    _write_raw_processed_artifacts(repo_root, requirements, mutation_validation_rows, valid_alternative_rows, boundary_rows, expected_verdict_rows)
    _write_final_results(repo_root, requirements, mutation_validation_rows, valid_alternative_rows, boundary_rows, expected_verdict_rows)
    _write_step_reports(repo_root, mutation_validation_rows, valid_alternative_rows, boundary_rows, expected_verdict_rows)
    _write_hashes(repo_root)

    return {
        "approved_mutations": len(approved),
        "mutation_validation_rows": len(mutation_validation_rows),
        "valid_alternatives": len(valid_alternative_rows),
        "boundary_cases": len(boundary_rows),
        "expected_verdict_rows": len(expected_verdict_rows),
        "requirements": len(requirements),
    }


def _load_requirements(repo_root: Path | None = None) -> list[dict[str, str]]:
    repo_root = repo_root or _repo_root()
    data = yaml.safe_load((repo_root / "requirements" / "requirements_v1.yaml").read_text())
    return data["requirements"]


def _requirements_by_id(repo_root: Path | None = None) -> dict[str, dict[str, str]]:
    return {row["requirement_id"]: row for row in _load_requirements(repo_root)}


def _obligations_by_requirement(repo_root: Path | None = None) -> dict[str, list[dict[str, str]]]:
    repo_root = repo_root or _repo_root()
    result: dict[str, list[dict[str, str]]] = {}
    for path in sorted((repo_root / "requirements" / "obligation_checklists" / "FINAL").glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        for checklist in data["checklists"]:
            result[checklist["requirement_id"]] = checklist["obligations"]
    return result


def _eligible_obligation_ids(obligations: list[dict[str, str]]) -> list[str]:
    eligible = []
    for obligation in obligations:
        if _is_ambiguous_obligation(obligation):
            continue
        eligible.append(obligation["obligation_id"])
    return eligible


def _is_ambiguous_obligation(obligation: dict[str, str]) -> bool:
    return any(isinstance(value, str) and "AMBIGUOUS" in value for value in obligation.values())


def _write_variant_manifests(repo_root: Path, rows: list[dict[str, str]], variant_dir: str, mode_key: str) -> None:
    root = repo_root / "variants" / variant_dir
    for row in rows:
        path = root / row["requirement_id"] / row["implementation_id"]
        manifest = {
            "implementation_id": row["implementation_id"],
            "requirement_id": row["requirement_id"],
            "variant_type": row["variant_type"],
            "base_implementation_id": row["base_implementation_id"],
            mode_key: row[mode_key],
            "rationale": row["rationale"],
            "status": ASSUMPTION_STATUS,
        }
        _write_json(path / "manifest.json", manifest)


def _write_experiment_contracts(repo_root: Path) -> None:
    _write_text(
        repo_root / "experiment" / "GUARDRAIL_INTERFACE.md",
        dedent(
            f"""\
            # GUARDRAIL_INTERFACE

            {assumption_banner()}

            ## Contract

            - Study-level entrypoint: `evaluate(case: dict) -> dict`
            - Supported generator conditions: `H`, `L0`, `L1`, `L2`
            - Output contract must follow `experiment/schema/guardrail_result.schema.json`
            - Guardrails must not read hidden expected verdicts during execution.
            - App-local hook adaptation may map `FAIL` verdicts into request-block records, but study interface remains generator-agnostic.
            """
        ),
    )
    schemas = {
        "guardrail_context.schema.json": {
            "type": "object",
            "required": ["run_id", "requirement_id", "formulation_id", "generator_condition", "implementation_id", "variant_type"],
            "properties": {
                "run_id": {"type": "string"},
                "requirement_id": {"type": "string"},
                "formulation_id": {"type": "string"},
                "generator_condition": {"type": "string", "enum": ["H", "L0", "L1", "L2"]},
                "implementation_id": {"type": "string"},
                "variant_type": {"type": "string"},
                "fixture_inputs": {"type": "object"},
                "evidence_collectors": {"type": "array", "items": {"type": "string"}},
            },
        },
        "guardrail_result.schema.json": {
            "type": "object",
            "required": ["guardrail_id", "requirement_id", "execution_status", "verdict", "runtime_ms"],
            "properties": {
                "guardrail_id": {"type": "string"},
                "requirement_id": {"type": "string"},
                "generator_condition": {"type": "string"},
                "execution_status": {"type": "string", "enum": ["ok", "compile_error", "runtime_error", "timeout", "unsupported"]},
                "verdict": {"type": "string", "enum": ["PASS", "FAIL", "ERROR"]},
                "failed_obligation_ids": {"type": "array", "items": {"type": "string"}},
                "observed_evidence": {"type": "array", "items": {"type": "object"}},
                "runtime_ms": {"type": "integer"},
            },
        },
        "guardrail_artifact_manifest.schema.json": {
            "type": "object",
            "required": ["guardrail_id", "requirement_id", "generator_condition", "artifact_path", "status"],
            "properties": {
                "guardrail_id": {"type": "string"},
                "requirement_id": {"type": "string"},
                "generator_condition": {"type": "string"},
                "artifact_path": {"type": "string"},
                "prompt_version": {"type": "string"},
                "model_config_id": {"type": "string"},
                "status": {"type": "string"},
            },
        },
        "structured_extraction.schema.json": {
            "type": "object",
            "required": ["requirement_id", "formulation_id", "obligations"],
            "properties": {
                "requirement_id": {"type": "string"},
                "formulation_id": {"type": "string"},
                "actor": {"type": "string"},
                "preconditions": {"type": "array", "items": {"type": "string"}},
                "obligations": {"type": "array", "items": {"type": "object"}},
            },
        },
        "l2_validation_record.schema.json": {
            "type": "object",
            "required": ["validation_id", "source_guardrail_id", "decision", "validated_at"],
            "properties": {
                "validation_id": {"type": "string"},
                "source_guardrail_id": {"type": "string"},
                "decision": {"type": "string", "enum": ["accepted", "rejected", "escalated"]},
                "reason_codes": {"type": "array", "items": {"type": "string"}},
                "validated_at": {"type": "string"},
            },
        },
        "raw_generation_record.schema.json": {
            "type": "object",
            "required": ["generation_id", "generator_condition", "requirement_id", "formulation_id", "status"],
            "properties": {
                "generation_id": {"type": "string"},
                "generator_condition": {"type": "string"},
                "requirement_id": {"type": "string"},
                "formulation_id": {"type": "string"},
                "artifact_path": {"type": "string"},
                "status": {"type": "string"},
                "error_type": {"type": ["string", "null"]},
            },
        },
    }
    for name, payload in schemas.items():
        _write_json(repo_root / "experiment" / "schema" / name, payload)


def _write_experiment_stubs(repo_root: Path) -> None:
    files = {
        "runner.py": """from experiment.assumption_package import assumption_banner\n\n\ndef main() -> None:\n    print(assumption_banner())\n    print(\"Runner scaffold only. No empirical generation or execution implemented in assumption package.\")\n\n\nif __name__ == \"__main__\":\n    main()\n""",
        "evaluator.py": """from experiment.assumption_package import assumption_banner\n\n\ndef main() -> None:\n    print(assumption_banner())\n    print(\"Evaluator scaffold only. Processed and final empirical metrics remain uncomputed.\")\n\n\nif __name__ == \"__main__\":\n    main()\n""",
        "validators.py": """from experiment.assumption_package import assumption_banner\n\n\ndef main() -> None:\n    print(assumption_banner())\n    print(\"Validator scaffold only. L2 validation decisions are not populated in assumption package.\")\n\n\nif __name__ == \"__main__\":\n    main()\n""",
        "freeze.py": """from experiment.assumption_package import assumption_banner\n\n\ndef main() -> None:\n    print(assumption_banner())\n    print(\"Freeze scaffold only. Use freeze/hashes.sha256 and freeze/EXPERIMENT_FREEZE.md for draft packaging.\")\n\n\nif __name__ == \"__main__\":\n    main()\n""",
    }
    for name, content in files.items():
        _write_text(repo_root / "experiment" / name, content)


def _write_human_guardrail_artifacts(repo_root: Path, requirements: list[dict[str, str]], obligations: dict[str, list[dict[str, str]]]) -> None:
    template = {
        "status": ASSUMPTION_STATUS,
        "notes": NOT_PROTOCOL_VALID,
        "worksheet_fields": [
            "worksheet_id",
            "requirement_id",
            "requirement_text",
            "category",
            "source_checklist_path",
            "obligations",
            "required_evidence",
            "valid_alternative_ids",
            "boundary_case_ids",
            "known_ambiguities",
        ],
    }
    _write_yaml(repo_root / "guardrails" / "human" / "WORKSHEET_TEMPLATE.yaml", template)

    worksheet_index_rows = []
    for requirement in requirements:
        requirement_id = requirement["requirement_id"]
        worksheet = {
            "worksheet_id": f"H_{requirement_id}",
            "requirement_id": requirement_id,
            "requirement_text": requirement["text"],
            "category": requirement["category"],
            "source_checklist_path": _checklist_path_for_requirement(requirement_id),
            "formulation_ids_for_reference": [f"{requirement_id}_F0", f"{requirement_id}_F1", f"{requirement_id}_F2"],
            "obligations": obligations[requirement_id],
            "required_evidence": requirement.get("candidate_evidence", []),
            "valid_alternative_ids": [f"{requirement_id}_A01"],
            "boundary_case_ids": [case_id for req_id, case_id, _, _ in BOUNDARY_CASES if req_id == requirement_id],
            "minimal_verdict_logic": "Block violating implementations; allow compliant, valid-alternative, and approved boundary implementations.",
            "known_ambiguities": [value for obligation in obligations[requirement_id] for value in obligation.values() if isinstance(value, str) and "AMBIGUOUS" in value],
            "human_author_notes": [assumption_banner()],
            "status": ASSUMPTION_STATUS,
        }
        _write_yaml(repo_root / "guardrails" / "human" / "worksheets" / f"{requirement_id}.yaml", worksheet)
        worksheet_index_rows.append(
            {
                "requirement_id": requirement_id,
                "worksheet_path": f"guardrails/human/worksheets/{requirement_id}.yaml",
                "category": requirement["category"],
                "review_status": ASSUMPTION_STATUS,
                "has_valid_alternative_refs": "yes",
                "has_boundary_refs": "yes" if worksheet["boundary_case_ids"] else "no",
                "has_expected_verdict_refs": "yes",
                "notes": ASSUMPTION_BASIS,
            }
        )
    _write_csv(
        repo_root / "guardrails" / "human" / "worksheet_index.csv",
        [
            "requirement_id",
            "worksheet_path",
            "category",
            "review_status",
            "has_valid_alternative_refs",
            "has_boundary_refs",
            "has_expected_verdict_refs",
            "notes",
        ],
        worksheet_index_rows,
    )
    _write_csv(
        repo_root / "guardrails" / "human" / "H_GUARDRAIL_FREEZE.csv",
        [
            "requirement_id",
            "guardrail_id",
            "artifact_path",
            "worksheet_path",
            "positive_control_status",
            "negative_control_status",
            "valid_alternative_status",
            "approval_status",
            "approved_by",
            "approval_date",
        ],
        [
            {
                "requirement_id": requirement["requirement_id"],
                "guardrail_id": f"H_{requirement['requirement_id']}",
                "artifact_path": "HUMAN_REQUIRED",
                "worksheet_path": f"guardrails/human/worksheets/{requirement['requirement_id']}.yaml",
                "positive_control_status": "ASSUMED_PENDING_UPSTREAM",
                "negative_control_status": "ASSUMED_PENDING_UPSTREAM",
                "valid_alternative_status": "ASSUMED_PENDING_UPSTREAM",
                "approval_status": ASSUMPTION_STATUS,
                "approved_by": ASSUMPTION_APPROVER,
                "approval_date": ASSUMPTION_DATE,
            }
            for requirement in requirements
        ],
    )


def _write_prompt_artifacts(repo_root: Path) -> None:
    l0_path = repo_root / "prompts" / "guardrail_generation" / "L0_PROMPT_v1.md"
    l1_path = repo_root / "prompts" / "structured_extraction" / "L1_PROMPT_v1.md"
    l2_path = repo_root / "prompts" / "L2_VALIDATION_SPEC.md"
    _write_text(
        l0_path,
        dedent(
            f"""\
            # L0_PROMPT_v1

            {assumption_banner()}

            Generate one executable guardrail for one requirement formulation.
            Use only provided requirement text, formulation text, and public reference surfaces.
            Do not read hidden expected verdicts.
            Output one guardrail artifact plus machine-readable manifest.
            If requirement is unsupported, say so explicitly instead of hallucinating logic.
            """
        ),
    )
    _write_text(
        l1_path,
        dedent(
            f"""\
            # L1_PROMPT_v1

            {assumption_banner()}

            Stage A: extract structured obligations from one frozen requirement formulation.
            Stage B: generate one executable guardrail using only extracted obligations and provided evidence surfaces.
            Preserve obligation-level traceability and report unsupported semantics explicitly.
            """
        ),
    )
    _write_text(
        l2_path,
        dedent(
            f"""\
            # L2_VALIDATION_SPEC

            {assumption_banner()}

            Validation checks:
            1. schema validity
            2. compile success
            3. positive control behavior
            4. declared negative control behavior
            5. paraphrase differential check
            6. static obligation coverage check

            Decisions: `accepted`, `rejected`, `escalated`.
            Reason codes: `SCHEMA_INVALID`, `COMPILE_FAILURE`, `POSITIVE_CONTROL_FAIL`, `NEGATIVE_CONTROL_FAIL`, `PARAPHRASE_DIVERGENCE`, `STATIC_COVERAGE_GAP`, `AMBIGUOUS_RESULT`, `RUNTIME_ERROR`.
            """
        ),
    )
    prompt_versions = {
        "status": ASSUMPTION_STATUS,
        "L0": {"version": "v1", "path": "prompts/guardrail_generation/L0_PROMPT_v1.md", "status": ASSUMPTION_STATUS},
        "L1": {"version": "v1", "path": "prompts/structured_extraction/L1_PROMPT_v1.md", "status": ASSUMPTION_STATUS},
        "L2": {"version": "v1", "path": "prompts/L2_VALIDATION_SPEC.md", "status": ASSUMPTION_STATUS},
    }
    _write_json(repo_root / "prompts" / "prompt_versions.json", prompt_versions)
    _write_yaml(
        repo_root / "freeze" / "MODEL_CONFIG_FREEZE.yaml",
        {
            "status": ASSUMPTION_STATUS,
            "approved_by": ASSUMPTION_APPROVER,
            "frozen_at": ASSUMPTION_DATE,
            "provider": "ASSUMED_PENDING_SELECTION",
            "model_id": "ASSUMED_PENDING_SELECTION",
            "temperature": 0,
            "replicates": 1,
            "notes": [NOT_PROTOCOL_VALID],
        },
    )


def _write_pilot_artifacts(repo_root: Path, requirements: list[dict[str, str]]) -> None:
    selected = [row["requirement_id"] for row in requirements[:6]]
    _write_text(
        repo_root / "pilot" / "README.md",
        dedent(
            f"""\
            # Pilot

            {assumption_banner()}

            Pilot scaffolding only. No empirical pilot generations or executions recorded in this package.
            """
        ),
    )
    _write_yaml(
        repo_root / "pilot" / "PILOT_SCOPE.yaml",
        {
            "status": ASSUMPTION_STATUS,
            "not_for_final_results": True,
            "requirement_count": len(selected),
            "selected_requirements": selected,
            "generator_conditions": ["H", "L0", "L1", "L2"],
            "approval_needed": False,
        },
    )
    _write_csv(
        repo_root / "pilot" / "PILOT_REQUIREMENTS.csv",
        ["requirement_id", "category", "formulation_ids", "selection_basis", "approval_status"],
        [
            {
                "requirement_id": requirement_id,
                "category": _requirements_by_id()[requirement_id]["category"],
                "formulation_ids": ";".join([f"{requirement_id}_F0", f"{requirement_id}_F1", f"{requirement_id}_F2"]),
                "selection_basis": "first_six_frozen_requirements_for_scaffold_only",
                "approval_status": ASSUMPTION_STATUS,
            }
            for requirement_id in selected
        ],
    )
    _write_text(
        repo_root / "pilot" / "PILOT_REPORT.md",
        dedent(
            f"""\
            # PILOT_REPORT

            - status: NOT_RUN
            - mode: {ASSUMPTION_STATUS}

            No empirical pilot run was executed. This artifact reserves pilot package structure only.
            """
        ),
    )
    for relative in [
        "pilot/raw/generations/L0/index.csv",
        "pilot/raw/generations/L1/index.csv",
        "pilot/raw/execution/index.csv",
        "pilot/raw/logs/index.csv",
        "pilot/raw/failures/index.csv",
    ]:
        _write_csv(repo_root / relative, ["status", "notes"], [])


def _write_raw_processed_artifacts(
    repo_root: Path,
    requirements: list[dict[str, str]],
    mutation_validation_rows: list[dict[str, str]],
    valid_alternative_rows: list[dict[str, str]],
    boundary_rows: list[dict[str, str]],
    expected_verdict_rows: list[dict[str, str]],
) -> None:
    _write_csv(
        repo_root / "raw" / "generations" / "L0" / "index.csv",
        ["generation_id", "generator_condition", "requirement_id", "formulation_id", "status", "notes"],
        [],
    )
    _write_csv(
        repo_root / "raw" / "generations" / "L1" / "index.csv",
        ["generation_id", "generator_condition", "requirement_id", "formulation_id", "status", "notes"],
        [],
    )
    _write_csv(
        repo_root / "guardrails" / "llm_validated" / "index.csv",
        ["validation_id", "requirement_id", "formulation_id", "source_guardrail_id", "decision", "notes"],
        [],
    )
    _write_text(
        repo_root / "raw" / "execution" / "README.md",
        dedent(
            f"""\
            # Raw Execution

            {assumption_banner()}

            No Step 40 execution campaign was run in this package. Keep this directory append-only when real executions occur.
            """
        ),
    )
    _write_csv(
        repo_root / "processed" / "guardrail_level_results.csv",
        [
            "guardrail_row_id",
            "requirement_id",
            "requirement_category",
            "formulation_id",
            "generator_condition",
            "guardrail_valid_flag",
            "invalid_reason",
            "raw_generation_ref",
        ],
        [],
    )
    _write_csv(
        repo_root / "processed" / "implementation_level_results.csv",
        [
            "implementation_eval_row_id",
            "requirement_id",
            "implementation_id",
            "variant_type",
            "expected_guardrail_verdict",
            "observed_guardrail_verdict",
            "execution_status",
            "correctness_classification",
            "raw_execution_ref",
        ],
        [],
    )
    _write_csv(
        repo_root / "processed" / "obligation_level_results.csv",
        [
            "obligation_eval_row_id",
            "requirement_id",
            "obligation_id",
            "obligation_result",
            "omission_flag",
            "mapping_basis",
            "raw_execution_refs",
        ],
        [],
    )
    _write_csv(
        repo_root / "processed" / "paraphrase_consistency.csv",
        [
            "paraphrase_row_id",
            "requirement_id",
            "generator_condition",
            "left_formulation_id",
            "right_formulation_id",
            "agreement_flag",
            "raw_left_execution_ref",
            "raw_right_execution_ref",
        ],
        [],
    )
    _write_csv(
        repo_root / "processed" / "failure_labels.csv",
        [
            "failure_label_row_id",
            "requirement_id",
            "formulation_id",
            "generator_condition",
            "failure_label",
            "label_status",
            "evidence_refs",
        ],
        [],
    )
    _write_json(
        repo_root / "processed" / "metrics.json",
        {
            "status": ASSUMPTION_STATUS,
            "notes": [NOT_PROTOCOL_VALID, "No raw generation or execution rows available for metric computation."],
            "artifact_counts": {
                "requirements": len(requirements),
                "approved_mutations": len(mutation_validation_rows),
                "valid_alternatives": len(valid_alternative_rows),
                "boundary_cases": len(boundary_rows),
                "expected_verdict_rows": len(expected_verdict_rows),
            },
            "metrics": [],
        },
    )


def _write_final_results(
    repo_root: Path,
    requirements: list[dict[str, str]],
    mutation_validation_rows: list[dict[str, str]],
    valid_alternative_rows: list[dict[str, str]],
    boundary_rows: list[dict[str, str]],
    expected_verdict_rows: list[dict[str, str]],
) -> None:
    verified_rows = [
        {
            "metric_name": "frozen_requirement_count",
            "slice_name": "overall",
            "slice_value": "overall",
            "numerator": str(len(requirements)),
            "denominator": str(len(requirements)),
            "formula": "count(frozen selected requirements)",
            "value": str(len(requirements)),
            "ci_95_low": "",
            "ci_95_high": "",
            "raw_row_ids": ";".join(row["requirement_id"] for row in requirements),
            "raw_files": "requirements/requirements_v1.yaml",
            "processed_source_files": "requirements/requirements_v1.yaml",
            "script_commit": "UNCOMMITTED_WORKTREE",
            "recompute_match_status": "match",
        },
        {
            "metric_name": "approved_mutation_count",
            "slice_name": "overall",
            "slice_value": "overall",
            "numerator": str(len(mutation_validation_rows)),
            "denominator": str(len(mutation_validation_rows)),
            "formula": "count(ASSUMED_VALID_MUTATION rows)",
            "value": str(len(mutation_validation_rows)),
            "ci_95_low": "",
            "ci_95_high": "",
            "raw_row_ids": ";".join(row["mutation_id"] for row in mutation_validation_rows),
            "raw_files": "MUTATION_PLAN.csv;MUTATION_VALIDATION.csv",
            "processed_source_files": "MUTATION_VALIDATION.csv",
            "script_commit": "UNCOMMITTED_WORKTREE",
            "recompute_match_status": "match",
        },
        {
            "metric_name": "assumed_valid_alternative_count",
            "slice_name": "overall",
            "slice_value": "overall",
            "numerator": str(len(valid_alternative_rows)),
            "denominator": str(len(valid_alternative_rows)),
            "formula": "count(ASSUMED_APPROVED_COMPLIANT rows)",
            "value": str(len(valid_alternative_rows)),
            "ci_95_low": "",
            "ci_95_high": "",
            "raw_row_ids": ";".join(row["implementation_id"] for row in valid_alternative_rows),
            "raw_files": "variants/valid_alternatives/VALID_ALTERNATIVE_CORPUS.csv",
            "processed_source_files": "variants/valid_alternatives/VALID_ALTERNATIVE_CORPUS.csv",
            "script_commit": "UNCOMMITTED_WORKTREE",
            "recompute_match_status": "match",
        },
        {
            "metric_name": "assumed_boundary_case_count",
            "slice_name": "overall",
            "slice_value": "overall",
            "numerator": str(len(boundary_rows)),
            "denominator": str(len(boundary_rows)),
            "formula": "count(ASSUMED_APPROVED_VALID_BOUNDARY rows)",
            "value": str(len(boundary_rows)),
            "ci_95_low": "",
            "ci_95_high": "",
            "raw_row_ids": ";".join(row["implementation_id"] for row in boundary_rows),
            "raw_files": "variants/boundary/BOUNDARY_CORPUS.csv",
            "processed_source_files": "variants/boundary/BOUNDARY_CORPUS.csv",
            "script_commit": "UNCOMMITTED_WORKTREE",
            "recompute_match_status": "match",
        },
        {
            "metric_name": "expected_verdict_row_count",
            "slice_name": "overall",
            "slice_value": "overall",
            "numerator": str(len(expected_verdict_rows)),
            "denominator": str(len(expected_verdict_rows)),
            "formula": "count(all rows in variants/EXPECTED_VERDICTS.csv)",
            "value": str(len(expected_verdict_rows)),
            "ci_95_low": "",
            "ci_95_high": "",
            "raw_row_ids": ";".join(row["implementation_id"] for row in expected_verdict_rows),
            "raw_files": "variants/EXPECTED_VERDICTS.csv",
            "processed_source_files": "variants/EXPECTED_VERDICTS.csv",
            "script_commit": "UNCOMMITTED_WORKTREE",
            "recompute_match_status": "match",
        },
        {
            "metric_name": "protocol_validity_flag",
            "slice_name": "overall",
            "slice_value": "overall",
            "numerator": "0",
            "denominator": "1",
            "formula": "1 only if all human gates and empirical stages are genuinely completed under frozen protocol",
            "value": "0",
            "ci_95_low": "",
            "ci_95_high": "",
            "raw_row_ids": "assumption_mode",
            "raw_files": "reports/;freeze/;final_results/",
            "processed_source_files": "processed/metrics.json",
            "script_commit": "UNCOMMITTED_WORKTREE",
            "recompute_match_status": "match",
        },
    ]
    _write_csv(
        repo_root / "final_results" / "VERIFIED_RESULTS.csv",
        [
            "metric_name",
            "slice_name",
            "slice_value",
            "numerator",
            "denominator",
            "formula",
            "value",
            "ci_95_low",
            "ci_95_high",
            "raw_row_ids",
            "raw_files",
            "processed_source_files",
            "script_commit",
            "recompute_match_status",
        ],
        verified_rows,
    )
    _write_csv(
        repo_root / "final_results" / "NUMBER_PROVENANCE.csv",
        [
            "number_id",
            "output_document",
            "output_section",
            "metric_name",
            "slice_name",
            "slice_value",
            "displayed_value",
            "numerator",
            "denominator",
            "formula",
            "raw_row_ids",
            "raw_files",
            "recompute_script",
            "script_commit",
            "verified_by",
            "verification_status",
        ],
        [
            {
                "number_id": f"N{index + 1:03d}",
                "output_document": "final_results/VERIFIED_RESULTS.md",
                "output_section": "Artifact Counts",
                "metric_name": row["metric_name"],
                "slice_name": row["slice_name"],
                "slice_value": row["slice_value"],
                "displayed_value": row["value"],
                "numerator": row["numerator"],
                "denominator": row["denominator"],
                "formula": row["formula"],
                "raw_row_ids": row["raw_row_ids"],
                "raw_files": row["raw_files"],
                "recompute_script": "experiment/assumption_package.py::write_assumption_artifacts",
                "script_commit": row["script_commit"],
                "verified_by": ASSUMPTION_APPROVER,
                "verification_status": "match",
            }
            for index, row in enumerate(verified_rows)
        ],
    )
    shared_note = (
        f"{assumption_banner()}\n\n"
        "This package assembles deterministic artifact counts and scaffold documentation only."
        " It does not claim empirical guardrail-generation or execution results."
    )
    docs = {
        "VERIFIED_RESULTS.md": f"# VERIFIED_RESULTS\n\n{shared_note}\n\n## Artifact Counts\n\n- Frozen requirements: {len(requirements)}\n- Approved violating mutations: {len(mutation_validation_rows)}\n- Assumed valid alternatives: {len(valid_alternative_rows)}\n- Assumed boundary cases: {len(boundary_rows)}\n- Expected verdict rows: {len(expected_verdict_rows)}\n- Protocol-valid final-results flag: 0\n",
        "RQ1_RESULTS.md": f"# RQ1_RESULTS\n\n{shared_note}\n\nRQ1 remains unanswerable without real generated guardrails, execution traces, and obligation-level evidence rows. This draft records only preparation status.\n",
        "RQ2_RESULTS.md": f"# RQ2_RESULTS\n\n{shared_note}\n\nRQ2 remains unanswerable without shared empirical verdict rows across frozen equivalent formulations.\n",
        "RQ3_RESULTS.md": f"# RQ3_RESULTS\n\n{shared_note}\n\nRQ3 remains unanswerable without empirical H/L0/L1/L2 guardrail outputs and execution rows on the frozen implementation corpus.\n",
        "RQ4_RESULTS.md": f"# RQ4_RESULTS\n\n{shared_note}\n\nRQ4 remains unanswerable without generated guardrail failure labels and L2 validation decisions.\n",
        "FAILURE_ANALYSIS.md": f"# FAILURE_ANALYSIS\n\n{shared_note}\n\nNo empirical failure-label rows exist in `processed/failure_labels.csv`. File intentionally left schema-only.\n",
        "PARAPHRASE_ANALYSIS.md": f"# PARAPHRASE_ANALYSIS\n\n{shared_note}\n\nNo paraphrase execution comparisons exist yet. `processed/paraphrase_consistency.csv` contains headers only.\n",
        "VALIDATION_YIELD.md": f"# VALIDATION_YIELD\n\n{shared_note}\n\nNo L2 validation rows exist yet. `guardrails/llm_validated/index.csv` remains unpopulated.\n",
        "LIMITATIONS_FACTS.md": f"# LIMITATIONS_FACTS\n\n{shared_note}\n\n- Human gates after Step 22 were assumed from user instruction rather than protocol execution.\n- No empirical guardrail generation, validation, or execution rows were preserved.\n- Result documents are package scaffolds, not final scientific claims.\n- Six approved mutation rows may still require obligation-ID reconciliation against frozen checklists.\n",
        "REPRODUCIBILITY.md": f"# REPRODUCIBILITY\n\n{shared_note}\n\n## Deterministic package regeneration\n\nRun from repo root:\n\n```bash\npython3 -c \"from experiment.assumption_package import write_assumption_artifacts; write_assumption_artifacts()\"\n```\n\nThen verify tests and artifact counts with the commands used in this session.\n",
        "FINAL_EXPERIMENT_REPORT.md": f"# FINAL_EXPERIMENT_REPORT\n\n{shared_note}\n\nThis repository now contains a complete assumption-mode artifact package through the final document set. It is suitable for review, further implementation, or protocol completion, but not for protocol-valid empirical claims.\n",
    }
    for name, content in docs.items():
        _write_text(repo_root / "final_results" / name, content)


def _write_step_reports(
    repo_root: Path,
    mutation_validation_rows: list[dict[str, str]],
    valid_alternative_rows: list[dict[str, str]],
    boundary_rows: list[dict[str, str]],
    expected_verdict_rows: list[dict[str, str]],
) -> None:
    summaries = {
        23: f"Prefilled `MUTATION_VALIDATION.csv` with {len(mutation_validation_rows)} assumed-valid approved mutations.",
        24: f"Created valid-alternative corpus with {len(valid_alternative_rows)} assumption-mode rows.",
        25: f"Created boundary corpus with {len(boundary_rows)} assumption-mode scenario rows.",
        26: f"Created `variants/EXPECTED_VERDICTS.csv` with {len(expected_verdict_rows)} rows under assumption mode.",
        27: "Created study-level guardrail interface and machine-readable schemas.",
        28: "Generated human worksheet template, worksheet index, and one worksheet per frozen requirement.",
        29: "Generated human guardrail freeze scaffold only; no empirical H guardrail artifacts were written.",
        30: "Wrote assumption-mode L0 prompt draft and prompt version manifest.",
        31: "Wrote assumption-mode L1 prompt draft and prompt version manifest entry.",
        32: "Wrote assumption-mode L2 validation spec draft.",
        33: "Wrote model/config freeze template under assumption mode.",
        34: "Created pilot package scaffolding and empty pilot raw indexes.",
        35: "Recorded pilot report as not run.",
        36: "Created experiment freeze draft and hash manifest under assumption mode.",
        37: "Created L0 raw generation index scaffold only.",
        38: "Created L1 raw generation index scaffold only.",
        39: "Created L2 validation index scaffold only.",
        40: "Reserved raw execution directory and README; no campaign rows recorded.",
        41: "Created guardrail-level processed CSV schema only.",
        42: "Created obligation-level processed CSV schema only.",
        43: "Created implementation-level processed CSV schema only.",
        44: "Created paraphrase-consistency processed CSV schema only.",
        45: "Created failure-label processed CSV schema only.",
        46: "Created metrics JSON carrying artifact counts and explicit not-computed state.",
        47: "Created verified-results and number-provenance outputs for deterministic artifact counts only.",
        48: "Created full final-results document set with explicit assumption-mode and non-protocol-valid disclaimers.",
    }
    for step in range(23, 49):
        created_files = STEP_REPORTS[step]
        status = ASSUMPTION_STATUS
        created_block = "\n".join(f"- `{path}`" for path in created_files)
        report = (
            f"# STEP_{step:02d}_REPORT\n\n"
            f"- status: {status}\n\n"
            "## Files created\n\n"
            f"{created_block}\n\n"
            "## Summary\n\n"
            f"- {summaries[step]}\n"
            f"- {NOT_PROTOCOL_VALID}.\n"
            "- Human-owned protocol steps were treated as assumed complete only because user explicitly instructed assumption mode.\n"
        )
        _write_text(repo_root / "reports" / f"STEP_{step:02d}_REPORT.md", report)


def _write_hashes(repo_root: Path) -> None:
    experiment_freeze = dedent(
        f"""\
        # EXPERIMENT_FREEZE

        {assumption_banner()}

        - frozen_at: {ASSUMPTION_DATE}
        - approved_by: {ASSUMPTION_APPROVER}
        - reference_application: `application/reference/service.py`
        - mutation_plan: `MUTATION_PLAN.csv`
        - expected_verdicts: `variants/EXPECTED_VERDICTS.csv`
        - prompts_manifest: `prompts/prompt_versions.json`
        - model_config_freeze: `freeze/MODEL_CONFIG_FREEZE.yaml`
        - notes: all downstream empirical steps remain unexecuted in this package.
        """
    )
    _write_text(repo_root / "freeze" / "EXPERIMENT_FREEZE.md", experiment_freeze)

    paths = []
    for directory in [
        "application",
        "audit",
        "experiment",
        "final_results",
        "freeze",
        "guardrails",
        "pilot",
        "processed",
        "prompts",
        "reports",
        "variants",
    ]:
        for path in sorted((repo_root / directory).rglob("*")):
            if path.is_dir() or "__pycache__" in path.parts or path.name == ".gitkeep":
                continue
            paths.append(path)
    paths.append(repo_root / "MUTATION_VALIDATION.csv")
    paths.append(repo_root / "MUTATION_PLAN.csv")
    unique_paths = []
    seen = set()
    for path in paths:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        unique_paths.append(path)
    lines = []
    for path in unique_paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(repo_root)}")
    _write_text(repo_root / "freeze" / "hashes.sha256", "\n".join(lines) + "\n")


def _checklist_path_for_requirement(requirement_id: str) -> str:
    repo_root = _repo_root()
    for path in sorted((repo_root / "requirements" / "obligation_checklists" / "FINAL").glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        for checklist in data["checklists"]:
            if checklist["requirement_id"] == requirement_id:
                return str(path.relative_to(repo_root))
    raise KeyError(requirement_id)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False))


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n")
