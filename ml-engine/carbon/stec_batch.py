"""Recompute location-based die STEC for the CarbonSet processor inventory."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from stec import STECIncompleteError, STECValidationError, calculate_stec, node_parameters


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CARBONSET = ROOT / "data" / "raw" / "carbonset" / "CarbonSet.csv"
DEFAULT_EVIDENCE = ROOT / "data" / "raw" / "stec" / "evidence"
DEFAULT_GRID = ROOT / "data" / "raw" / "environmental" / "owid-lifecycle-carbon-intensity.csv"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "stec-per-chip.csv"

OUTPUT_FIELDS = (
    "product",
    "type",
    "vendor",
    "node_nm",
    "carbonset_die_area_mm2",
    "manufacturing_year",
    "manufacturing_year_status",
    "location_level",
    "location_confidence",
    "candidate_regions",
    "status",
    "stec_kg_co2e",
    "stec_min_kg_co2e",
    "stec_max_kg_co2e",
    "chiplet_applied",
    "chiplet_die_area_mm2",
    "global_baseline_stec_kg_co2e",
    "yield_applied",
    "market_based_status",
    "carbonset_emb_mean_kg_co2e",
    "carbonset_emb_min_kg_co2e",
    "carbonset_emb_max_kg_co2e",
    "location_basis",
    "warnings",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _number(value: str | None, field: str, *, positive: bool = False) -> float:
    try:
        number = float(value) if value not in (None, "") else float("nan")
    except (TypeError, ValueError) as exc:
        raise STECValidationError(f"{field} must be numeric") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise STECValidationError(f"{field} must be finite")
    if number < 0 or (positive and number == 0):
        qualifier = "positive" if positive else "non-negative"
        raise STECValidationError(f"{field} must be {qualifier}")
    return number


def _normalized(value: str | None) -> str:
    return (value or "").strip().casefold()


def _normalized_node(value: str | None) -> str:
    node = (value or "").strip()
    return node[:-2] if node.endswith(".0") else node


def _year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", value)
    return int(match.group()) if match else None


def _optional_number(value: str | None) -> float | None:
    return None if value in (None, "") else _number(value, "CarbonSet carbon reference")


def _integer(value: str | None, field: str, *, positive: bool = False) -> int:
    numeric = _number(value, field, positive=positive)
    if not numeric.is_integer():
        raise STECValidationError(f"{field} must be an integer")
    return int(numeric)


def _index_evidence(evidence_dir: Path) -> tuple[dict[str, dict[str, str]], dict[tuple[str, str, str], dict[str, str]], dict[str, list[dict[str, str]]], dict[str, dict[str, str]]]:
    provenance = {}
    for row in _read_csv(evidence_dir / "fab-provenance.csv"):
        key = _normalized(row.get("product"))
        if not key or key in provenance:
            raise STECValidationError(f"Missing or duplicate product in fab-provenance.csv: {row.get('product')}")
        provenance[key] = row

    rules = {}
    for row in _read_csv(evidence_dir / "fab-rules.csv"):
        key = (_normalized(row.get("vendor")), _normalized(row.get("type")), _normalized_node(row.get("node_nm")).casefold())
        if not all(key) or key in rules:
            raise STECValidationError(f"Missing or duplicate vendor/type/node rule: {key}")
        rules[key] = row

    chiplets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _read_csv(evidence_dir / "chiplets.csv"):
        key = _normalized(row.get("product"))
        if not key:
            raise STECValidationError("Missing product in chiplets.csv")
        chiplets[key].append(row)

    years = {}
    for row in _read_csv(evidence_dir / "manufacturing-years.csv"):
        key = _normalized(row.get("product"))
        if not key or key in years:
            raise STECValidationError(f"Missing or duplicate product in manufacturing-years.csv: {row.get('product')}")
        years[key] = row
    return provenance, rules, dict(chiplets), years


def _grid_index(path: Path) -> dict[tuple[str, int], float]:
    rows = _read_csv(path)
    expected = ("Entity", "Code", "Year", "Carbon intensity")
    if not rows or not all(field in rows[0] for field in expected):
        raise STECValidationError(f"Grid dataset must contain columns: {', '.join(expected)}")
    result = {}
    for row in rows:
        region = row["Entity"].strip()
        year = _integer(row["Year"], "grid year", positive=True)
        intensity = _number(row["Carbon intensity"], "grid carbon intensity")
        key = (_normalized(region), year)
        if key in result:
            raise STECValidationError(f"Duplicate grid intensity row for {region}, {year}")
        result[key] = intensity
    return result


def _manufacturing_year(product: str, release_date: str, overrides: dict[str, dict[str, str]]) -> tuple[int | None, str]:
    override = overrides.get(_normalized(product))
    if override and override.get("manufacturing_year"):
        year = _integer(override["manufacturing_year"], "manufacturing year", positive=True)
        return year, f"source:{override.get('source') or 'manufacturing-years.csv'}"
    year = _year(release_date)
    return year, "release_year_proxy" if year else "missing"


def _resolve_location(
    product: str,
    vendor: str,
    device_type: str,
    node: str,
    provenance: dict[str, dict[str, str]],
    rules: dict[tuple[str, str, str], dict[str, str]],
) -> tuple[list[str], str, str, str, list[str]]:
    warnings = []
    specific = provenance.get(_normalized(product))
    if specific:
        evidence_node = specific.get("process_node_nm", "").strip()
        region = specific.get("manufacturing_region", "").strip()
        if not region or not evidence_node:
            raise STECValidationError(f"Incomplete product-specific fab evidence for {product}")
        if _normalized(specific.get("vendor")) != _normalized(vendor) or _normalized(specific.get("type")) != _normalized(device_type):
            raise STECValidationError(f"Fab evidence vendor/type mismatch for {product}")
        if _normalized_node(evidence_node) != _normalized_node(node):
            warnings.append(f"Product source node {evidence_node} differs from CarbonSet node {node}; source node used")
        return [region], "product_sourced", specific.get("confidence", "source-backed"), specific.get("source", ""), warnings

    rule = rules.get((_normalized(vendor), _normalized(device_type), _normalized_node(node).casefold()))
    location_level = "vendor_node_assumption"
    if rule is None:
        rule = rules.get((_normalized(vendor), _normalized(device_type), "*"))
        location_level = "vendor_type_assumption"
    if rule is None:
        return [], "unresolved", "unresolved", "", [f"No fab provenance or vendor/type/node rule for {vendor} {device_type} {node}nm"]
    regions = [part.strip() for part in rule["candidate_regions"].split(";") if part.strip()]
    if not regions:
        return [], "unresolved", rule.get("confidence", "unresolved"), rule.get("basis", ""), ["Fab rule has no candidate regions"]
    return regions, location_level, rule.get("confidence", "assumed"), rule.get("basis", ""), warnings


def _calculate_component(area_mm2: float, node: str, region: str, year: int, grid: dict[tuple[str, int], float], source: str, role: str | None = None) -> float:
    intensity = grid.get((_normalized(region), year))
    if intensity is None:
        raise STECIncompleteError(f"No grid CI for {region}, {year}")
    assumptions: dict[str, Any] = {}
    if role:
        assumptions["die_role"] = role
    result = calculate_stec(
        die_area_mm2=area_mm2,
        node_nm=node,
        grid_intensity_g_co2e_per_kwh=intensity,
        manufacturing_region=region,
        manufacturing_year=year,
        source=source,
        assumptions=assumptions,
    )
    return result.stec_kg_co2e


def build_stec_inventory(
    carbonset_path: Path = DEFAULT_CARBONSET,
    evidence_dir: Path = DEFAULT_EVIDENCE,
    grid_path: Path = DEFAULT_GRID,
) -> list[dict[str, Any]]:
    provenance, rules, chiplets, year_overrides = _index_evidence(evidence_dir)
    grid = _grid_index(grid_path)
    carbonset_rows = _read_csv(carbonset_path)
    required = ("Product", "Type", "Vendor", "Release Date", "Process Size (nm)", "DieSizeValue")
    if not carbonset_rows or not all(field in carbonset_rows[0] for field in required):
        raise STECValidationError(f"CarbonSet must contain columns: {', '.join(required)}")

    inventory = []
    seen_products = set()
    for source_row in carbonset_rows:
        product = source_row["Product"].strip()
        product_key = _normalized(product)
        if not product or product_key in seen_products:
            continue
        seen_products.add(product_key)

        device_type = source_row["Type"].strip()
        vendor = source_row["Vendor"].strip()
        node = source_row["Process Size (nm)"].strip()
        area = _number(source_row["DieSizeValue"], f"{product} die area", positive=True)
        year, year_status = _manufacturing_year(product, source_row.get("Release Date", ""), year_overrides)
        product_chiplets = chiplets.get(product_key, [])
        warnings: list[str] = []
        candidate_regions: list[str] = []
        location_level = "unresolved"
        location_confidence = "unresolved"
        location_basis = ""
        component_area: float | None = None

        if not year:
            warnings.append("No manufacturing year or release-year proxy")
        try:
            parameters = node_parameters(node)
            if parameters.proxy_for_node_nm:
                warnings.append(f"Explicit node proxy: {node} uses {parameters.node_nm} nm parameters")
        except STECIncompleteError:
            pass
        try:
            if product_chiplets:
                component_area = 0.0
                component_values = []
                component_regions = []
                component_confidence = []
                component_sources = []
                for chiplet in product_chiplets:
                    count = _integer(chiplet.get("die_count"), f"{product} die_count", positive=True)
                    chiplet_area = _number(chiplet.get("die_area_mm2"), f"{product} chiplet area", positive=True)
                    chiplet_node = chiplet.get("node_nm", "").strip()
                    chiplet_region = chiplet.get("manufacturing_region", "").strip()
                    if not chiplet_node or not chiplet_region:
                        raise STECIncompleteError(f"Chiplet source is missing node or fab region for {product}")
                    chiplet_parameters = node_parameters(chiplet_node)
                    if chiplet_parameters.proxy_for_node_nm:
                        warnings.append(f"Explicit chiplet node proxy: {chiplet_node} uses {chiplet_parameters.node_nm} nm parameters")
                    component_area += count * chiplet_area
                    component_regions.append(chiplet_region)
                    component_confidence.append(chiplet.get("confidence", "source-backed"))
                    component_sources.append(chiplet.get("source", ""))
                    if year:
                        component_values.append(_calculate_component(
                            chiplet_area * count, chiplet_node, chiplet_region, year, grid,
                            f"Chiplet evidence: {chiplet.get('source', 'chiplets.csv')}",
                            chiplet.get("die_role"),
                        ))
                candidate_regions = list(dict.fromkeys(component_regions))
                location_level = "chiplet_sourced"
                location_confidence = "mixed" if len(set(component_confidence)) > 1 else component_confidence[0]
                location_basis = " | ".join(dict.fromkeys(component_sources))
                if year and len(component_values) == len(product_chiplets):
                    total = sum(component_values)
                    status = "point"
                    minimum = maximum = total
                    point = total
                    global_total = sum(
                        _calculate_component(
                            _number(chiplet["die_area_mm2"], f"{product} chiplet area", positive=True)
                            * int(_number(chiplet["die_count"], f"{product} die_count", positive=True)),
                            chiplet["node_nm"], "World", year, grid,
                            "Global baseline using Carbon intensity of electricity",
                            chiplet.get("die_role"),
                        )
                        for chiplet in product_chiplets
                    )
                else:
                    raise STECIncompleteError(f"One or more chiplet nodes lack validated STEC parameters for {product}")
            else:
                candidate_regions, location_level, location_confidence, location_basis, location_warnings = _resolve_location(
                    product, vendor, device_type, node, provenance, rules,
                )
                warnings.extend(location_warnings)
                if not year:
                    raise STECIncompleteError(f"Manufacturing year unavailable for {product}")
                if not candidate_regions:
                    raise STECIncompleteError(f"Fab location unavailable for {product}")
                values = [
                    _calculate_component(area, node, region, year, grid, "CarbonSet die area and fab evidence")
                    for region in candidate_regions
                ]
                minimum = min(values)
                maximum = max(values)
                point = values[0] if len(values) == 1 else None
                status = "point" if point is not None else "range"
                global_total = _calculate_component(area, node, "World", year, grid, "Global baseline using Carbon intensity of electricity")
        except (STECIncompleteError, STECValidationError, ValueError) as exc:
            status = "incomplete"
            point = minimum = maximum = global_total = None
            warnings.append(str(exc))

        inventory.append({
            "product": product,
            "type": device_type,
            "vendor": vendor,
            "node_nm": node,
            "carbonset_die_area_mm2": area,
            "manufacturing_year": year,
            "manufacturing_year_status": year_status,
            "location_level": location_level,
            "location_confidence": location_confidence,
            "candidate_regions": ";".join(candidate_regions),
            "status": status,
            "stec_kg_co2e": point,
            "stec_min_kg_co2e": minimum,
            "stec_max_kg_co2e": maximum,
            "chiplet_applied": bool(product_chiplets),
            "chiplet_die_area_mm2": component_area if product_chiplets else None,
            "global_baseline_stec_kg_co2e": global_total,
            "yield_applied": False,
            "market_based_status": "not_available",
            "carbonset_emb_mean_kg_co2e": _optional_number(source_row.get("Emb_Carbon_Mean")),
            "carbonset_emb_min_kg_co2e": _optional_number(source_row.get("Emb_Carbon_Min")),
            "carbonset_emb_max_kg_co2e": _optional_number(source_row.get("Emb_Carbon_Max")),
            "location_basis": location_basis,
            "warnings": " | ".join(dict.fromkeys(warnings)),
        })
    return inventory


def write_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Recompute CarbonHardware location-based STEC per chip.")
    parser.add_argument("--carbonset", type=Path, default=DEFAULT_CARBONSET)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--grid-csv", type=Path, default=DEFAULT_GRID)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true", help="Write result records as JSON to stdout instead of CSV.")
    args = parser.parse_args()

    rows = build_stec_inventory(args.carbonset, args.evidence_dir, args.grid_csv)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
        return
    write_csv(rows, args.output)
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["status"]] += 1
    print(json.dumps({"output": str(args.output), "rows": len(rows), "statusCounts": dict(counts)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
