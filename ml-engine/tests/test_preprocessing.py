import sys
import unittest
from pathlib import Path

import pandas as pd

DATA_PROCESSING = Path(__file__).resolve().parents[1] / "data_processing"
sys.path.insert(0, str(DATA_PROCESSING))

from clean_data import DatasetValidationError, NoValidTargetError, clean_frame, convert_units
from feature_engineering import select_hardware_features
from prepare_dataset import split_by_hardware_group


class PreprocessingTests(unittest.TestCase):
    def test_supported_unit_conversion_is_explicit(self):
        values = pd.Series([1000.0])
        converted = convert_units(values, "g_co2e", "kg_co2e")
        self.assertEqual(converted.iloc[0], 1.0)

    def test_unsupported_unit_conversion_is_rejected(self):
        with self.assertRaises(DatasetValidationError):
            convert_units(pd.Series([1.0]), "kwh", "kg_co2e")

    def test_missing_target_blocks_supervised_cleaning(self):
        frame = pd.DataFrame({"hardware": ["A100"], "area_mm2": [826]})
        with self.assertRaises(NoValidTargetError):
            clean_frame(
                frame,
                source_id="test",
                target_column=None,
                target_unit=None,
                target_source_unit=None,
                group_column="hardware",
            )

    def test_cleaning_drops_invalid_rows_without_imputation(self):
        frame = pd.DataFrame(
            {
                "hardware": ["A", "A", "B", "C"],
                "area_mm2": [10, 10, None, 30],
                "embodied": [2.0, 2.0, 3.0, -1.0],
            }
        )
        result = clean_frame(
            frame,
            source_id="test",
            target_column="embodied",
            target_unit="kg_co2e",
            target_source_unit="kg_co2e",
            group_column="hardware",
            feature_columns=["area_mm2"],
        )
        self.assertEqual(len(result.frame), 1)
        self.assertEqual(result.report["removed_exact_duplicates"], 1)
        self.assertEqual(result.report["removed_invalid_or_missing_targets"], 1)
        self.assertEqual(result.report["removed_rows_missing_features"], 1)
        self.assertFalse(result.frame.isna().any().any())

    def test_feature_selection_rejects_target_like_columns(self):
        frame = pd.DataFrame(
            {
                "hardware": ["A"],
                "area_mm2": [10],
                "carbon_proxy": [4.0],
                "target": [2.0],
            }
        )
        selected = select_hardware_features(
            frame,
            target_column="target",
            group_column="hardware",
        )
        self.assertEqual(selected, ["area_mm2"])

    def test_group_split_has_disjoint_hardware_groups(self):
        frame = pd.DataFrame(
            {
                "hardware": ["A", "A", "B", "B", "C", "C", "D", "D", "E", "E"],
                "area_mm2": range(10),
                "embodied": range(10),
            }
        )
        splits = split_by_hardware_group(frame, group_column="hardware", seed=42)
        groups = {name: set(part["hardware"]) for name, part in splits.items()}
        self.assertTrue(groups["train"].isdisjoint(groups["validation"]))
        self.assertTrue(groups["train"].isdisjoint(groups["test"]))
        self.assertTrue(groups["validation"].isdisjoint(groups["test"]))


if __name__ == "__main__":
    unittest.main()
