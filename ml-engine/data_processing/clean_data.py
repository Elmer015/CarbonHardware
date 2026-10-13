"""Schema and record validation for the Phase 3 dataset pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


class DatasetValidationError(ValueError):
	"""Raised when a dataset cannot satisfy the explicit data contract."""


class NoValidTargetError(DatasetValidationError):
	"""Raised when supervised learning has no verified target column."""


@dataclass
class CleaningResult:
	frame: pd.DataFrame
	report: dict[str, Any] = field(default_factory=dict)


SUPPORTED_UNIT_CONVERSIONS = {
	("g_co2e", "kg_co2e"): 0.001,
	("kg_co2e", "g_co2e"): 1000.0,
	("t_co2e", "kg_co2e"): 1000.0,
	("kg_co2e", "t_co2e"): 0.001,
}


def normalize_unit_name(unit: str) -> str:
	return unit.strip().lower().replace(" ", "_").replace("-", "_")


def convert_units(values: pd.Series, source_unit: str, target_unit: str) -> pd.Series:
	"""Convert only explicitly supported CO2e units."""
	source = normalize_unit_name(source_unit)
	target = normalize_unit_name(target_unit)
	if source == target:
		return values.copy()
	factor = SUPPORTED_UNIT_CONVERSIONS.get((source, target))
	if factor is None:
		raise DatasetValidationError(
			f"Unsupported or unjustified unit conversion: {source_unit} -> {target_unit}"
		)
	return pd.to_numeric(values, errors="raise") * factor


def validate_schema(
	frame: pd.DataFrame,
	*,
	target_column: str | None,
	group_column: str | None,
	feature_columns: list[str] | None = None,
) -> list[str]:
	"""Validate explicit columns without guessing a target or unit."""
	if frame.columns.duplicated().any():
		duplicate_columns = frame.columns[frame.columns.duplicated()].tolist()
		raise DatasetValidationError(f"Duplicate column names: {duplicate_columns}")
	if target_column is None:
		raise NoValidTargetError(
			"No target column was supplied. Provide a verified embodied-carbon label "
			"and its source unit before supervised learning."
		)
	required = [target_column]
	if group_column:
		required.append(group_column)
	if feature_columns:
		required.extend(feature_columns)
	missing = sorted(set(column for column in required if column not in frame.columns))
	if missing:
		raise DatasetValidationError(f"Missing required columns: {missing}")
	return feature_columns or [
		column
		for column in frame.select_dtypes(include="number").columns
		if column != target_column
	]


def clean_frame(
	frame: pd.DataFrame,
	*,
	source_id: str,
	target_column: str | None,
	target_unit: str | None,
	target_source_unit: str | None,
	group_column: str | None,
	feature_columns: list[str] | None = None,
) -> CleaningResult:
	"""Return a cleaned copy and an auditable record-level cleaning report."""
	working = frame.copy(deep=True)
	initial_rows = len(working)
	selected_features = validate_schema(
		working,
		target_column=target_column,
		group_column=group_column,
		feature_columns=feature_columns,
	)
	if not target_unit or not target_source_unit:
		raise NoValidTargetError(
			"A verified target requires both target_unit and target_source_unit; "
			"the pipeline will not infer units from a column name."
		)

	empty_rows = working.isna().all(axis=1)
	working = working.loc[~empty_rows].copy()
	duplicate_rows = working.duplicated(keep="first")
	working = working.loc[~duplicate_rows].copy()

	target_values = pd.to_numeric(working[target_column], errors="coerce")
	invalid_target = target_values.isna() | ~target_values.notna()
	invalid_target |= target_values < 0
	working = working.loc[~invalid_target].copy()
	target_values = pd.to_numeric(working[target_column], errors="raise")
	working[target_column] = convert_units(target_values, target_source_unit, target_unit)

	missing_features = working[selected_features].isna().any(axis=1)
	working = working.loc[~missing_features].copy()
	if group_column and working[group_column].isna().any():
		working = working.loc[working[group_column].notna()].copy()
	if working.empty:
		raise NoValidTargetError(
			f"Source {source_id} has no valid labeled rows after validation. "
			"Obtain non-missing, non-negative embodied-carbon labels."
		)

	report = {
		"source_id": source_id,
		"initial_rows": initial_rows,
		"removed_empty_rows": int(empty_rows.sum()),
		"removed_exact_duplicates": int(duplicate_rows.sum()),
		"removed_invalid_or_missing_targets": int(invalid_target.sum()),
		"removed_rows_missing_features": int(missing_features.sum()),
		"target_column": target_column,
		"target_unit": normalize_unit_name(target_unit),
		"target_source_unit": normalize_unit_name(target_source_unit),
		"feature_columns": selected_features,
		"group_column": group_column,
		"final_rows": len(working),
		"imputation": "none; rows with required missing values were excluded",
	}
	return CleaningResult(working.reset_index(drop=True), report)
