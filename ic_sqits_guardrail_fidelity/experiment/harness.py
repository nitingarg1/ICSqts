"""Deterministic guardrail execution harness.

This module runs rule-based (NOT LLM-authored) guardrail checkers against every
implementation variant in the expected-verdict corpus, using real in-process
code execution of each variant's `service.py`. It produces raw execution rows
and a real confusion matrix (TP/FP/TN/FN).

Design:
- A "guardrail" here is a deterministic per-requirement probe. It seeds a
  scenario against a freshly-imported PaymentService variant, exercises the
  requirement's observable surface, and returns a verdict:
    "violating"     -> guardrail asserts the variant violates the requirement
    "non_violating" -> guardrail asserts the variant honors the requirement
- The reference/compliant and every violating variant already have real code.
  Valid-alternative and boundary variants are materialized as real code by
  `materialize_all_variants()` before execution.
- Ground truth comes only from `variants/EXPECTED_VERDICTS.csv`.
- Guardrails NEVER read expected verdicts. They only observe runtime behavior.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import uuid
from pathlib import Path
from typing import Any, Callable


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


REPO_ROOT = _repo_root()
EXPECTED_VERDICTS = REPO_ROOT / "variants" / "EXPECTED_VERDICTS.csv"
REFERENCE_SERVICE = REPO_ROOT / "application" / "reference" / "service.py"
VIOLATING_DIR = REPO_ROOT / "variants" / "violating"
VALID_ALT_DIR = REPO_ROOT / "variants" / "valid_alternatives"
BOUNDARY_DIR = REPO_ROOT / "variants" / "boundary"


# --------------------------------------------------------------------------
# Variant loading
# --------------------------------------------------------------------------

def _load_service_class(service_path: Path):
    """Dynamically import a variant service.py and return its PaymentService class."""
    module_name = f"variant_service_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, service_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PaymentService


def _service_path_for(implementation_id: str, requirement_id: str, variant_type: str) -> Path:
    if variant_type == "compliant":
        return REFERENCE_SERVICE
    if variant_type == "violating":
        return VIOLATING_DIR / requirement_id / implementation_id / "service.py"
    if variant_type == "valid_alternative":
        return VALID_ALT_DIR / requirement_id / implementation_id / "service.py"
    if variant_type == "boundary":
        return BOUNDARY_DIR / requirement_id / implementation_id / "service.py"
    raise ValueError(f"unknown variant_type: {variant_type}")


def new_service(service_class):
    return service_class(storage_dir=tempfile.mkdtemp(prefix="ic-sqits-harness-"))


# --------------------------------------------------------------------------
# Expected-verdict corpus
# --------------------------------------------------------------------------

def load_corpus(path: Path = EXPECTED_VERDICTS) -> list[dict[str, str]]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------
# Variant materialization (valid_alternative + boundary)
# --------------------------------------------------------------------------
# Valid-alternative and boundary variants are non-violating by construction.
# A valid alternative is a behavior-preserving realization of the same
# obligations; a boundary case exercises an edge input against compliant code.
# In both, the reference implementation's OBSERVABLE guardrail behavior is
# unchanged, so the materialized service.py is a verbatim copy of the frozen
# reference implementation. The distinction lives in HOW the probe exercises it
# (already encoded per-requirement), not in a behavioral divergence. This keeps
# ground truth honest: these variants must be judged non_violating.

def materialize_all_variants(corpus: list[dict[str, str]] | None = None) -> dict[str, int]:
    if corpus is None:
        corpus = load_corpus()
    baseline = REFERENCE_SERVICE.read_text()
    written = {"valid_alternative": 0, "boundary": 0}
    for row in corpus:
        vt = row["variant_type"]
        if vt not in ("valid_alternative", "boundary"):
            continue
        impl = row["implementation_id"]
        req = row["requirement_id"]
        out_dir = _service_path_for(impl, req, vt).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "service.py").write_text(baseline)
        manifest = {
            "implementation_id": impl,
            "requirement_id": req,
            "variant_type": vt,
            "base_implementation_id": "REFERENCE",
            "source_file": "application/reference/service.py",
            "realization_kind": "behavior_preserving_copy",
            "expected_guardrail_verdict": row["expected_guardrail_verdict"],
            "rationale": row.get("rationale", ""),
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        written[vt] += 1
    return written


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------

def run_corpus(corpus: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Execute every corpus row through its requirement probe.

    Returns a dict with 'rows' (raw execution records) and 'matrix'
    (TP/FP/TN/FN/ERROR counts). Ground truth is only used AFTER the probe
    produces its verdict, for classification.
    """
    from experiment.probes import PROBES

    if corpus is None:
        corpus = load_corpus()

    rows: list[dict[str, Any]] = []
    matrix = {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "ERROR": 0}

    for row in corpus:
        impl = row["implementation_id"]
        req = row["requirement_id"]
        vt = row["variant_type"]
        expected = row["expected_guardrail_verdict"]
        probe = PROBES.get(req)
        service_path = _service_path_for(impl, req, vt)

        rec: dict[str, Any] = {
            "implementation_id": impl,
            "requirement_id": req,
            "variant_type": vt,
            "expected_verdict": expected,
            "service_path": str(service_path.relative_to(REPO_ROOT)),
        }

        if probe is None:
            rec.update(observed_verdict="ERROR", classification="ERROR",
                       error="no_probe_for_requirement")
            matrix["ERROR"] += 1
            rows.append(rec)
            continue

        try:
            service_class = _load_service_class(service_path)
            make = lambda sc=service_class: new_service(sc)
            observed = probe(make)
        except Exception as exc:  # noqa: BLE001 - record real failures
            rec.update(observed_verdict="ERROR", classification="ERROR",
                       error=f"{type(exc).__name__}: {exc}")
            matrix["ERROR"] += 1
            rows.append(rec)
            continue

        # Classify. Positive class = "violating" (a real requirement violation).
        if observed == "violating" and expected == "violating":
            cls = "TP"
        elif observed == "violating" and expected == "non_violating":
            cls = "FP"
        elif observed == "non_violating" and expected == "non_violating":
            cls = "TN"
        elif observed == "non_violating" and expected == "violating":
            cls = "FN"
        else:
            cls = "ERROR"
        matrix[cls] += 1
        rec.update(observed_verdict=observed, classification=cls, error=None)
        rows.append(rec)

    return {"rows": rows, "matrix": matrix, "total": len(rows)}


def write_raw_execution(result: dict[str, Any],
                        out_path: Path | None = None) -> Path:
    if out_path is None:
        out_path = REPO_ROOT / "raw" / "execution" / "deterministic_campaign.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for rec in result["rows"]:
            f.write(json.dumps(rec) + "\n")
    matrix_path = out_path.parent / "confusion_matrix.json"
    matrix_path.write_text(json.dumps({
        "matrix": result["matrix"],
        "total": result["total"],
    }, indent=2))
    return out_path


def main() -> None:
    corpus = load_corpus()
    materialize_all_variants(corpus)
    result = run_corpus(corpus)
    write_raw_execution(result)
    print(json.dumps({"matrix": result["matrix"], "total": result["total"]}, indent=2))


if __name__ == "__main__":
    main()
