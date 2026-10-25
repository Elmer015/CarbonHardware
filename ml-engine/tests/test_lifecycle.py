import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml-engine" / "carbon"))

from grid_intensity import GridIntensityUnavailableError, grid_intensity, list_regions
from lifecycle import LifecycleValidationError, estimate_lifecycle

USAGE = {"tdpW": 180, "hoursPerDay": 8, "daysPerYear": 365, "usageYears": 5, "utilization": 0.7}


class GridIntensityTests(unittest.TestCase):
    def test_lookup_returns_sourced_location_based_value(self):
        grid = grid_intensity("Taiwan", 2022)
        self.assertAlmostEqual(grid.g_co2e_per_kwh, 639.23)
        self.assertAlmostEqual(grid.kg_co2e_per_kwh, 0.63923)
        self.assertEqual(grid.basis, "location-based")
        self.assertTrue(any(item["region"] == "Indonesia" for item in list_regions()["regions"]))

    def test_missing_year_is_not_extrapolated(self):
        with self.assertRaises(GridIntensityUnavailableError):
            grid_intensity("Indonesia", 1990)


class LifecycleTests(unittest.TestCase):
    def payload(self, **overrides):
        base = {
            "embodied": {"value": 10.0, "lowerValue": 8.0, "upperValue": 14.0, "intervalSource": "CarbonSet min/mean/max"},
            "usage": {**USAGE, "usageRegion": "Indonesia", "gridYear": 2024},
            "workload": {"completedComputeWork": 100, "workloadUnit": "compute-hour"},
            "samples": 2000,
        }
        base.update(overrides)
        return base

    def test_operational_total_and_final_cci(self):
        result = estimate_lifecycle(self.payload())
        self.assertAlmostEqual(result["electricityKwh"], 1839.6)
        operational = 1839.6 * 0.68025
        self.assertAlmostEqual(result["operational"]["carbonKgCo2e"], operational, places=6)
        self.assertAlmostEqual(result["totalKgCo2e"], 10.0 + operational, places=6)
        self.assertAlmostEqual(result["cci"]["cciKgCo2ePerWorkload"], (10.0 + operational) / 100, places=6)
        self.assertEqual((result["cci"]["status"], result["status"]), ("final", "complete"))

    def test_without_grid_operational_is_pending_and_cci_is_embodied_only(self):
        result = estimate_lifecycle(self.payload(usage=dict(USAGE)))
        self.assertIsNone(result["operational"])
        self.assertIsNone(result["totalKgCo2e"])
        self.assertEqual(result["status"], "operational_pending_grid")
        self.assertEqual(result["cci"]["status"], "embodied_only")
        self.assertAlmostEqual(result["cci"]["cciKgCo2ePerWorkload"], 0.1)

    def test_supplied_grid_value_requires_a_source(self):
        with self.assertRaises(LifecycleValidationError):
            estimate_lifecycle(self.payload(usage={**USAGE, "gridIntensityKgCo2ePerKwh": 0.5}))
        result = estimate_lifecycle(self.payload(usage={**USAGE, "gridIntensityKgCo2ePerKwh": 0.5, "gridIntensitySource": "utility report 2024"}))
        self.assertAlmostEqual(result["operational"]["carbonKgCo2e"], 1839.6 * 0.5)

    def test_distributions_propagate_and_are_reproducible(self):
        distributions = {
            "tdpW": {"min": 150, "mostLikely": 180, "max": 220},
            "utilization": {"min": 0.4, "mostLikely": 0.7, "max": 0.95},
            "gridIntensityKgCo2ePerKwh": {"min": 0.55, "mostLikely": 0.66724, "max": 0.8},
        }
        first = estimate_lifecycle(self.payload(distributions=distributions))
        second = estimate_lifecycle(self.payload(distributions=distributions))
        total = first["uncertainty"]["total"]
        self.assertEqual(total, second["uncertainty"]["total"])
        self.assertLess(total["p2_5"], first["totalKgCo2e"])
        self.assertGreater(total["p97_5"], first["totalKgCo2e"])
        self.assertIn("tdpW", first["uncertainty"]["variedInputs"])
        self.assertAlmostEqual(first["grid"]["kgCo2ePerKwh"], 0.66724)
        self.assertIn("cci", first["uncertainty"])

    def test_grid_range_without_mode_keeps_the_sourced_value(self):
        result = estimate_lifecycle(self.payload(distributions={"gridIntensityKgCo2ePerKwh": {"min": 0.6, "max": 0.75}}))
        self.assertAlmostEqual(result["grid"]["kgCo2ePerKwh"], 0.68025)
        self.assertNotIn("note", result["grid"])
        self.assertIn("gridIntensityKgCo2ePerKwh", result["uncertainty"]["variedInputs"])
        with self.assertRaises(LifecycleValidationError):
            estimate_lifecycle(self.payload(distributions={"gridIntensityKgCo2ePerKwh": {"min": 0.7, "max": 0.8}}))

    def test_no_distribution_collapses_to_point(self):
        result = estimate_lifecycle(self.payload(embodied={"value": 10.0}))
        total = result["uncertainty"]["total"]
        self.assertAlmostEqual(total["p2_5"], total["p97_5"])
        self.assertTrue(any("collapse" in warning for warning in result["warnings"]))

    def test_custom_model_prediction_uses_empirical_interval(self):
        result = estimate_lifecycle(self.payload(embodied={"value": 10.0, "valueKind": "model_prediction"}))
        self.assertEqual(result["embodied"]["intervalKind"], "model_prediction_interval")
        self.assertLess(result["embodied"]["lowerKgCo2e"], 10.0)
        self.assertGreater(result["embodied"]["upperKgCo2e"], 10.0)

    def test_invalid_distribution_is_rejected(self):
        with self.assertRaises(LifecycleValidationError):
            estimate_lifecycle(self.payload(distributions={"tdpW": {"min": 200, "mostLikely": 180, "max": 220}}))
        with self.assertRaises(LifecycleValidationError):
            estimate_lifecycle(self.payload(distributions={"utilization": {"min": 0.5, "mostLikely": 0.9, "max": 1.2}}))


if __name__ == "__main__":
    unittest.main()
