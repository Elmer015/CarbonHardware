"""Empirical prediction interval for the embodied-carbon model (custom processors).

Custom processors have no CarbonSet min/max, so their uncertainty comes from the
model's own out-of-fold error. Residuals are taken from 5-fold cross-validation
grouped by die signature (products sharing a die never sit on both sides of a
fold), using the same Random Forest configuration as the Phase 4 artifact.

The interval is multiplicative: [pred * (1 + q_low), pred * (1 + q_high)], with
q the quantiles of the relative residual (actual - pred) / pred. Coverage holds
on CarbonSet by construction and is not validated on external hardware.

Writes ml-engine/artifacts/embodied_prediction_interval.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

import type_validation as tv

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "ml-engine" / "artifacts" / "embodied_prediction_interval.json"
LEVELS = {"0.90": (0.05, 0.95), "0.95": (0.025, 0.975)}


def out_of_fold() -> pd.DataFrame:
	splits = tv.load_splits()
	full = pd.concat([splits["train"], splits["validation"], splits["test"]], ignore_index=True)
	die_cols = ["Process Size (nm)", "DieSizeValue", "#dies", "Avg Die Area"]
	groups = full[die_cols].astype(str).agg("|".join, axis=1)
	predicted = np.zeros(len(full))
	for train_idx, test_idx in GroupKFold(n_splits=5).split(full, groups=groups):
		model = tv.make_model().fit(full.iloc[train_idx][tv.FEATURES], full.iloc[train_idx][tv.TARGET])
		predicted[test_idx] = model.predict(full.iloc[test_idx][tv.FEATURES])
	full["predicted"] = predicted
	full["relative_residual"] = (full[tv.TARGET] - predicted) / predicted
	return full


def quantiles(residuals: pd.Series) -> dict[str, dict[str, float]]:
	return {
		level: {"q_low": float(residuals.quantile(low)), "q_high": float(residuals.quantile(high))}
		for level, (low, high) in LEVELS.items()
	}


def main() -> None:
	frame = out_of_fold()
	payload = {
		"method": "multiplicative interval from relative out-of-fold residuals, 5-fold GroupKFold by die signature",
		"model_configuration": "RandomForestRegressor(n_estimators=100, max_depth=10, min_samples_leaf=1, random_state=42)",
		"residual_definition": "(actual - predicted) / predicted",
		"coverage_note": "empirical on CarbonSet only; not calibrated or validated on hardware outside CarbonSet",
		"rows": int(len(frame)),
		"pooled": quantiles(frame["relative_residual"]),
		"by_type": {kind: quantiles(group["relative_residual"]) for kind, group in frame.groupby("Type")},
	}
	OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
	print(json.dumps(payload, indent=2))


if __name__ == "__main__":
	main()
