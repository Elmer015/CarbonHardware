import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CARBON = ROOT / "ml-engine" / "carbon"
sys.path.insert(0, str(CARBON))

from stec_batch import build_stec_inventory


class StecBatchTests(unittest.TestCase):
    def test_supplied_inventory_recomputes_all_unique_carbonset_processors(self):
        rows = build_stec_inventory()
        self.assertEqual(len(rows), 1272)
        self.assertEqual(len({row["product"] for row in rows}), 1272)
        self.assertEqual(sum(row["status"] == "point" for row in rows), 659)
        self.assertEqual(sum(row["status"] == "range" for row in rows), 610)
        self.assertEqual(sum(row["status"] == "incomplete" for row in rows), 3)

    def test_product_specific_fab_and_release_year_proxy_are_recorded(self):
        rows = {row["product"]: row for row in build_stec_inventory()}
        a100 = rows["NVIDIA A100 PCIe 40 GB"]
        self.assertEqual(a100["status"], "point")
        self.assertEqual(a100["location_level"], "product_sourced")
        self.assertEqual(a100["candidate_regions"], "Taiwan")
        self.assertEqual(a100["manufacturing_year_status"], "release_year_proxy")
        self.assertAlmostEqual(a100["stec_kg_co2e"], 13.918522912)

    def test_unsupported_chiplet_node_is_not_reported_as_a_complete_total(self):
        rows = {row["product"]: row for row in build_stec_inventory()}
        result = rows["AMD Ryzen 9 3950X"]
        self.assertEqual(result["status"], "incomplete")
        self.assertTrue(result["chiplet_applied"])
        self.assertIsNone(result["stec_kg_co2e"])
        self.assertIn("node 12 nm", result["warnings"])

    def test_ambiguous_fab_location_returns_a_range(self):
        rows = {row["product"]: row for row in build_stec_inventory()}
        result = rows["Intel Core i3-3120M"]
        self.assertEqual(result["status"], "range")
        self.assertIsNone(result["stec_kg_co2e"])
        self.assertLess(result["stec_min_kg_co2e"], result["stec_max_kg_co2e"])
        self.assertIn("Explicit node proxy", result["warnings"])


if __name__ == "__main__":
    unittest.main()
