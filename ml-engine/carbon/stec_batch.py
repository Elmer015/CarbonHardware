"""Batch STEC for every processor in the cleaned CarbonSet table.

Usage (from the repository root):

    python ml-engine/carbon/stec_batch.py

Writes data/processed/stec-per-chip.csv and data/processed/stec-batch-summary.json.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from stec_evidence import GRID_SOURCE, load_evidence, resolve_processor_stec

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "interim" / "carbonset-cleaned.csv"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "stec-per-chip.csv"
DEFAULT_SUMMARY = ROOT / "data" / "processed" / "stec-batch-summary.json"

FIELDS = [
    "product", "type", "vendor", "node_nm", "carbonset_die_area_mm2", "manufacturing_year",
    "manufacturing_year_status", "location_level", "location_confidence", "candidate_regions",
    "status", "stec_kg_co2e", "stec_min_kg_co2e", "stec_max_kg_co2e", "chiplet_applied",
    "chiplet_die_area_mm2", "global_baseline_stec_kg_co2e", "yield_applied", "market_based_status",
    "carbonset_emb_mean_kg_co2e", "carbonset_emb_min_kg_co2e", "carbonset_emb_max_kg_co2e",
    "location_basis", "warnings",
]


def processors(input_path: Path) -> list[dict]:
    with input_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    seen: set[str] = set()
    unique = []
    for row in rows:
        if row["Product"] in seen:
            continue
        seen.add(row["Product"])
        unique.append(row)
    return unique


def run(input_path: Path, output_path: Path, summary_path: Path) -> dict:
    evidence = load_evidence()
    records = []
    for row in processors(input_path):
        result = resolve_processor_stec({
            "name": row["Product"], "type": row["Type"], "vendor": row["Vendor"],
            "processSizeNm": row["Process Size (nm)"], "dieAreaMm2": float(row["DieSizeValue"]),
            "releaseYear": int(row["Release Date"][:4]),
        }, evidence=evidence)
        complete = [item for item in result["regions"] if item["status"] == "complete"]
        records.append({
            "product": result["product"], "type": result["type"], "vendor": result["vendor"],
            "node_nm": result["nodeNm"], "carbonset_die_area_mm2": result["dieAreaMm2"],
            "manufacturing_year": result["manufacturingYear"],
            "manufacturing_year_status": result["manufacturingYearStatus"],
            "location_level": result["location"]["level"],
            "location_confidence": result["location"]["confidence"],
            "candidate_regions": ";".join(result["location"]["candidates"]),
            "status": result["status"],
            "stec_kg_co2e": result["stecKgCo2e"],
            "stec_min_kg_co2e": result["stecMinKgCo2e"],
            "stec_max_kg_co2e": result["stecMaxKgCo2e"],
            "chiplet_applied": result["chiplet"].get("applied", False),
            "chiplet_die_area_mm2": result["chiplet"].get("totalDieAreaMm2"),
            "global_baseline_stec_kg_co2e": result["globalBaseline"]["stecKgCo2e"],
            "yield_applied": any(item["yield"]["applied"] for item in complete),
            "market_based_status": ";".join(sorted({item["marketBased"]["status"] for item in complete})) or "not_available",
            "carbonset_emb_mean_kg_co2e": float(row["Emb_Carbon_Mean"]),
            "carbonset_emb_min_kg_co2e": float(row["Emb_Carbon_Min"]),
            "carbonset_emb_max_kg_co2e": float(row["Emb_Carbon_Max"]),
            "location_basis": result["location"]["basis"],
            "warnings": " | ".join(result["warnings"]),
        })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    summary = {
        "input": str(input_path.relative_to(ROOT)),
        "output": str(output_path.relative_to(ROOT)),
        "processors": len(records),
        "grid_source": GRID_SOURCE,
        "status_counts": dict(Counter(r["status"] for r in records)),
        "location_level_counts": dict(Counter(r["location_level"] for r in records)),
        "manufacturing_year_status_counts": dict(Counter(r["manufacturing_year_status"] for r in records)),
        "chiplet_products": sum(1 for r in records if r["chiplet_applied"]),
        "yield_corrected_products": sum(1 for r in records if r["yield_applied"]),
        "market_based_computed_products": sum(1 for r in records if "computed" in r["market_based_status"]),
        "label": "estimated location-based die STEC; see location_level and warnings per row",
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    print(json.dumps(run(args.input_csv, args.output_csv, args.summary_json), indent=2))


if __name__ == "__main__":
    main()
