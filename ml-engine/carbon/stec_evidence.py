"""Resolve STEC inputs for a processor from sourced evidence files.

Evidence lives in ``data/stec`` and ``data/raw/grid``:

    fab-provenance.csv      product-level fab region (sourced)       -> point result
    fab-rules.csv           vendor/type/node candidate regions       -> point or range (assumption)
    chiplets.csv            per-die role, area, node, region         -> multi-die STEC
    manufacturing-years.csv sourced manufacturing year               -> else release-year proxy
    yields.csv              sourced yield per node/foundry/year      -> else no yield correction
    market-factors.csv      sourced PPA/REC factor per foundry/year  -> else market-based unavailable
    owid-carbon-intensity-electricity.csv  country-year CI (g CO2e/kWh)

Every result states which evidence level produced it, so assumptions are never
reported as sourced values.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from stec import (
    STECDieComponent,
    STECIncompleteError,
    calculate_market_based_stec,
    calculate_multi_die_stec,
    calculate_stec,
)

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "data" / "stec"
GRID_PATH = ROOT / "data" / "raw" / "grid" / "owid-carbon-intensity-electricity.csv"
GRID_SOURCE = "Our World in Data, Carbon intensity of electricity (Ember-based, g CO2e/kWh)"
GLOBAL_REGION = "World"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.DictReader(handle) if any((value or "").strip() for value in row.values())]


def _node_key(value: Any) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


@dataclass(frozen=True)
class Evidence:
    grid: dict[tuple[str, int], float]
    fab_rules: list[dict[str, str]]
    provenance: dict[str, dict[str, str]]
    chiplets: dict[str, list[dict[str, str]]]
    manufacturing_years: dict[str, dict[str, str]]
    yields: dict[tuple[str, str, int], dict[str, str]]
    market_factors: dict[tuple[str, int], dict[str, str]]
    paths: dict[str, str] = field(default_factory=dict)


@lru_cache(maxsize=1)
def load_evidence(evidence_dir: str = str(EVIDENCE_DIR), grid_path: str = str(GRID_PATH)) -> Evidence:
    directory = Path(evidence_dir)
    grid: dict[tuple[str, int], float] = {}
    for row in _read_csv(Path(grid_path)):
        value_key = next(key for key in row if key.startswith("co2_intensity"))
        grid[(row["entity"], int(row["year"]))] = float(row[value_key])
    if not grid:
        raise STECIncompleteError(f"Grid carbon-intensity file is missing or empty: {grid_path}")
    chiplets: dict[str, list[dict[str, str]]] = {}
    for row in _read_csv(directory / "chiplets.csv"):
        chiplets.setdefault(row["product"], []).append(row)
    return Evidence(
        grid=grid,
        fab_rules=_read_csv(directory / "fab-rules.csv"),
        provenance={row["product"]: row for row in _read_csv(directory / "fab-provenance.csv")},
        chiplets=chiplets,
        manufacturing_years={row["product"]: row for row in _read_csv(directory / "manufacturing-years.csv")},
        yields={
            (_node_key(row["process_node_nm"]), row["foundry"], int(row["year"])): row
            for row in _read_csv(directory / "yields.csv")
        },
        market_factors={(row["foundry"], int(row["year"])): row for row in _read_csv(directory / "market-factors.csv")},
        paths={"evidence_dir": str(directory), "grid": str(grid_path)},
    )


def grid_intensity(evidence: Evidence, region: str, year: int) -> float:
    try:
        return evidence.grid[(region, int(year))]
    except KeyError as exc:
        raise STECIncompleteError(f"No country-year carbon intensity for {region} in {year}") from exc


def available_regions(evidence: Evidence | None = None) -> dict[str, Any]:
    evidence = evidence or load_evidence()
    years: dict[str, list[int]] = {}
    for region, year in evidence.grid:
        years.setdefault(region, []).append(year)
    return {
        "source": GRID_SOURCE,
        "regions": [
            {"region": region, "firstYear": min(values), "lastYear": max(values)}
            for region, values in sorted(years.items())
        ],
    }


def _rule_for(evidence: Evidence, vendor: str, kind: str, node: str) -> dict[str, str] | None:
    for rule in evidence.fab_rules:
        if rule["vendor"] == vendor and rule["type"] == kind and rule["node_nm"] in (node, "*"):
            return rule
    return None


def _manufacturing_year(evidence: Evidence, product: str, release_year: int | None, override: int | None) -> tuple[int, str, str]:
    if override is not None:
        return int(override), "user_input", "value supplied by the user"
    sourced = evidence.manufacturing_years.get(product)
    if sourced and sourced.get("manufacturing_year"):
        return int(sourced["manufacturing_year"]), "sourced", sourced.get("source", "")
    if release_year is None:
        raise STECIncompleteError("manufacturing year is unknown and no release year is available")
    return int(release_year), "release_year_proxy", "CarbonSet release date used as a proxy for manufacturing year"


def _yield(evidence: Evidence, node: str, foundry: str | None, year: int) -> tuple[float | None, dict[str, Any]]:
    row = evidence.yields.get((node, foundry or "", year)) if foundry else None
    if not row:
        return None, {"applied": False, "reason": "no sourced yield for this node/foundry/year"}
    return float(row["yield_factor"]), {"applied": True, "yieldFactor": float(row["yield_factor"]), "source": row.get("source", "")}


def _market_based(evidence: Evidence, *, foundry: str | None, year: int, die_area_mm2: float, node: str, region: str, yield_factor: float | None) -> dict[str, Any]:
    row = evidence.market_factors.get((foundry or "", year)) if foundry else None
    if not row:
        return {
            "status": "not_available",
            "reason": f"no sourced market-based factor for foundry '{foundry or 'unknown'}' in {year}",
        }
    result = calculate_market_based_stec(
        die_area_mm2=die_area_mm2,
        node_nm=node,
        market_based_factor_g_co2e_per_kwh=float(row["market_based_factor_g_co2e_per_kwh"]),
        contract_type=row["contract_type"],
        factor_source=row["source"],
        foundry=foundry,
        manufacturing_region=region,
        manufacturing_year=year,
        yield_factor=yield_factor,
    )
    return {
        "status": "computed",
        "stecKgCo2e": result.stec_kg_co2e,
        "factorGCo2ePerKwh": result.ci_g_co2e_per_kwh,
        "contractType": row["contract_type"],
        "source": row["source"],
    }


def _region_result(evidence: Evidence, *, region: str, year: int, die_area_mm2: float, node: str, foundry: str | None) -> dict[str, Any]:
    yield_factor, yield_info = _yield(evidence, node, foundry, year)
    try:
        ci = grid_intensity(evidence, region, year)
    except STECIncompleteError as error:
        return {"region": region, "status": "incomplete", "reason": str(error)}
    result = calculate_stec(
        die_area_mm2=die_area_mm2,
        node_nm=node,
        grid_intensity_g_co2e_per_kwh=ci,
        manufacturing_region=region,
        manufacturing_year=year,
        yield_factor=yield_factor,
        source=GRID_SOURCE,
    )
    return {
        "region": region,
        "status": "complete",
        "foundry": foundry,
        "ciGCo2ePerKwh": ci,
        "intensityGPerCm2": result.intensity_g_per_cm2,
        "stecKgCo2e": result.stec_kg_co2e,
        "yield": yield_info,
        "explicitProxyNode": result.assumptions.get("explicit_proxy_node"),
        "marketBased": _market_based(evidence, foundry=foundry, year=year, die_area_mm2=die_area_mm2, node=node, region=region, yield_factor=yield_factor),
    }


def _chiplet_result(evidence: Evidence, product: str, rows: list[dict[str, str]], year: int) -> dict[str, Any]:
    components = []
    details = []
    for row in rows:
        count = int(row.get("die_count") or 1)
        area = float(row["die_area_mm2"])
        node = _node_key(row["node_nm"])
        yield_factor, yield_info = _yield(evidence, node, row.get("foundry"), year)
        ci = grid_intensity(evidence, row["manufacturing_region"], year)
        for index in range(count):
            components.append(STECDieComponent(
                role=f"{row['die_role']}#{index + 1}" if count > 1 else row["die_role"],
                die_area_mm2=area,
                node_nm=node,
                manufacturing_region=row["manufacturing_region"],
                manufacturing_year=year,
                grid_intensity_g_co2e_per_kwh=ci,
                yield_factor=yield_factor,
                source=row.get("source", ""),
            ))
        details.append({
            "dieRole": row["die_role"], "dieCount": count, "dieAreaMm2": area, "nodeNm": node,
            "region": row["manufacturing_region"], "foundry": row.get("foundry"), "ciGCo2ePerKwh": ci,
            "confidence": row.get("confidence"), "source": row.get("source"), "yield": yield_info,
        })
    total = calculate_multi_die_stec(components)
    per_role: dict[str, float] = {}
    for role, result in total.components:
        key = role.split("#")[0]
        per_role[key] = per_role.get(key, 0.0) + result.stec_kg_co2e
    for detail in details:
        detail["stecKgCo2e"] = per_role[detail["dieRole"]]
    return {
        "applied": True,
        "stecKgCo2e": total.stec_kg_co2e,
        "totalDieAreaMm2": sum(d["dieAreaMm2"] * d["dieCount"] for d in details),
        "components": details,
    }


def resolve_processor_stec(
    processor: dict[str, Any],
    *,
    manufacturing_region: str | None = None,
    manufacturing_year: int | None = None,
    evidence: Evidence | None = None,
) -> dict[str, Any]:
    """Resolve STEC for one processor, labeling every evidence level used."""
    evidence = evidence or load_evidence()
    product = processor["name"]
    vendor = processor.get("vendor") or ""
    kind = processor.get("type") or ""
    node = _node_key(processor["processSizeNm"])
    die_area = float(processor["dieAreaMm2"])
    release_year = processor.get("releaseYear")
    year, year_status, year_source = _manufacturing_year(evidence, product, release_year, manufacturing_year)
    warnings: list[str] = []
    if year_status == "release_year_proxy":
        warnings.append("Manufacturing year is the release year (proxy).")

    if manufacturing_region:
        location_level, candidates, foundry, confidence, basis = "user_input", [manufacturing_region], None, "user", "region supplied by the user"
    elif product in evidence.provenance:
        row = evidence.provenance[product]
        location_level, candidates, foundry, confidence, basis = "product_sourced", [row["manufacturing_region"]], row.get("foundry"), row.get("confidence"), row.get("source")
    else:
        rule = _rule_for(evidence, vendor, kind, node)
        if rule:
            regions = [value.strip() for value in rule["candidate_regions"].split(";") if value.strip()]
            foundries = [value.strip() for value in rule["foundry"].split(";") if value.strip()]
            location_level, candidates, confidence, basis = "vendor_node_assumption", regions, rule.get("confidence"), rule.get("basis")
            foundry = foundries[0] if len(foundries) == 1 else None
            warnings.append("Fab region is a vendor/node assumption, not product-level evidence.")
        else:
            location_level, candidates, foundry, confidence, basis = "unresolved", [], None, None, "no fab evidence or rule"

    regions = [_region_result(evidence, region=region, year=year, die_area_mm2=die_area, node=node, foundry=foundry) for region in candidates]
    complete = [item for item in regions if item["status"] == "complete"]
    values = [item["stecKgCo2e"] for item in complete]
    if len(candidates) == 1 and complete:
        status = "point"
    elif complete:
        status = "range"
        warnings.append("Several candidate fab regions: result is a range, not a point estimate.")
    else:
        status = "incomplete"
        warnings.append("No location-based STEC could be computed; supply a manufacturing region.")

    chiplet = {"applied": False}
    if product in evidence.chiplets and not manufacturing_region:
        try:
            chiplet = _chiplet_result(evidence, product, evidence.chiplets[product], year)
            warnings.append("Chiplet dies modeled separately; CarbonSet die area is not used for the total.")
        except STECIncompleteError as error:
            chiplet = {"applied": False, "reason": str(error)}

    try:
        global_ci = grid_intensity(evidence, GLOBAL_REGION, year)
        baseline = calculate_stec(die_area_mm2=die_area, node_nm=node, grid_intensity_g_co2e_per_kwh=global_ci, manufacturing_region=GLOBAL_REGION, manufacturing_year=year, source=GRID_SOURCE).stec_kg_co2e
    except STECIncompleteError:
        global_ci, baseline = None, None

    headline = chiplet["stecKgCo2e"] if chiplet.get("applied") else (values[0] if status == "point" else None)
    location = {"level": location_level, "confidence": confidence, "basis": basis, "candidates": candidates}
    if chiplet.get("applied"):
        location = {
            "level": "chiplet_sourced",
            "confidence": ";".join(sorted({c["confidence"] or "" for c in chiplet["components"]})),
            "basis": "per-die regions from chiplets.csv; 'regions' below use the CarbonSet die area for comparison only",
            "candidates": sorted({c["region"] for c in chiplet["components"]}),
        }
    return {
        "product": product,
        "type": kind,
        "vendor": vendor,
        "nodeNm": node,
        "dieAreaMm2": die_area,
        "attribution": "location-based",
        "valueKind": "estimated_location_based_die_stec",
        "boundary": "cradle-to-gate die manufacturing",
        "functionalUnit": "one chip (dies only)",
        "status": "point" if chiplet.get("applied") else status,
        "stecKgCo2e": headline,
        "stecMinKgCo2e": min(values) if values else None,
        "stecMaxKgCo2e": max(values) if values else None,
        "manufacturingYear": year,
        "manufacturingYearStatus": year_status,
        "manufacturingYearSource": year_source,
        "location": location,
        "regions": regions,
        "chiplet": chiplet,
        "globalBaseline": {"region": GLOBAL_REGION, "ciGCo2ePerKwh": global_ci, "stecKgCo2e": baseline},
        "gridSource": GRID_SOURCE,
        "warnings": warnings,
    }


def estimate_processor_stec(payload: dict[str, Any]) -> dict[str, Any]:
    """Entry point for the backend: payload carries processor fields and optional overrides."""
    region = payload.get("manufacturingRegion") or None
    year = payload.get("manufacturingYear")
    return resolve_processor_stec(
        payload["processor"],
        manufacturing_region=region,
        manufacturing_year=int(year) if year not in (None, "") else None,
    )
