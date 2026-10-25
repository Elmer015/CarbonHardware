"""Location-based grid carbon intensity per region and year.

Source table: data/grid/grid-intensity.csv with columns
    region, year, grid_intensity_g_co2e_per_kwh, source, basis
built from the Our World in Data / Ember series in data/raw/grid by
``python ml-engine/carbon/grid_intensity.py --build``.

No value is interpolated or extrapolated: a missing region/year raises
GridIntensityUnavailableError.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_OWID = ROOT / "data" / "raw" / "grid" / "owid-carbon-intensity-electricity.csv"
GRID_TABLE = ROOT / "data" / "grid" / "grid-intensity.csv"
OWID_SOURCE = "Our World in Data / Ember, Carbon intensity of electricity"
BASIS = "location-based"


class GridIntensityUnavailableError(LookupError):
    """Raised when no sourced grid intensity exists for a region and year."""


@dataclass(frozen=True)
class GridIntensity:
    region: str
    year: int
    g_co2e_per_kwh: float
    source: str
    basis: str

    @property
    def kg_co2e_per_kwh(self) -> float:
        return self.g_co2e_per_kwh / 1000


@lru_cache(maxsize=4)
def load_grid_table(path: str = str(GRID_TABLE)) -> dict[tuple[str, int], GridIntensity]:
    table_path = Path(path)
    if not table_path.exists():
        raise GridIntensityUnavailableError(f"Grid intensity table is missing: {table_path}")
    with table_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {
        (row["region"], int(row["year"])): GridIntensity(
            region=row["region"],
            year=int(row["year"]),
            g_co2e_per_kwh=float(row["grid_intensity_g_co2e_per_kwh"]),
            source=row["source"],
            basis=row["basis"],
        )
        for row in rows
    }


def grid_intensity(region: str, year: int, *, path: str = str(GRID_TABLE)) -> GridIntensity:
    if not region:
        raise GridIntensityUnavailableError("usage region is required")
    try:
        return load_grid_table(path)[(region, int(year))]
    except KeyError as exc:
        raise GridIntensityUnavailableError(f"No sourced grid intensity for {region} in {year}") from exc


def list_regions(*, path: str = str(GRID_TABLE)) -> dict[str, Any]:
    years: dict[str, list[int]] = {}
    for region, year in load_grid_table(path):
        years.setdefault(region, []).append(year)
    return {
        "source": OWID_SOURCE,
        "basis": BASIS,
        "unit": "g CO2e/kWh",
        "regions": [
            {"region": region, "firstYear": min(values), "lastYear": max(values)}
            for region, values in sorted(years.items())
        ],
    }


def build_grid_table(raw_path: Path = RAW_OWID, output_path: Path = GRID_TABLE) -> int:
    with raw_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    value_key = next(key for key in rows[0] if key.startswith("co2_intensity"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["region", "year", "grid_intensity_g_co2e_per_kwh", "source", "basis"])
        for row in rows:
            writer.writerow([row["entity"], row["year"], row[value_key], OWID_SOURCE, BASIS])
    load_grid_table.cache_clear()
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="rebuild data/grid/grid-intensity.csv from data/raw/grid")
    args = parser.parse_args()
    if args.build:
        print(f"wrote {build_grid_table()} rows to {GRID_TABLE.relative_to(ROOT).as_posix()}")
