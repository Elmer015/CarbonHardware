"""Embodied-carbon accounting with explicit provenance and value type."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
	from ..models.predict import load_model, predict_frame
except ImportError:
	from predict import load_model, predict_frame


class EmbodiedCarbonValidationError(ValueError):
	"""Raised for invalid values or ambiguous carbon provenance."""


@dataclass(frozen=True)
class EmbodiedCarbonResult:
	value: float
	unit: str
	value_kind: str
	source: str
	functional_unit: str
	boundary: str
	metadata: dict[str, Any]


def _validate_nonnegative(value: float, name: str) -> float:
	numeric = float(value)
	if not np.isfinite(numeric) or numeric < 0:
		raise EmbodiedCarbonValidationError(f"{name} must be finite and non-negative")
	return numeric


def reported_lca_value(
	value: float,
	*,
	unit: str,
	source: str,
	functional_unit: str,
	boundary: str,
) -> EmbodiedCarbonResult:
	"""Record a reported/measured LCA value without relabeling it as a prediction."""
	if not all((unit, source, functional_unit, boundary)):
		raise EmbodiedCarbonValidationError("unit, source, functional_unit, and boundary are required")
	return EmbodiedCarbonResult(
		value=_validate_nonnegative(value, "value"),
		unit=unit,
		value_kind="reported_or_measured_lca",
		source=source,
		functional_unit=functional_unit,
		boundary=boundary,
		metadata={},
	)


def predict_embodied_carbon(
	model_path: Path,
	features: pd.DataFrame,
	*,
	source: str = "Phase 4 validated model",
	functional_unit: str = "one processor over modeled lifecycle",
	boundary: str = "CarbonSet/ECO-CHIP modeled design, manufacturing, packaging, use, and end of life",
) -> list[EmbodiedCarbonResult]:
	"""Return model predictions explicitly labeled as estimates, never LCA measurements."""
	artifact = load_model(model_path)
	predictions = predict_frame(artifact, features)
	target = artifact.get("target", {})
	unit = target.get("unit")
	if not unit:
		raise EmbodiedCarbonValidationError("The model artifact has no target unit")
	results = []
	for prediction in predictions:
		results.append(
			EmbodiedCarbonResult(
				value=_validate_nonnegative(prediction, "predicted embodied carbon"),
				unit=unit,
				value_kind="model_prediction",
				source=source,
				functional_unit=functional_unit,
				boundary=boundary,
				metadata={
					"dataset_version": artifact.get("dataset_version"),
					"model_type": artifact.get("metadata", {}).get("model_type"),
				},
			)
		)
	return results
