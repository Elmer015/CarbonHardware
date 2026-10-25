"""Location-based STEC calculation for CPU/GPU die manufacturing.

The implementation follows the workbook's Eq. (1)/(7):

    intensity_g_per_cm2 = GPS + MPS + CI * EPS
    stec_kg = intensity_g_per_cm2 * die_area_cm2 / 1000

The result is cradle-to-gate die embodied carbon. Packaging, board, use, and
end-of-life are outside this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


class STECIncompleteError(RuntimeError):
    """Raised when the evidence required for a requested STEC result is absent."""


class STECValidationError(ValueError):
    """Raised when a STEC input has an invalid unit, value, or attribution."""


@dataclass(frozen=True)
class STECNodeParameters:
    node_nm: str
    eps_kwh_per_cm2: float
    gps_g_per_cm2: float
    mps_g_per_cm2: float
    source: str
    proxy_for_node_nm: str | None = None


@dataclass(frozen=True)
class STECResult:
    stec_kg_co2e: float
    die_area_cm2: float
    intensity_g_per_cm2: float
    node_nm: str
    ci_g_co2e_per_kwh: float
    manufacturing_region: str
    manufacturing_year: int
    yield_factor: float | None
    assumptions: dict[str, Any]
    attribution: str = "location-based"


@dataclass(frozen=True)
class STECDieComponent:
    role: str
    die_area_mm2: float
    node_nm: int | float | str
    manufacturing_region: str
    manufacturing_year: int
    grid_intensity_g_co2e_per_kwh: float
    yield_factor: float | None = None
    source: str = ""


@dataclass(frozen=True)
class MultiDieSTECResult:
    stec_kg_co2e: float
    components: tuple[tuple[str, STECResult], ...]
    attribution: str
    assumptions: dict[str, Any]


@dataclass(frozen=True)
class STECStatus:
    status: str
    missing_evidence: tuple[str, ...]
    notes: str


NODE_PARAMETERS: dict[str, STECNodeParameters] = {
    "28": STECNodeParameters("28", 0.9, 100, 500, "Zhang et al. Table 7"),
    "20": STECNodeParameters("20", 1.2, 110, 500, "Zhang et al. Table 7"),
    "14": STECNodeParameters("14", 1.2, 125, 500, "Zhang et al. Table 7"),
    "10": STECNodeParameters("10", 1.475, 150, 500, "Zhang et al. Table 7"),
    "7": STECNodeParameters("7", 1.52, 200, 500, "Zhang et al. Table 7"),
    "7-EUV": STECNodeParameters("7-EUV", 2.15, 200, 500, "Zhang et al. Table 7"),
    "7-EUV-DP": STECNodeParameters("7-EUV-DP", 2.15, 200, 500, "Zhang et al. Table 7"),
    "5": STECNodeParameters("5", 2.75, 225, 500, "Zhang et al. Table 7"),
    "3": STECNodeParameters("3", 2.75, 275, 500, "Zhang et al. Table 7"),
    "22": STECNodeParameters("20", 1.2, 110, 500, "Explicit 20 nm proxy", "22"),
    "12": STECNodeParameters("14", 1.2, 125, 500, "Explicit 14 nm proxy (GlobalFoundries 12LP is a 14LPP derivative)", "12"),
}


def _finite_nonnegative(value: float, name: str) -> float:
    numeric = float(value)
    if numeric != numeric or numeric in (float("inf"), float("-inf")) or numeric < 0:
        raise STECValidationError(f"{name} must be finite and non-negative")
    return numeric


def node_parameters(node_nm: int | float | str) -> STECNodeParameters:
    key = str(node_nm).strip()
    if key.endswith(".0"):
        key = key[:-2]
    try:
        return NODE_PARAMETERS[key]
    except KeyError as exc:
        raise STECIncompleteError(
            f"No validated STEC parameters are available for node {node_nm} nm"
        ) from exc


def calculate_stec(
    *,
    die_area_mm2: float,
    node_nm: int | float | str,
    grid_intensity_g_co2e_per_kwh: float,
    manufacturing_region: str,
    manufacturing_year: int,
    yield_factor: float | None = None,
    source: str = "CarbonHardware STEC dataset",
    assumptions: dict[str, Any] | None = None,
) -> STECResult:
    """Calculate location-based STEC for one chip.

    ``grid_intensity_g_co2e_per_kwh`` must be a country-year value, such as the
    workbook's OWID/Ember table. Market-based factors are intentionally not
    accepted by this function; they require a separate sourced contract.
    """
    if not manufacturing_region:
        raise STECValidationError("manufacturing_region is required")
    if int(manufacturing_year) != manufacturing_year or manufacturing_year < 1:
        raise STECValidationError("manufacturing_year must be a positive integer")
    area_mm2 = _finite_nonnegative(die_area_mm2, "die_area_mm2")
    ci = _finite_nonnegative(grid_intensity_g_co2e_per_kwh, "grid intensity")
    parameters = node_parameters(node_nm)
    if yield_factor is not None and not 0 < float(yield_factor) <= 1:
        raise STECValidationError("yield_factor must be greater than 0 and at most 1")
    area_cm2 = area_mm2 / 100
    intensity = parameters.gps_g_per_cm2 + parameters.mps_g_per_cm2 + ci * parameters.eps_kwh_per_cm2
    correction = 1 / float(yield_factor) if yield_factor is not None else 1
    result = intensity * area_cm2 * correction / 1000
    recorded_assumptions = dict(assumptions or {})
    recorded_assumptions.update(
        {
            "boundary": "cradle-to-gate die manufacturing",
            "functional_unit": "one chip",
            "equation": "GPS + MPS + CI * EPS, multiplied by die area",
            "grid_intensity_unit": "g CO2e/kWh",
            "parameter_source": parameters.source,
            "input_source": source,
        }
    )
    if parameters.proxy_for_node_nm:
        recorded_assumptions["explicit_proxy_node"] = parameters.proxy_for_node_nm
    return STECResult(
        stec_kg_co2e=result,
        die_area_cm2=area_cm2,
        intensity_g_per_cm2=intensity,
        node_nm=str(node_nm),
        ci_g_co2e_per_kwh=ci,
        manufacturing_region=manufacturing_region,
        manufacturing_year=int(manufacturing_year),
        yield_factor=yield_factor,
        assumptions=recorded_assumptions,
    )


def calculate_market_based_stec(
    *,
    die_area_mm2: float,
    node_nm: int | float | str,
    market_based_factor_g_co2e_per_kwh: float,
    contract_type: str,
    factor_source: str,
    foundry: str,
    manufacturing_region: str,
    manufacturing_year: int,
    yield_factor: float | None = None,
    assumptions: dict[str, Any] | None = None,
) -> STECResult:
    """Calculate market-based STEC from a sourced supplier/contract factor.

    Market-based and location-based results are reported side by side and are
    never summed. The factor must come from a contractual instrument disclosure
    (for example PPA or REC volumes in a foundry sustainability report).
    """
    if not contract_type or not factor_source or not foundry:
        raise STECIncompleteError("market-based STEC requires contract_type, factor_source, and foundry")
    recorded = dict(assumptions or {})
    recorded.update({"attribution": "market-based", "contract_type": contract_type, "foundry": foundry})
    result = calculate_stec(
        die_area_mm2=die_area_mm2,
        node_nm=node_nm,
        grid_intensity_g_co2e_per_kwh=market_based_factor_g_co2e_per_kwh,
        manufacturing_region=manufacturing_region,
        manufacturing_year=manufacturing_year,
        yield_factor=yield_factor,
        source=factor_source,
        assumptions=recorded,
    )
    return replace(result, attribution="market-based")


def calculate_multi_die_stec(
    components: list[STECDieComponent],
    *,
    attribution: str = "location-based",
) -> MultiDieSTECResult:
    """Sum die-level STEC for chiplet products whose dies differ in node or fab.

    Each die keeps its own node, manufacturing region, year, and carbon intensity.
    """
    if not components:
        raise STECIncompleteError("at least one die component is required")
    if attribution not in ("location-based", "market-based"):
        raise STECValidationError("attribution must be location-based or market-based")
    results = []
    for component in components:
        if not component.role:
            raise STECValidationError("each die component needs a role, for example CCD or IOD")
        result = calculate_stec(
            die_area_mm2=component.die_area_mm2,
            node_nm=component.node_nm,
            grid_intensity_g_co2e_per_kwh=component.grid_intensity_g_co2e_per_kwh,
            manufacturing_region=component.manufacturing_region,
            manufacturing_year=component.manufacturing_year,
            yield_factor=component.yield_factor,
            source=component.source or "CarbonHardware chiplet dataset",
            assumptions={"die_role": component.role},
        )
        results.append((component.role, replace(result, attribution=attribution)))
    return MultiDieSTECResult(
        stec_kg_co2e=sum(result.stec_kg_co2e for _, result in results),
        components=tuple(results),
        attribution=attribution,
        assumptions={
            "boundary": "cradle-to-gate die manufacturing, summed over all dies",
            "functional_unit": "one chip package (dies only)",
            "aggregation": "sum of per-die GPS + MPS + CI * EPS over each die area",
        },
    )


def stec_status() -> STECStatus:
    return STECStatus(
        status="implemented_location_market_multidie",
        missing_evidence=(
            "product-level fab provenance for unresolved vendors/products",
            "validated manufacturing year when release year is used as proxy",
            "sourced yield data when yield correction is required",
            "sourced market-based PPA/REC factors per foundry and year",
        ),
        notes="Location-based, market-based (sourced factor only), and multi-die STEC are implemented; unresolved evidence remains explicit.",
    )
