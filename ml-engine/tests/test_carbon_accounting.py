import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CARBON = ROOT / "ml-engine" / "carbon"
MODELS = ROOT / "ml-engine" / "models"
sys.path.insert(0, str(CARBON))
sys.path.insert(0, str(MODELS))

from cci import CCIValidationError, compute_cci
from e_waste import EWasteValidationError, calculate_e_waste
from embodied_carbon import predict_embodied_carbon, reported_lca_value
from operational_carbon import OperationalCarbonValidationError, calculate_from_power, calculate_operational_carbon
from stec import STECIncompleteError, calculate_stec, stec_status
from uncertainty import UncertaintyValidationError, summarize_interval, summarize_samples


class CarbonAccountingTests(unittest.TestCase):
    def test_phase4_prediction_is_not_reported_lca(self):
        model_path = ROOT / "ml-engine" / "artifacts" / "embodied_carbon_model.joblib"
        if not model_path.exists():
            self.skipTest("Phase 4 artifact is not available")
        features = pd.DataFrame(
            {
                "Process Size (nm)": [7.0],
                "TDP (W)": [300.0],
                "DieSizeValue": [628.0],
                "#dies": [1],
                "Avg Die Area": [628.0],
            }
        )
        result = predict_embodied_carbon(model_path, features)[0]
        self.assertEqual(result.value_kind, "model_prediction")
        self.assertEqual(result.unit, "kg_co2e")
        self.assertGreaterEqual(result.value, 0)
        measured = reported_lca_value(
            10,
            unit="kg_co2e",
            source="example LCA",
            functional_unit="one processor",
            boundary="cradle to grave",
        )
        self.assertEqual(measured.value_kind, "reported_or_measured_lca")

    def test_operational_carbon_equation_and_power_conversion(self):
        result = calculate_operational_carbon(
            10,
            0.5,
            grid_intensity_source="approved grid inventory",
            analysis_period="2025",
        )
        self.assertEqual(result.carbon_kg_co2e, 5.0)
        power_result = calculate_from_power(
            100,
            2,
            0.5,
            grid_intensity_source="approved grid inventory",
            analysis_period="2025",
            utilization=0.5,
        )
        self.assertEqual(power_result.electricity_kwh, 0.1)
        self.assertEqual(power_result.carbon_kg_co2e, 0.05)

    def test_operational_carbon_rejects_negative_input(self):
        with self.assertRaises(OperationalCarbonValidationError):
            calculate_operational_carbon(
                -1,
                0.5,
                grid_intensity_source="source",
                analysis_period="2025",
            )

    def test_cci_requires_positive_equivalent_work(self):
        result = compute_cci(
            20,
            4,
            workload_unit="completed equivalent training run",
            lifecycle_boundary="embodied plus operational",
            analysis_period="2025",
        )
        self.assertEqual(result.cci_kg_co2e_per_workload, 5.0)
        with self.assertRaises(CCIValidationError):
            compute_cci(
                20,
                0,
                workload_unit="work",
                lifecycle_boundary="boundary",
                analysis_period="2025",
            )

    def test_e_waste_mass_is_conserved_and_separate(self):
        result = calculate_e_waste(
            10,
            reuse_fraction=0.2,
            recycling_fraction=0.5,
            disposal_fraction=0.3,
            scenario_source="approved end-of-life scenario",
        )
        self.assertEqual(result.accounted_mass_kg, 10.0)
        self.assertEqual(result.recycling_mass_kg, 5.0)
        self.assertFalse(hasattr(result, "carbon_kg_co2e"))
        with self.assertRaises(EWasteValidationError):
            calculate_e_waste(
                10,
                reuse_fraction=0.2,
                recycling_fraction=0.2,
                disposal_fraction=0.2,
                scenario_source="source",
            )

    def test_uncertainty_reports_source_and_method_without_calibration_claim(self):
        result = summarize_samples(
            [1, 2, 3, 4],
            unit="kg_co2e",
            source="CarbonSet modeled interval",
        )
        self.assertEqual(result.sample_count, 4)
        self.assertIn("not calibrated coverage", result.method)
        interval = summarize_interval(
            1,
            2,
            3,
            unit="kg_co2e",
            source="reported range",
            uncertainty_kind="source_range",
            method="published min/max",
        )
        self.assertEqual(interval.central_value, 2)
        with self.assertRaises(UncertaintyValidationError):
            summarize_interval(
                3,
                2,
                1,
                unit="kg_co2e",
                source="source",
                uncertainty_kind="range",
                method="published",
            )

    def test_stec_is_explicitly_incomplete(self):
        status = stec_status()
        self.assertEqual(status.status, "incomplete")
        with self.assertRaises(STECIncompleteError):
            calculate_stec()


if __name__ == "__main__":
    unittest.main()
