"""Lifecycle carbon: embodied + operational carbon, final CCI, and Monte Carlo uncertainty.

    electricity_kwh   = tdp_w / 1000 * hours_per_day * days_per_year * usage_years * utilization
    operational_kg    = electricity_kwh * grid_intensity_kg_co2e_per_kwh
    total_kg          = embodied_kg + operational_kg
    cci_final         = total_kg / completed_compute_work

Grid intensity comes from data/grid/grid-intensity.csv (location-based) unless the
caller supplies a sourced value. Uncertainty is propagated by Monte Carlo sampling
of triangular distributions given as {"min", "mostLikely", "max"}; inputs without a
distribution are held at their point value, and the output lists which inputs varied.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from cci import compute_cci
from grid_intensity import GridIntensityUnavailableError, grid_intensity
from operational_carbon import calculate_from_tdp

ROOT = Path(__file__).resolve().parents[2]
PREDICTION_INTERVAL = ROOT / "ml-engine" / "artifacts" / "embodied_prediction_interval.json"
DISTRIBUTION_INPUTS = ("tdpW", "utilization", "hoursPerDay", "daysPerYear", "usageYears", "gridIntensityKgCo2ePerKwh")
DEFAULT_SAMPLES = 10_000
DEFAULT_SEED = 42


class LifecycleValidationError(ValueError):
	"""Raised when a lifecycle input or distribution is invalid."""


def _number(payload: dict[str, Any], key: str, *, low: float = 0.0, high: float | None = None) -> float:
	if payload.get(key) in (None, ""):
		raise LifecycleValidationError(f"{key} is required")
	value = float(payload[key])
	if not np.isfinite(value) or value < low or (high is not None and value > high):
		bound = f" and <= {high}" if high is not None else ""
		raise LifecycleValidationError(f"{key} must be finite, >= {low}{bound}")
	return value


def _distribution(spec: dict[str, Any], key: str, default_mode: float | None = None) -> tuple[float, float, float]:
	spec = dict(spec)
	if spec.get("mostLikely") in (None, "") and default_mode is not None:
		spec["mostLikely"] = default_mode
	try:
		low, mode, high = (float(spec[k]) for k in ("min", "mostLikely", "max"))
	except (KeyError, TypeError, ValueError) as exc:
		raise LifecycleValidationError(f"{key} distribution needs numeric min, mostLikely, max") from exc
	if not (np.isfinite([low, mode, high]).all() and 0 <= low <= mode <= high):
		raise LifecycleValidationError(f"{key} distribution must satisfy 0 <= min <= mostLikely <= max")
	if key == "utilization" and high > 1:
		raise LifecycleValidationError("utilization distribution must stay within [0, 1]")
	return low, mode, high


def embodied_interval(embodied: dict[str, Any]) -> dict[str, Any]:
	"""Return (lower, central, upper) for embodied carbon with its uncertainty source."""
	central = _number(embodied, "value")
	if embodied.get("lowerValue") not in (None, "") and embodied.get("upperValue") not in (None, ""):
		lower, upper = float(embodied["lowerValue"]), float(embodied["upperValue"])
		if not 0 <= lower <= central <= upper:
			raise LifecycleValidationError("embodied interval must satisfy 0 <= lower <= value <= upper")
		return {"lower": lower, "central": central, "upper": upper,
			"source": embodied.get("intervalSource") or "supplied interval", "kind": "source_range"}
	if embodied.get("valueKind") == "model_prediction" and PREDICTION_INTERVAL.exists():
		spec = json.loads(PREDICTION_INTERVAL.read_text(encoding="utf-8"))
		q = spec["pooled"]["0.90"]
		return {"lower": max(0.0, central * (1 + q["q_low"])), "central": central, "upper": central * (1 + q["q_high"]),
			"source": f"model 90% empirical interval ({spec['method']}); {spec['coverage_note']}", "kind": "model_prediction_interval"}
	return {"lower": central, "central": central, "upper": central, "source": "no embodied uncertainty available", "kind": "point_only"}


def _resolve_grid(usage: dict[str, Any]) -> dict[str, Any]:
	if usage.get("gridIntensityKgCo2ePerKwh") not in (None, ""):
		if not usage.get("gridIntensitySource"):
			raise LifecycleValidationError("a supplied gridIntensityKgCo2ePerKwh needs gridIntensitySource")
		return {"kgCo2ePerKwh": _number(usage, "gridIntensityKgCo2ePerKwh"), "gCo2ePerKwh": float(usage["gridIntensityKgCo2ePerKwh"]) * 1000,
			"region": usage.get("usageRegion"), "year": usage.get("gridYear"), "source": usage["gridIntensitySource"],
			"basis": usage.get("gridBasis", "location-based")}
	region = usage.get("usageRegion")
	year = usage.get("gridYear")
	if not region or year in (None, ""):
		raise GridIntensityUnavailableError("usageRegion and gridYear are required to compute operational carbon")
	grid = grid_intensity(region, int(year))
	return {"kgCo2ePerKwh": grid.kg_co2e_per_kwh, "gCo2ePerKwh": grid.g_co2e_per_kwh, "region": grid.region,
		"year": grid.year, "source": grid.source, "basis": grid.basis}


def _summary(samples: np.ndarray, unit: str) -> dict[str, Any]:
	return {
		"unit": unit,
		"mean": float(samples.mean()),
		"median": float(np.median(samples)),
		"p2_5": float(np.quantile(samples, 0.025)),
		"p97_5": float(np.quantile(samples, 0.975)),
		"p5": float(np.quantile(samples, 0.05)),
		"p95": float(np.quantile(samples, 0.95)),
	}


def estimate_lifecycle(payload: dict[str, Any]) -> dict[str, Any]:
	usage = dict(payload.get("usage") or {})
	workload = payload.get("workload") or {}
	distributions = payload.get("distributions") or {}
	unknown = sorted(set(distributions) - set(DISTRIBUTION_INPUTS))
	if unknown:
		raise LifecycleValidationError(f"unsupported distribution inputs: {unknown}")

	grid_spec = distributions.get("gridIntensityKgCo2ePerKwh")
	parsed = {key: _distribution(spec, key) for key, spec in distributions.items() if spec and key != "gridIntensityKgCo2ePerKwh"}
	# The deterministic result uses the most likely value of any supplied distribution.
	for key, (_, mode, _) in parsed.items():
		usage[key] = mode

	tdp = _number(usage, "tdpW")
	utilization = _number(usage, "utilization", high=1)
	hours = _number(usage, "hoursPerDay", high=24)
	days = _number(usage, "daysPerYear", high=366)
	years = _number(usage, "usageYears")
	embodied = embodied_interval(payload.get("embodied") or {})
	warnings: list[str] = []

	grid = None
	operational = None
	try:
		grid = _resolve_grid(usage)
		if grid_spec:
			# Without an explicit mostLikely, the sourced grid value is the mode of the range.
			parsed["gridIntensityKgCo2ePerKwh"] = _distribution(grid_spec, "gridIntensityKgCo2ePerKwh", default_mode=grid["kgCo2ePerKwh"])
			mode = parsed["gridIntensityKgCo2ePerKwh"][1]
			if mode != grid["kgCo2ePerKwh"]:
				grid = {**grid, "kgCo2ePerKwh": mode, "gCo2ePerKwh": mode * 1000,
					"note": "point value replaced by the supplied distribution's mostLikely"}
		per_year = calculate_from_tdp(tdp, utilization, hours, days, grid["kgCo2ePerKwh"],
			grid_intensity_source=grid["source"], analysis_period=f"{grid.get('year')} grid, {years:g} usage years",
			assumptions={"basis": grid["basis"], "region": grid.get("region")})
		operational = {"electricityKwh": per_year.electricity_kwh * years, "carbonKgCo2e": per_year.carbon_kg_co2e * years,
			"annualCarbonKgCo2e": per_year.carbon_kg_co2e, "assumptions": per_year.assumptions}
		if grid.get("year") is not None and years > 1:
			warnings.append(f"Grid intensity of {grid['year']} is held constant over {years:g} usage years.")
	except GridIntensityUnavailableError as error:
		warnings.append(f"Operational carbon not computed: {error}")

	electricity = tdp / 1000 * hours * days * years * utilization
	total = embodied["central"] + operational["carbonKgCo2e"] if operational else None
	cci = None
	if workload.get("completedComputeWork") not in (None, "") and workload.get("workloadUnit"):
		carbon_for_cci = total if total is not None else embodied["central"]
		boundary = "embodied + operational" if total is not None else "embodied only (operational carbon unavailable)"
		result = compute_cci(carbon_for_cci, float(workload["completedComputeWork"]), workload_unit=workload["workloadUnit"],
			lifecycle_boundary=boundary, analysis_period=f"{years:g} usage years")
		cci = {"cciKgCo2ePerWorkload": result.cci_kg_co2e_per_workload, "workloadUnit": result.workload_unit,
			"completedComputeWork": result.completed_compute_work, "lifecycleBoundary": boundary,
			"status": "final" if total is not None else "embodied_only"}

	uncertainty = None
	n = int(payload.get("samples") or DEFAULT_SAMPLES)
	if not 100 <= n <= 100_000:
		raise LifecycleValidationError("samples must be between 100 and 100000")
	rng = np.random.default_rng(int(payload.get("seed", DEFAULT_SEED)))

	def draw(key: str, point: float) -> np.ndarray:
		if key in parsed:
			low, mode, high = parsed[key]
			return np.full(n, mode) if low == high else rng.triangular(low, mode, high, n)
		return np.full(n, point)

	emb = embodied
	emb_samples = np.full(n, emb["central"]) if emb["lower"] == emb["upper"] else rng.triangular(emb["lower"], emb["central"], emb["upper"], n)
	energy_samples = draw("tdpW", tdp) / 1000 * draw("hoursPerDay", hours) * draw("daysPerYear", days) * draw("usageYears", years) * draw("utilization", utilization)
	varied = [key for key in DISTRIBUTION_INPUTS if key in parsed and parsed[key][0] != parsed[key][2]]
	if emb["kind"] != "point_only":
		varied.insert(0, f"embodied ({emb['kind']})")
	uncertainty = {
		"method": f"Monte Carlo, {n} samples, triangular distributions, seed {int(payload.get('seed', DEFAULT_SEED))}",
		"variedInputs": varied,
		"heldConstant": [key for key in DISTRIBUTION_INPUTS if key not in parsed or parsed[key][0] == parsed[key][2]],
		"coverageNote": "propagated input uncertainty; intervals are not calibrated coverage",
		"embodied": _summary(emb_samples, "kg_co2e"),
		"electricity": _summary(energy_samples, "kWh"),
	}
	if operational:
		grid_samples = draw("gridIntensityKgCo2ePerKwh", grid["kgCo2ePerKwh"])
		op_samples = energy_samples * grid_samples
		total_samples = emb_samples + op_samples
		uncertainty["operational"] = _summary(op_samples, "kg_co2e")
		uncertainty["total"] = _summary(total_samples, "kg_co2e")
		uncertainty["embodiedShare"] = _summary(emb_samples / total_samples, "fraction")
		if cci:
			uncertainty["cci"] = _summary(total_samples / cci["completedComputeWork"], f"kg_co2e per {cci['workloadUnit']}")
		# Spearman rank correlation of each varied input with total carbon.
		drivers = {"embodied": emb_samples, "electricity": energy_samples, "gridIntensity": grid_samples}
		ranks_total = total_samples.argsort().argsort()
		uncertainty["drivers"] = {
			name: float(np.corrcoef(values.argsort().argsort(), ranks_total)[0, 1])
			for name, values in drivers.items() if values.std() > 0
		}
	if not varied:
		warnings.append("No input distribution supplied: uncertainty bands collapse to the point estimate.")

	return {
		"valueKind": "lifecycle_carbon_estimate",
		"embodied": {"valueKgCo2e": embodied["central"], "lowerKgCo2e": embodied["lower"], "upperKgCo2e": embodied["upper"],
			"intervalSource": embodied["source"], "intervalKind": embodied["kind"]},
		"electricityKwh": electricity,
		"grid": grid,
		"operational": operational,
		"totalKgCo2e": total,
		"embodiedShare": embodied["central"] / total if total else None,
		"cci": cci,
		"uncertainty": uncertainty,
		"status": "complete" if operational and cci else ("operational_pending_grid" if not operational else "cci_pending_workload"),
		"warnings": warnings,
	}
