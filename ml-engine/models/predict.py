"""Load an experimental embodied-carbon model and make validated predictions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


class ModelArtifactError(ValueError):
	"""Raised when a saved model artifact is incomplete or incompatible."""


def load_model(model_path: Path) -> dict[str, Any]:
	artifact = joblib.load(model_path)
	if not isinstance(artifact, dict) or "model" not in artifact or "feature_columns" not in artifact:
		raise ModelArtifactError("Model artifact must contain model and feature_columns")
	if not artifact.get("target", {}).get("unit"):
		raise ModelArtifactError("Model artifact is missing the target unit")
	return artifact


def predict_frame(artifact: dict[str, Any], frame: pd.DataFrame) -> np.ndarray:
	feature_columns = artifact["feature_columns"]
	missing = sorted(set(feature_columns) - set(frame.columns))
	if missing:
		raise ModelArtifactError(f"Prediction input is missing features: {missing}")
	features = frame[feature_columns]
	if not all(pd.api.types.is_numeric_dtype(features[column]) for column in feature_columns):
		raise ModelArtifactError("Prediction features must be numeric")
	if features.isna().any().any():
		raise ModelArtifactError("Prediction features contain missing values")
	return np.asarray(artifact["model"].predict(features), dtype=float)


def predict_csv(model_path: Path, input_path: Path, output_path: Path) -> None:
	artifact = load_model(model_path)
	frame = pd.read_csv(input_path)
	predictions = predict_frame(artifact, frame)
	output = frame.copy()
	output["predicted_embodied_carbon"] = predictions
	output_path.parent.mkdir(parents=True, exist_ok=True)
	output.to_csv(output_path, index=False)
