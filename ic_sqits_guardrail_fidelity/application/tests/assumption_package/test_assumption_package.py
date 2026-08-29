import unittest
from pathlib import Path

from experiment.assumption_package import (
    ASSUMPTION_APPROVER,
    ASSUMPTION_DATE,
    assumption_banner,
    build_boundary_rows,
    build_expected_verdict_rows,
    build_mutation_validation_rows,
    build_valid_alternative_rows,
    load_approved_mutations,
    write_assumption_artifacts,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MUTATION_PLAN = REPO_ROOT / "MUTATION_PLAN.csv"


class AssumptionPackageTests(unittest.TestCase):
    def test_builds_expected_row_counts(self):
        approved = load_approved_mutations(MUTATION_PLAN)
        self.assertEqual(96, len(approved))

        mutation_validation_rows = build_mutation_validation_rows(approved)
        valid_alternative_rows = build_valid_alternative_rows(approved)
        boundary_rows = build_boundary_rows()
        expected_verdict_rows = build_expected_verdict_rows(approved, valid_alternative_rows, boundary_rows)

        self.assertEqual(96, len(mutation_validation_rows))
        self.assertEqual(48, len(valid_alternative_rows))
        self.assertEqual(12, len(boundary_rows))
        self.assertEqual(204, len(expected_verdict_rows))
        self.assertEqual({"violating", "non_violating"}, {row["expected_guardrail_verdict"] for row in expected_verdict_rows})

    def test_assumption_rows_are_labeled_honestly(self):
        approved = load_approved_mutations(MUTATION_PLAN)
        mutation_validation_rows = build_mutation_validation_rows(approved)
        valid_alternative_rows = build_valid_alternative_rows(approved)
        boundary_rows = build_boundary_rows()

        self.assertTrue(all(row["human_approved_by"] == ASSUMPTION_APPROVER for row in mutation_validation_rows))
        self.assertTrue(all(row["approval_date"] == ASSUMPTION_DATE for row in mutation_validation_rows))
        self.assertTrue(all(row["validation_basis"] == "assumption_mode_user_instruction" for row in mutation_validation_rows))
        self.assertTrue(all(row["review_status"] == "ASSUMED_APPROVED_COMPLIANT" for row in valid_alternative_rows))
        self.assertTrue(all(row["review_status"] == "ASSUMED_APPROVED_VALID_BOUNDARY" for row in boundary_rows))

    def test_banner_declares_non_protocol_valid_state(self):
        banner = assumption_banner()
        self.assertIn("ASSUMPTION_BASED_DRAFT", banner)
        self.assertIn("Not protocol-valid final results", banner)

    def test_writer_emits_key_scaffold_files(self):
        counts = write_assumption_artifacts(REPO_ROOT)
        self.assertEqual(48, counts["requirements"])

        for relative_path in [
            "experiment/runner.py",
            "experiment/evaluator.py",
            "experiment/validators.py",
            "experiment/freeze.py",
            "freeze/EXPERIMENT_FREEZE.md",
            "freeze/hashes.sha256",
            "reports/STEP_23_REPORT.md",
            "reports/STEP_48_REPORT.md",
        ]:
            self.assertTrue((REPO_ROOT / relative_path).exists(), relative_path)

        step_48 = (REPO_ROOT / "reports/STEP_48_REPORT.md").read_text()
        self.assertTrue(step_48.startswith("# STEP_48_REPORT\n"))
        self.assertIn("ASSUMPTION_BASED_DRAFT", step_48)


if __name__ == "__main__":
    unittest.main()
