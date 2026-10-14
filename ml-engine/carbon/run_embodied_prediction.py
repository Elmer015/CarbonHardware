"""Run Phase 4 embodied-carbon predictions and write provenance metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml-engine" / "models"))
sys.path.insert(0, str(ROOT / "ml-engine" / "carbon"))

from embodied_carbon import predict_embodied_carbon


FEATURE_COLUMNS = [
    "Process Size (nm)",
    "TDP (W)",
    "DieSizeValue",
    "#dies",
    "Avg Die Area",
]
DEFAULT_MODEL = ROOT / "ml-engine" / "artifacts" / "embodied_carbon_model.joblib"
DEFAULT_OUTPUT = ROOT / "data" / "interim" / "embodied-predictions.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    frame = pd.read_csv(args.input_csv)
    missing = sorted(set(FEATURE_COLUMNS) - set(frame.columns))
    if missing:
        raise SystemExit(f"Input CSV is missing required hardware features: {missing}")

    results = predict_embodied_carbon(args.model, frame[FEATURE_COLUMNS])
    output = []
    for result in results:
        output.append(
            {
                "predicted_embodied_carbon_kg_co2e": result.value,
                "value_kind": result.value_kind,
                "model_type": result.metadata.get("model_type"),
                "dataset_version": result.metadata.get("dataset_version"),
                "functional_unit": result.functional_unit,
                "boundary": result.boundary,
            }
        )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output_json), "rows": len(output)}, indent=2))


if __name__ == "__main__":
    main()