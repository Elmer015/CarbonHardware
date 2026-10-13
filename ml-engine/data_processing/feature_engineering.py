"""Leakage-aware feature selection and deterministic feature construction."""

from __future__ import annotations

from typing import Any

import pandas as pd


LEAKAGE_NAME_FRAGMENTS = ("target", "carbon", "ecfp", "ocfp", "label", "y_")


def select_hardware_features(
	frame: pd.DataFrame,
	*,
	target_column: str,
	group_column: str,
	feature_columns: list[str] | None = None,
) -> list[str]:
	"""Select explicitly requested numeric features or safe numeric candidates."""
	if feature_columns is None:
		candidates = frame.select_dtypes(include="number").columns.tolist()
	else:
		candidates = list(feature_columns)
	missing = sorted(set(candidates) - set(frame.columns))
	if missing:
		raise ValueError(f"Feature columns are missing: {missing}")
	selected = []
	for column in candidates:
		normalized = column.lower()
		if column in {target_column, group_column}:
			continue
		if any(fragment in normalized for fragment in LEAKAGE_NAME_FRAGMENTS):
			continue
		if not pd.api.types.is_numeric_dtype(frame[column]):
			raise TypeError(f"Feature column must be numeric: {column}")
		selected.append(column)
	if not selected:
		raise ValueError("No safe numeric hardware features remain after leakage checks")
	return selected


def build_feature_frame(
	frame: pd.DataFrame,
	*,
	target_column: str,
	group_column: str,
	feature_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
	selected = select_hardware_features(
		frame,
		target_column=target_column,
		group_column=group_column,
		feature_columns=feature_columns,
	)
	features = frame[selected].copy()
	if features.isna().any().any():
		raise ValueError("Feature frame contains missing values; clean rows before engineering")
	metadata = {
		"feature_columns": selected,
		"transformations": "numeric hardware columns retained without scaling or imputation",
	}
	return features, selected, metadata
