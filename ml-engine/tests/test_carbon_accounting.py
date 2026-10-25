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
from custom_pc import BuildComponent, ComponentFactor, CustomPcValidationError, calculate_custom_pc_embodied_carbon
from e_waste import EWasteValidationError, calculate_e_waste
from embodied_carbon import predict_embodied_carbon, reported_lca_value
from operational_carbon import OperationalCarbonValidationError, calculate_from_power, calculate_from_tdp, calculate_operational_carbon
from stec import STECIncompleteError, STECValidationError, calculate_stec, stec_status
from uncertainty import UncertaintyValidationError, summarize_interval, summarize_samples


class CarbonAccountingTests(unittest.TestCase):
    def test_custom_pc_requires_all_component_factors_for_a_total(self):
        factors = [
            ComponentFactor("cpu-example", "cpu", "Example CPU", 20, "verified LCA", "manufacturing"),
            ComponentFactor("ram-16gb", "ram", "16 GB DIMM", 4, "verified LCA", "manufacturing"),
        ]
        result = calculate_custom_pc_embodied_carbon(
            [
                BuildComponent("cpu-example", "cpu"),
                BuildComponent("ram-16gb", "ram", quantity=2),
                BuildComponent("custom-ssd", "storage"),
            ],
            factors,
        )
        self.assertFalse(result.complete)
        self.assertIsNone(result.total_kg_co2e)
        self.assertEqual(result.resolved_subtotal_kg_co2e, 28)
        self.assertEqual(result.components[2].status, "unresolved")

    def test_custom_pc_records_an_explicit_proxy(self):
        factors = [
            ComponentFactor("gpu-proxy", "gpu", "Comparable GPU", 100, "verified LCA", "manufacturing"),
        ]
        result = calculate_custom_pc_embodied_carbon(
            [BuildComponent("requested-gpu", "gpu", proxy_component_id="gpu-proxy")], factors
        )
        self.assertTrue(result.complete)
        self.assertEqual(result.total_kg_co2e, 100)
        self.assertEqual(result.components[0].method, "explicit_proxy_factor")

    def test_custom_pc_rejects_a_cross_type_proxy(self):
        factors = [
            ComponentFactor("cpu-example", "cpu", "Example CPU", 20, "verified LCA", "manufacturing"),
        ]
        with self.assertRaises(CustomPcValidationError):
            calculate_custom_pc_embodied_carbon(
                [BuildComponent("requested-gpu", "gpu", proxy_component_id="cpu-example")], factors
            )

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

    def test_operational_carbon_estimate_from_tdp_uses_assumption_mode(self):
        result = calculate_from_tdp(
            250,
            0.6,
            8,
            365,
            0.5,
            grid_intensity_source="example grid",
            analysis_period="2025",
            assumptions={"method": "TDP-based assumption"},
        )
        self.assertAlmostEqual(result.electricity_kwh, 438.0)
        self.assertAlmostEqual(result.carbon_kg_co2e, 219.0)
        self.assertEqual(result.assumptions["method"], "TDP-based assumption")

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

    def test_stec_reproduces_eq7_with_country_year_ci(self):
        result = calculate_stec(
            die_area_mm2=100,
            node_nm=28,
            grid_intensity_g_co2e_per_kwh=561,
            manufacturing_region="Taiwan",
            manufacturing_year=2022,
        )
        self.assertAlmostEqual(result.intensity_g_per_cm2, 1104.9)
        self.assertAlmostEqual(result.stec_kg_co2e, 1.1049)
        self.assertEqual(result.assumptions["boundary"], "cradle-to-gate die manufacturing")

    def test_stec_records_explicit_node_proxy_and_yield(self):
        result = calculate_stec(
            die_area_mm2=100,
            node_nm=22,
            grid_intensity_g_co2e_per_kwh=500,
            manufacturing_region="Taiwan",
            manufacturing_year=2022,
            yield_factor=0.5,
        )
        self.assertEqual(result.assumptions["explicit_proxy_node"], "22")
        self.assertAlmostEqual(result.stec_kg_co2e, 2.42)

    def test_stec_rejects_unknown_node_and_invalid_yield(self):
        status = stec_status()
        with self.assertRaises(STECIncompleteError):
            calculate_stec(
                die_area_mm2=100,
                node_nm=2,
                grid_intensity_g_co2e_per_kwh=500,
                manufacturing_region="Taiwan",
                manufacturing_year=2022,
            )
        with self.assertRaises(STECValidationError):
            calculate_stec(
                die_area_mm2=100,
                node_nm=28,
                grid_intensity_g_co2e_per_kwh=500,
                manufacturing_region="Taiwan",
                manufacturing_year=2022,
                yield_factor=0,
            )
        self.assertEqual(status.status, "implemented_location_based")


if __name__ == "__main__":
    unittest.main()
