"""Prepare one compatible source for supervised learning.

This module refuses to create a processed training set until the caller
provides a verified target, explicit units, and a hardware grouping column.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

try:
	from clean_data import NoValidTargetError, clean_frame
	from feature_engineering import build_feature_frame
except ImportError:
	from .clean_data import NoValidTargetError, clean_frame
	from .feature_engineering import build_feature_frame


SUPPORTED_SUFFIXES = {".csv", ".xls", ".xlsx", ".xlsm"}
DEFAULT_RAW_ROOT = Path(__file__).resolve().parents[2] / "data" / "raw"
DEFAULT_INTERIM_ROOT = Path(__file__).resolve().parents[2] / "data" / "interim"
DEFAULT_PROCESSED_ROOT = Path(__file__).resolve().parents[2] / "data" / "processed"


def load_source_frames(raw_root: Path, source: str) -> list[tuple[str, pd.DataFrame]]:
	"""Load one source only; source mixing is intentionally unsupported."""
	source_root = raw_root / source
	files = sorted(
		path for path in source_root.rglob("*")
		if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
	) if source_root.exists() else []
	loaded: list[tuple[str, pd.DataFrame]] = []
	for path in files:
		if path.suffix.lower() == ".csv":
			loaded.append((f"{source}:{path.name}", pd.read_csv(path)))
			continue
		workbook = pd.ExcelFile(path)
		for sheet in workbook.sheet_names:
			loaded.append(
				(f"{source}:{path.name}#{sheet}", pd.read_excel(path, sheet_name=sheet))
			)
	return loaded


def split_by_hardware_group(
	frame: pd.DataFrame,
	*,
	group_column: str,
	seed: int = 42,
	validation_fraction: float = 0.2,
	test_fraction: float = 0.2,
) -> dict[str, pd.DataFrame]:
	"""Split by hardware group so related observations cannot cross partitions."""
	if not 0 < validation_fraction < 1 or not 0 < test_fraction < 1:
		raise ValueError("Validation and test fractions must be between 0 and 1")
	if validation_fraction + test_fraction >= 1:
		raise ValueError("Validation and test fractions must leave training data")
	if frame[group_column].isna().any():
		raise ValueError("Missing hardware groups prevent leakage-safe splitting")
	if frame[group_column].nunique() < 3:
		raise ValueError("At least three hardware groups are required for three splits")

	first_split = GroupShuffleSplit(n_splits=1, test_size=test_fraction, random_state=seed)
	train_validation_index, test_index = next(
		first_split.split(frame, groups=frame[group_column])
	)
	train_validation = frame.iloc[train_validation_index]
	test = frame.iloc[test_index]
	relative_validation = validation_fraction / (1 - test_fraction)
	second_split = GroupShuffleSplit(n_splits=1, test_size=relative_validation, random_state=seed)
	train_index, validation_index = next(
		second_split.split(train_validation, groups=train_validation[group_column])
	)
	splits = {
		"train": train_validation.iloc[train_index].reset_index(drop=True),
		"validation": train_validation.iloc[validation_index].reset_index(drop=True),
		"test": test.reset_index(drop=True),
	}
	groups = {name: set(part[group_column]) for name, part in splits.items()}
	if groups["train"] & groups["validation"] or groups["train"] & groups["test"] or groups["validation"] & groups["test"]:
		raise RuntimeError("Hardware group leakage detected after splitting")
	return splits


def prepare_dataset(
	*,
	raw_root: Path,
	interim_root: Path,
	processed_root: Path,
	source: str,
	target_column: str | None,
	target_source_unit: str | None,
	target_unit: str | None,
	target_definition: str | None,
	group_column: str | None,
	feature_columns: list[str] | None = None,
	seed: int = 42,
) -> dict[str, Any]:
	interim_root.mkdir(parents=True, exist_ok=True)
	processed_root.mkdir(parents=True, exist_ok=True)
	frames = load_source_frames(raw_root, source)
	if not frames:
		report = {
			"status": "blocked",
			"reason": "No supported local CSV or Excel files were found for the selected source.",
			"source": source,
			"required_next_input": "Approved source data with a verified embodied-carbon target, units, and hardware grouping column.",
		}
		(interim_root / "preprocessing-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
		return report
	if target_column is None or not target_source_unit or not target_unit or not group_column:
		report = {
			"status": "blocked",
			"reason": "Supervised preprocessing requires an explicit target, target definition, source unit, target unit, and hardware group column.",
			"source": source,
			"available_tables": [source_id for source_id, _ in frames],
			"required_next_input": "Verify the target definition and units from the source documentation; provide a group column to prevent related-hardware leakage.",
		}
		(interim_root / "preprocessing-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
		return report
	if not target_definition:
		report = {
			"status": "blocked",
			"reason": "The target definition is missing; a column name alone is not a ground-truth contract.",
			"source": source,
			"required_next_input": "Provide the exact target boundary, functional unit, and label definition from the source documentation.",
		}
		(interim_root / "preprocessing-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
		return report
	schemas = {tuple(str(column) for column in frame.columns) for _, frame in frames}
	if len(schemas) != 1:
		report = {
			"status": "blocked",
			"reason": "Input tables within the selected source have incompatible schemas and were not merged.",
			"source": source,
			"available_tables": [source_id for source_id, _ in frames],
			"required_next_input": "Select one compatible table or provide a documented harmonization contract; do not merge by position or guessed names.",
		}
		(interim_root / "preprocessing-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
		return report

	cleaned = []
	cleaning_reports = []
	for source_id, frame in frames:
		result = clean_frame(
			frame,
			source_id=source_id,
			target_column=target_column,
			target_unit=target_unit,
			target_source_unit=target_source_unit,
			group_column=group_column,
			feature_columns=feature_columns,
		)
		cleaned.append(result.frame)
		cleaning_reports.append(result.report)
	combined = pd.concat(cleaned, ignore_index=True)
	features, selected_features, feature_report = build_feature_frame(
		combined,
		target_column=target_column,
		group_column=group_column,
		feature_columns=feature_columns,
	)
	model_frame = features.copy()
	model_frame[target_column] = combined[target_column].to_numpy()
	model_frame[group_column] = combined[group_column].to_numpy()
	splits = split_by_hardware_group(model_frame, group_column=group_column, seed=seed)
	report = {
		"status": "prepared",
		"source": source,
		"seed": seed,
		"target": {"column": target_column, "unit": target_unit, "definition": target_definition},
		"cleaning": cleaning_reports,
		"features": feature_report,
		"split_strategy": "GroupShuffleSplit twice; hardware groups are disjoint across train/validation/test",
		"rows": {name: len(part) for name, part in splits.items()},
	}
	combined.to_csv(interim_root / f"{source}-cleaned.csv", index=False)
	for name, split in splits.items():
		split.to_csv(processed_root / f"{source}-{name}.csv", index=False)
	(interim_root / "preprocessing-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
	return report


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--source", choices=("scarif", "carbonset", "environmental"), required=True)
	parser.add_argument("--target-column")
	parser.add_argument("--target-source-unit")
	parser.add_argument("--target-unit")
	parser.add_argument("--target-definition")
	parser.add_argument("--group-column")
	parser.add_argument("--feature-columns", nargs="*")
	parser.add_argument("--seed", type=int, default=42)
	parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
	parser.add_argument("--interim-root", type=Path, default=DEFAULT_INTERIM_ROOT)
	parser.add_argument("--processed-root", type=Path, default=DEFAULT_PROCESSED_ROOT)
	args = parser.parse_args()
	report = prepare_dataset(
		raw_root=args.raw_root,
		interim_root=args.interim_root,
		processed_root=args.processed_root,
		source=args.source,
		target_column=args.target_column,
		target_source_unit=args.target_source_unit,
		target_unit=args.target_unit,
		target_definition=args.target_definition,
		group_column=args.group_column,
		feature_columns=args.feature_columns,
		seed=args.seed,
	)
	print(json.dumps(report, indent=2))
	if report["status"] == "blocked":
		raise SystemExit(2)


if __name__ == "__main__":
	main()
