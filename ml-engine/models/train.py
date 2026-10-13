"""Train and evaluate an experimental embodied-carbon regression model.

The implementation is SCARIF-informed only in its use of hardware/configuration
features and statistical regression. It does not claim to reproduce SCARIF's
implementation, data, or reported estimator.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor

try:
	from evaluate import evaluate_predictions
except ImportError:
	from .evaluate import evaluate_predictions


class NoValidatedDatasetError(RuntimeError):
	"""Raised when Phase 3 has not produced a valid supervised dataset."""


def _read_phase3_contract(interim_root: Path, source: str) -> dict[str, Any]:
	report_path = interim_root / "preprocessing-report.json"
	if not report_path.exists():
		raise NoValidatedDatasetError("Phase 3 preprocessing-report.json is missing")
	report = json.loads(report_path.read_text(encoding="utf-8"))
	if report.get("status") != "prepared" or report.get("source") != source:
		raise NoValidatedDatasetError(
			"Phase 3 does not contain a prepared validated dataset for this source"
		)
	return report


def _load_split(processed_root: Path, source: str, split: str) -> pd.DataFrame:
	path = processed_root / f"{source}-{split}.csv"
	if not path.exists():
		raise NoValidatedDatasetError(f"Missing validated {split} split: {path}")
	return pd.read_csv(path)


def _validate_splits(
	splits: dict[str, pd.DataFrame],
	*,
	target_column: str,
	feature_columns: list[str],
	group_column: str,
) -> None:
	for split_name, frame in splits.items():
		required = set(feature_columns) | {target_column, group_column}
		missing = sorted(required - set(frame.columns))
		if missing:
			raise NoValidatedDatasetError(f"{split_name} split is missing columns: {missing}")
		if frame[feature_columns + [target_column]].isna().any().any():
			raise NoValidatedDatasetError(f"{split_name} split contains missing model values")
		if not all(pd.api.types.is_numeric_dtype(frame[column]) for column in feature_columns):
			raise NoValidatedDatasetError(f"{split_name} features must all be numeric")
	groups = {name: set(frame[group_column]) for name, frame in splits.items()}
	if groups["train"] & groups["validation"] or groups["train"] & groups["test"] or groups["validation"] & groups["test"]:
		raise NoValidatedDatasetError("Hardware groups overlap across prepared splits")


def _candidate_models(seed: int) -> list[tuple[str, Any]]:
	return [
		("mean_baseline", DummyRegressor(strategy="mean")),
		(
			"random_forest_depth_none_leaf_1",
			RandomForestRegressor(
				n_estimators=100,
				max_depth=None,
				min_samples_leaf=1,
				random_state=seed,
				n_jobs=-1,
			),
		),
		(
			"random_forest_depth_10_leaf_1",
			RandomForestRegressor(
				n_estimators=100,
				max_depth=10,
				min_samples_leaf=1,
				random_state=seed,
				n_jobs=-1,
			),
		),
		(
			"random_forest_depth_none_leaf_2",
			RandomForestRegressor(
				n_estimators=100,
				max_depth=None,
				min_samples_leaf=2,
				random_state=seed,
				n_jobs=-1,
			),
		),
	]


def train_model(
	*,
	processed_root: Path,
	interim_root: Path,
	artifact_path: Path,
	metadata_path: Path,
	source: str,
	dataset_version: str,
	seed: int = 42,
) -> dict[str, Any]:
	contract = _read_phase3_contract(interim_root, source)
	target = contract.get("target", {})
	target_column = target.get("column")
	target_unit = target.get("unit")
	target_definition = target.get("definition")
	feature_columns = contract.get("features", {}).get("feature_columns", [])
	cleaning_report = contract.get("cleaning", [{}])[0]
	group_column = cleaning_report.get("group_column")
	if not target_column or not target_unit or not target_definition or not feature_columns or not group_column:
		raise NoValidatedDatasetError("Phase 3 contract lacks target, unit, features, or group metadata")

	splits = {name: _load_split(processed_root, source, name) for name in ("train", "validation", "test")}
	_validate_splits(
		splits,
		target_column=target_column,
		feature_columns=feature_columns,
		group_column=group_column,
	)
	x_train = splits["train"][feature_columns]
	y_train = splits["train"][target_column]
	validation_results = {}
	fitted_models = {}
	for name, model in _candidate_models(seed):
		model.fit(x_train, y_train)
		fitted_models[name] = model
		validation_results[name] = evaluate_predictions(
			splits["validation"],
			target_column=target_column,
			predicted=model.predict(splits["validation"][feature_columns]),
			group_column=group_column,
		)
	selected_name = min(
		validation_results,
		key=lambda name: (validation_results[name]["metrics"]["mae"], validation_results[name]["metrics"]["rmse"]),
	)
	selected_model = fitted_models[selected_name]
	test_predictions = selected_model.predict(splits["test"][feature_columns])
	test_results = evaluate_predictions(
		splits["test"],
		target_column=target_column,
		predicted=test_predictions,
		group_column=group_column,
	)
	metadata = {
		"model_type": selected_name,
		"experimental_status": "experimental baseline; not a validated SCARIF reproduction",
		"methodology_note": "SCARIF documentation supports server-level statistical estimation from hardware/configuration features; it does not verify Random Forest as SCARIF's original algorithm.",
		"source": source,
		"dataset_version": dataset_version,
		"seed": seed,
		"feature_definitions": {column: "validated Phase 3 numeric hardware feature" for column in feature_columns},
		"feature_columns": feature_columns,
		"target": {"column": target_column, "unit": target_unit, "definition": target_definition},
		"group_column": group_column,
		"validation_model_comparison": validation_results,
		"selected_validation_metrics": validation_results[selected_name]["metrics"],
		"held_out_test": test_results,
		"training_rows": len(splits["train"]),
		"validation_rows": len(splits["validation"]),
		"test_rows": len(splits["test"]),
	}
	artifact = {
		"model": selected_model,
		"feature_columns": feature_columns,
		"target": metadata["target"],
		"dataset_version": dataset_version,
		"metadata": metadata,
	}
	artifact_path.parent.mkdir(parents=True, exist_ok=True)
	metadata_path.parent.mkdir(parents=True, exist_ok=True)
	joblib.dump(artifact, artifact_path)
	metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
	return metadata


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--source", choices=("scarif", "carbonset", "environmental"), required=True)
	parser.add_argument("--dataset-version", required=True)
	parser.add_argument("--processed-root", type=Path, default=Path(__file__).resolve().parents[2] / "data" / "processed")
	parser.add_argument("--interim-root", type=Path, default=Path(__file__).resolve().parents[2] / "data" / "interim")
	parser.add_argument("--artifact-path", type=Path, default=Path(__file__).resolve().parents[1] / "artifacts" / "embodied_carbon_model.joblib")
	parser.add_argument("--metadata-path", type=Path, default=Path(__file__).resolve().parents[1] / "artifacts" / "embodied_carbon_model.json")
	parser.add_argument("--seed", type=int, default=42)
	args = parser.parse_args()
	try:
		metadata = train_model(
			processed_root=args.processed_root,
			interim_root=args.interim_root,
			artifact_path=args.artifact_path,
			metadata_path=args.metadata_path,
			source=args.source,
			dataset_version=args.dataset_version,
			seed=args.seed,
		)
	except NoValidatedDatasetError as error:
		print(json.dumps({
			"status": "blocked",
			"reason": str(error),
			"required_next_input": "A Phase 3 prepared dataset with a verified embodied-carbon target and disjoint hardware-group splits.",
		}, indent=2))
		raise SystemExit(2)
	print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
	main()
