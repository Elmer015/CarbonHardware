"""E-waste mass accounting kept separate from carbon accounting."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class EWasteValidationError(ValueError):
	"""Raised when an end-of-life mass scenario is invalid."""


@dataclass(frozen=True)
class EWasteResult:
	hardware_mass_kg: float
	reuse_mass_kg: float
	recycling_mass_kg: float
	disposal_mass_kg: float
	scenario_source: str
	assumptions: dict[str, str]

	@property
	def accounted_mass_kg(self) -> float:
		return self.reuse_mass_kg + self.recycling_mass_kg + self.disposal_mass_kg


def calculate_e_waste(
	hardware_mass_kg: float,
	*,
	reuse_fraction: float,
	recycling_fraction: float,
	disposal_fraction: float,
	scenario_source: str,
	assumptions: dict[str, str] | None = None,
) -> EWasteResult:
	"""Allocate hardware mass across reuse, recycling, and disposal routes."""
	mass = float(hardware_mass_kg)
	fractions = (float(reuse_fraction), float(recycling_fraction), float(disposal_fraction))
	if not np.isfinite(mass) or mass < 0:
		raise EWasteValidationError("hardware mass must be finite and non-negative")
	if any(not np.isfinite(value) or value < 0 or value > 1 for value in fractions):
		raise EWasteValidationError("end-of-life fractions must each be between 0 and 1")
	if not np.isclose(sum(fractions), 1.0, atol=1e-9):
		raise EWasteValidationError("end-of-life fractions must sum to 1")
	if not scenario_source:
		raise EWasteValidationError("scenario_source is required")
	return EWasteResult(
		hardware_mass_kg=mass,
		reuse_mass_kg=mass * fractions[0],
		recycling_mass_kg=mass * fractions[1],
		disposal_mass_kg=mass * fractions[2],
		scenario_source=scenario_source,
		assumptions=assumptions or {},
	)
