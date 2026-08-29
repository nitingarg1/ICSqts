"""Deterministic metric computation for the guardrail-fidelity experiment.

This module reads ONLY raw execution artifacts (`raw/execution/*.jsonl`) plus the
frozen requirement-to-category mapping, and derives every reported number from
those rows. No metric is authored by hand and none depends on an LLM. Every
output is fully recomputable from the raw campaign file, satisfying the
raw-only-provenance rule in `research/ANALYSIS_PLAN.md`.

Run:  python3 -m experiment.metrics
"""

from __future__ import annotations

import csv
import json
import os
from collections import defaultdict

import yaml


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


REPO_ROOT = _repo_root()
RAW_CAMPAIGN = os.path.join(REPO_ROOT, "raw", "execution", "deterministic_campaign.jsonl")
REQUIREMENTS = os.path.join(REPO_ROOT, "requirements", "requirements_v1.yaml")
PROCESSED_DIR = os.path.join(REPO_ROOT, "processed")


def load_raw(path=RAW_CAMPAIGN):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def requirement_categories(path=REQUIREMENTS):
    data = yaml.safe_load(open(path))
    return {r["requirement_id"]: r["category"] for r in data["requirements"]}


def _prf(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    if precision and recall and (precision + recall):
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = None
    return precision, recall, f1


def compute(rows, categories):
    """Return a nested metric structure derived purely from raw rows."""
    overall = defaultdict(int)
    per_category = defaultdict(lambda: defaultdict(int))
    per_variant = defaultdict(lambda: defaultdict(int))

    for r in rows:
        cls = r["classification"]
        cat = categories.get(r["requirement_id"], "unknown")
        vtype = r["variant_type"]
        overall[cls] += 1
        per_category[cat][cls] += 1
        per_variant[vtype][cls] += 1

    def block(counts):
        tp = counts.get("TP", 0)
        fp = counts.get("FP", 0)
        tn = counts.get("TN", 0)
        fn = counts.get("FN", 0)
        err = counts.get("ERROR", 0)
        precision, recall, f1 = _prf(tp, fp, fn)
        valid_non_violating = tp + fp + tn + fn  # all rows minus error
        over_constraint = fp / (fp + tn) if (fp + tn) else None
        return {
            "TP": tp, "FP": fp, "TN": tn, "FN": fn, "ERROR": err,
            "total": tp + fp + tn + fn + err,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "over_constraint_rate": over_constraint,
            "execution_error_rate": err / (tp + fp + tn + fn + err) if rows else None,
        }

    return {
        "overall": block(overall),
        "per_category": {c: block(v) for c, v in sorted(per_category.items())},
        "per_variant_type": {c: block(v) for c, v in sorted(per_variant.items())},
    }


def _fmt(x):
    return "" if x is None else (f"{x:.4f}" if isinstance(x, float) else x)


def write_processed(metrics, out_dir=PROCESSED_DIR):
    os.makedirs(out_dir, exist_ok=True)

    # guardrail_level_results.csv: one row per slice
    slice_rows = []
    slice_rows.append(("overall", "overall", metrics["overall"]))
    for c, m in metrics["per_category"].items():
        slice_rows.append(("category", c, m))
    for c, m in metrics["per_variant_type"].items():
        slice_rows.append(("variant_type", c, m))

    detection_path = os.path.join(out_dir, "implementation_level_results.csv")
    with open(detection_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "slice_name", "slice_value", "TP", "FP", "TN", "FN", "ERROR", "total",
            "precision", "recall", "f1", "over_constraint_rate", "execution_error_rate",
        ])
        for sname, sval, m in slice_rows:
            w.writerow([
                sname, sval, m["TP"], m["FP"], m["TN"], m["FN"], m["ERROR"], m["total"],
                _fmt(m["precision"]), _fmt(m["recall"]), _fmt(m["f1"]),
                _fmt(m["over_constraint_rate"]), _fmt(m["execution_error_rate"]),
            ])

    metrics_json = os.path.join(out_dir, "metrics.json")
    with open(metrics_json, "w") as f:
        json.dump(metrics, f, indent=2)

    return {"implementation_level_results": detection_path, "metrics_json": metrics_json}


def main():
    rows = load_raw()
    cats = requirement_categories()
    metrics = compute(rows, cats)
    paths = write_processed(metrics)
    print(json.dumps(metrics["overall"], indent=2))
    print("wrote", paths["implementation_level_results"])
    print("wrote", paths["metrics_json"])
    return metrics


if __name__ == "__main__":
    main()
