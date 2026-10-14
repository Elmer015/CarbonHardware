"""STEC research boundary.

The cited spatial-temporal embodied-carbon and dual-attribution equations are
not available in this repository. This module deliberately refuses to produce
a number until the equation, parameters, and source data are supplied.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class STECIncompleteError(RuntimeError):
	"""Raised because a defensible STEC calculation is not yet specified."""


@dataclass(frozen=True)
class STECStatus:
	status: str
	missing_evidence: tuple[str, ...]
	notes: str


def stec_status() -> STECStatus:
	return STECStatus(
		status="incomplete",
		missing_evidence=(
			"verified spatial-temporal embodied-carbon equation",
			"dual carbon attribution definitions and allocation rule",
			"required spatial and temporal input data",
			"validated correction factors and units",
		),
		notes="No STEC value is calculated until the cited methodology and parameters are supplied.",
	)


def calculate_stec(**_: Any) -> float:
	"""Fail closed rather than inventing STEC correction factors."""
	raise STECIncompleteError(stec_status().notes)
