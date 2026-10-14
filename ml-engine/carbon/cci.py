"""Compute Carbon Intensity (CCI) for equivalent completed workloads."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class CCIValidationError(ValueError):
	"""Raised for invalid CCI inputs or incomplete accounting metadata."""


@dataclass(frozen=True)
class CCIResult:
	cci_kg_co2e_per_workload: float
	total_carbon_kg_co2e: float
	completed_compute_work: float
	workload_unit: str
	lifecycle_boundary: str
	analysis_period: str


def compute_cci(
	total_carbon_kg_co2e: float,
	completed_compute_work: float,
	*,
	workload_unit: str,
	lifecycle_boundary: str,
	analysis_period: str,
) -> CCIResult:
	"""Compute CCI = total carbon / completed equivalent compute work."""
	carbon = float(total_carbon_kg_co2e)
	work = float(completed_compute_work)
	if not np.isfinite(carbon) or carbon < 0:
		raise CCIValidationError("total carbon must be finite and non-negative")
	if not np.isfinite(work) or work <= 0:
		raise CCIValidationError("completed compute work must be finite and greater than zero")
	if not all((workload_unit, lifecycle_boundary, analysis_period)):
		raise CCIValidationError("workload unit, lifecycle boundary, and analysis period are required")
	return CCIResult(
		cci_kg_co2e_per_workload=carbon / work,
		total_carbon_kg_co2e=carbon,
		completed_compute_work=work,
		workload_unit=workload_unit,
		lifecycle_boundary=lifecycle_boundary,
		analysis_period=analysis_period,
	)
