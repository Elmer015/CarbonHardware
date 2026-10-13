"""Inspect local CSV and Excel datasets without changing them.

The command scans the three Phase 2 raw-data directories by default and writes
an evidence report. It deliberately reports unavailable sources instead of
inventing schemas or labels.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_SUFFIXES = {".csv", ".xls", ".xlsx", ".xlsm"}
DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "raw"
TARGET_TERMS = (
	"embodied",
	"emb carbon",
	"ecfp",
	"operational",
	"ocfp",
	"total carbon",
	"carbon footprint",
	"e_waste",
	"ewaste",
	"stec",
	"cci",
)
UNIT_PATTERN = re.compile(
	r"(?:kg\s*co2e?|g\s*co2e?|t\s*co2e?|wh|kwh|mwh|gco2|kgco2|mm2|nm|years?|hours?)",
	re.IGNORECASE,
)


def _json_value(value: Any) -> Any:
	"""Convert pandas/numpy values to JSON-safe values."""
	if pd.isna(value):
		return None
	if hasattr(value, "item"):
		return value.item()
	return value


def _candidate_targets(columns: list[str]) -> list[dict[str, Any]]:
	candidates = []
	for column in columns:
		normalized = column.lower().replace("_", " ")
		matches = [term for term in TARGET_TERMS if term in normalized]
		if matches:
			candidates.append(
				{
					"column": column,
					"matched_terms": matches,
					"status": "candidate only; verify definition and unit",
				}
			)
	return candidates


def _column_summary(frame: pd.DataFrame) -> list[dict[str, Any]]:
	summaries = []
	for column in frame.columns:
		series = frame[column]
		non_null = series.dropna()
		summary: dict[str, Any] = {
			"name": str(column),
			"dtype": str(series.dtype),
			"missing_count": int(series.isna().sum()),
			"missing_fraction": float(series.isna().mean()),
			"unique_count": int(series.nunique(dropna=True)),
			"unit_token_candidates": sorted(set(UNIT_PATTERN.findall(str(column)))),
		}
		if pd.api.types.is_numeric_dtype(series) and not non_null.empty:
			stats = non_null.describe()
			summary["descriptive_statistics"] = {
				key: float(stats[key])
				for key in ("count", "mean", "std", "min", "25%", "50%", "75%", "max")
				if key in stats
			}
		else:
			summary["descriptive_statistics"] = {}
			if not non_null.empty:
				summary["top_values"] = [
					{"value": _json_value(value), "count": int(count)}
					for value, count in series.value_counts(dropna=True).head(5).items()
				]
		summaries.append(summary)
	return summaries


def _inspect_frame(frame: pd.DataFrame, source: str, sheet: str | None = None) -> dict[str, Any]:
	frame = frame.copy()
	return {
		"source": source,
		"sheet": sheet,
		"rows": int(frame.shape[0]),
		"columns": [str(column) for column in frame.columns],
		"duplicate_rows": int(frame.duplicated().sum()),
		"candidate_targets": _candidate_targets([str(column) for column in frame.columns]),
		"column_profiles": _column_summary(frame),
	}


def inspect_file(path: Path) -> list[dict[str, Any]]:
	"""Inspect one supported file, including every Excel sheet."""
	if path.suffix.lower() == ".csv":
		return [_inspect_frame(pd.read_csv(path), str(path))]

	workbook = pd.ExcelFile(path)
	return [
		_inspect_frame(pd.read_excel(path, sheet_name=sheet), str(path), str(sheet))
		for sheet in workbook.sheet_names
	]


def inspect_directory(data_root: Path) -> dict[str, Any]:
	sources = {}
	for source_name in ("scarif", "carbonset", "environmental"):
		source_path = data_root / source_name
		files = sorted(
			path for path in source_path.rglob("*")
			if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
		) if source_path.exists() else []
		source_result: dict[str, Any] = {
			"path": str(source_path),
			"available": source_path.exists() and bool(files),
			"supported_files": [str(path) for path in files],
			"file_reports": [],
		}
		for path in files:
			try:
				source_result["file_reports"].extend(inspect_file(path))
			except Exception as error:  # Keep the report useful for mixed datasets.
				source_result.setdefault("errors", []).append(
					{"file": str(path), "error": f"{type(error).__name__}: {error}"}
				)
		if not files:
			source_result["limitation"] = "No supported local CSV or Excel files were found."
		sources[source_name] = source_result
	return {"data_root": str(data_root), "sources": sources}


def _markdown_report(report: dict[str, Any]) -> str:
	lines = ["# Dataset Inspection Report", "", f"Data root: `{report['data_root']}`", ""]
	for name, source in report["sources"].items():
		lines.extend([f"## {name}", "", f"Available local data: **{source['available']}**"])
		if source["supported_files"]:
			lines.append("Files: " + ", ".join(f"`{file}`" for file in source["supported_files"]))
		else:
			lines.append(f"Limitation: {source['limitation']}")
		for item in source["file_reports"]:
			sheet = f" (sheet `{item['sheet']}`)" if item["sheet"] else ""
			lines.extend(
				[
					"",
					f"### `{item['source']}`{sheet}",
					f"Rows: {item['rows']}  ",
					f"Columns ({len(item['columns'])}): {', '.join(f'`{column}`' for column in item['columns'])}",
					f"Duplicate rows: {item['duplicate_rows']}",
					f"Candidate targets: {json.dumps(item['candidate_targets'])}",
				]
			)
			for column in item["column_profiles"]:
				lines.append(
					f"- `{column['name']}`: dtype `{column['dtype']}`, "
					f"missing {column['missing_count']} ({column['missing_fraction']:.1%}), "
					f"unique {column['unique_count']}, units suggested by name: "
					f"{', '.join(column['unit_token_candidates']) or 'none'}"
				)
	return "\n".join(lines) + "\n"


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
	parser.add_argument("--json-output", type=Path)
	parser.add_argument("--markdown-output", type=Path)
	args = parser.parse_args()

	report = inspect_directory(args.data_root)
	serialized = json.dumps(report, indent=2, ensure_ascii=True)
	if args.json_output:
		args.json_output.parent.mkdir(parents=True, exist_ok=True)
		args.json_output.write_text(serialized + "\n", encoding="utf-8")
	if args.markdown_output:
		args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
		args.markdown_output.write_text(_markdown_report(report), encoding="utf-8")
	print(_markdown_report(report), end="")


if __name__ == "__main__":
	main()
