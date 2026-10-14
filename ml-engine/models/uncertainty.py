"""Evidence-bounded uncertainty summaries for carbon accounting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


class UncertaintyValidationError(ValueError):
	"""Raised when an uncertainty input cannot be summarized safely."""


@dataclass(frozen=True)
class UncertaintySummary:
	central_value: float
	lower_value: float
	upper_value: float
	unit: str
	source: str
	uncertainty_kind: str
	method: str
	sample_count: int | None


def summarize_interval(
	lower_value: float,
	central_value: float,
	upper_value: float,
	*,
	unit: str,
	source: str,
	uncertainty_kind: str,
	method: str,
) -> UncertaintySummary:
	lower = float(lower_value)
	central = float(central_value)
	upper = float(upper_value)
	if not all(np.isfinite(value) for value in (lower, central, upper)):
		raise UncertaintyValidationError("interval values must be finite")
	if lower < 0 or lower > central or central > upper:
		raise UncertaintyValidationError("values must satisfy 0 <= lower <= central <= upper")
	if not all((unit, source, uncertainty_kind, method)):
		raise UncertaintyValidationError("unit, source, uncertainty_kind, and method are required")
	return UncertaintySummary(central, lower, upper, unit, source, uncertainty_kind, method, None)


def summarize_samples(
	samples: Iterable[float],
	*,
	unit: str,
	source: str,
	uncertainty_kind: str = "propagated_model_input",
	confidence_level: float = 0.95,
) -> UncertaintySummary:
	"""Summarize supplied samples; does not claim calibration or coverage."""
	values = np.asarray(list(samples), dtype=float)
	if values.size < 2 or not np.isfinite(values).all() or (values < 0).any():
		raise UncertaintyValidationError("at least two finite, non-negative samples are required")
	if not 0 < confidence_level < 1:
		raise UncertaintyValidationError("confidence_level must be between 0 and 1")
	tail = (1 - confidence_level) / 2
	return UncertaintySummary(
		central_value=float(np.mean(values)),
		lower_value=float(np.quantile(values, tail)),
		upper_value=float(np.quantile(values, 1 - tail)),
		unit=unit,
		source=source,
		uncertainty_kind=uncertainty_kind,
		method=f"empirical quantiles at {confidence_level:.3f}; not calibrated coverage",
		sample_count=int(values.size),
	)
