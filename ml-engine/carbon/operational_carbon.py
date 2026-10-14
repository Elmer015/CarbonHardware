"""Operational-carbon calculations with caller-supplied grid intensity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


class OperationalCarbonValidationError(ValueError):
	"""Raised when an operational-carbon input is missing or invalid."""


@dataclass(frozen=True)
class OperationalCarbonResult:
	electricity_kwh: float
	grid_intensity_kg_co2e_per_kwh: float
	carbon_kg_co2e: float
	grid_intensity_source: str
	analysis_period: str
	assumptions: dict[str, Any]


def _nonnegative(value: float, name: str) -> float:
	numeric = float(value)
	if not np.isfinite(numeric) or numeric < 0:
		raise OperationalCarbonValidationError(f"{name} must be finite and non-negative")
	return numeric


def calculate_operational_carbon(
	electricity_kwh: float,
	grid_intensity_kg_co2e_per_kwh: float,
	*,
	grid_intensity_source: str,
	analysis_period: str,
	assumptions: dict[str, Any] | None = None,
) -> OperationalCarbonResult:
	"""Calculate kg CO2e = kWh * kg CO2e/kWh; no grid value is assumed."""
	if not grid_intensity_source or not analysis_period:
		raise OperationalCarbonValidationError("grid intensity source and analysis period are required")
	electricity = _nonnegative(electricity_kwh, "electricity_kwh")
	intensity = _nonnegative(grid_intensity_kg_co2e_per_kwh, "grid intensity")
	return OperationalCarbonResult(
		electricity_kwh=electricity,
		grid_intensity_kg_co2e_per_kwh=intensity,
		carbon_kg_co2e=electricity * intensity,
		grid_intensity_source=grid_intensity_source,
		analysis_period=analysis_period,
		assumptions=assumptions or {},
	)


def calculate_from_power(
	power_w: float,
	runtime_hours: float,
	grid_intensity_kg_co2e_per_kwh: float,
	*,
	grid_intensity_source: str,
	analysis_period: str,
	utilization: float = 1.0,
	assumptions: dict[str, Any] | None = None,
) -> OperationalCarbonResult:
	"""Derive electricity from power and runtime with explicit utilization."""
	power = _nonnegative(power_w, "power_w")
	runtime = _nonnegative(runtime_hours, "runtime_hours")
	utilization_value = float(utilization)
	if not np.isfinite(utilization_value) or not 0 <= utilization_value <= 1:
		raise OperationalCarbonValidationError("utilization must be between 0 and 1")
	assumptions = dict(assumptions or {})
	assumptions["power_to_energy"] = "electricity_kwh = power_w / 1000 * runtime_hours * utilization"
	assumptions["utilization"] = utilization_value
	electricity = power / 1000 * runtime * utilization_value
	return calculate_operational_carbon(
		electricity,
		grid_intensity_kg_co2e_per_kwh,
		grid_intensity_source=grid_intensity_source,
		analysis_period=analysis_period,
		assumptions=assumptions,
	)
