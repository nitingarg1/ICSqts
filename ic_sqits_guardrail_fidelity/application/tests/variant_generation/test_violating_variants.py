import csv
import json
import tempfile
import unittest
from pathlib import Path

from variants.variant_tools import approved_rows, materialize_variant


REPO_ROOT = Path(__file__).resolve().parents[3]
MUTATION_PLAN = REPO_ROOT / "MUTATION_PLAN.csv"
VIOLATING_ROOT = REPO_ROOT / "variants" / "violating"
REFERENCE_SERVICE = REPO_ROOT / "application" / "reference" / "service.py"


class ViolatingVariantArtifactTests(unittest.TestCase):
    def test_every_approved_mutation_has_variant_artifacts(self):
        rows = approved_rows(MUTATION_PLAN)

        self.assertGreater(len(rows), 0)

        for row in rows:
            variant_dir = VIOLATING_ROOT / row["requirement_id"] / row["mutation_id"]
            manifest_path = variant_dir / "manifest.json"
            diff_path = variant_dir / "diff.patch"

            self.assertTrue(variant_dir.is_dir(), row["mutation_id"])
            self.assertTrue(manifest_path.is_file(), row["mutation_id"])
            self.assertTrue(diff_path.is_file(), row["mutation_id"])

            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(row["mutation_id"], manifest["mutation_id"])
            self.assertEqual(row["requirement_id"], manifest["requirement_id"])
            self.assertEqual(row["target_obligation_id"], manifest["target_obligation_id"])
            self.assertEqual("violating", manifest["variant_type"])
            self.assertTrue(manifest["operations"])
            self.assertTrue(diff_path.read_text().strip())

    def test_every_approved_manifest_materializes_valid_python(self):
        baseline_text = REFERENCE_SERVICE.read_text()
        rows = approved_rows(MUTATION_PLAN)

        with tempfile.TemporaryDirectory(prefix="ic-sqits-variants-") as temp_dir:
            temp_root = Path(temp_dir)
            for row in rows:
                manifest_path = VIOLATING_ROOT / row["requirement_id"] / row["mutation_id"] / "manifest.json"
                generated = materialize_variant(manifest_path, temp_root / row["mutation_id"])
                generated_text = generated.read_text()

                self.assertNotEqual(baseline_text, generated_text, row["mutation_id"])
                compile(generated_text, str(generated), "exec")


if __name__ == "__main__":
    unittest.main()
