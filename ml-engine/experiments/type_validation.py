"""CPU/GPU-specific validation of the Phase 4 embodied-carbon model.

Compares, on the same group-disjoint Phase 3 splits:
  A. the saved Phase 4 artifact (5 numeric features, no Type);
  B. the same Random Forest configuration refit with Type as a binary feature;
  C. separate CPU-only and GPU-only models.
It also reports leave-one-vendor-out results, the largest errors per type, and
test rows whose features fall outside the training range.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
INTERIM = ROOT / "data" / "interim"
ARTIFACT = ROOT / "ml-engine" / "artifacts" / "embodied_carbon_model.joblib"

FEATURES = ["Process Size (nm)", "TDP (W)", "DieSizeValue", "#dies", "Avg Die Area"]
TARGET = "Emb_Carbon_Mean"
GROUP = "Product"
SEED = 42


def make_model() -> RandomForestRegressor:
	# Same configuration as the selected Phase 4 model (random_forest_depth_10_leaf_1).
	return RandomForestRegressor(n_estimators=100, max_depth=10, min_samples_leaf=1, random_state=SEED, n_jobs=-1)


def metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
	actual = np.asarray(actual, dtype=float)
	predicted = np.asarray(predicted, dtype=float)
	error = predicted - actual
	ape = np.abs(error) / actual
	ss_res = float(np.sum(error**2))
	ss_tot = float(np.sum((actual - actual.mean()) ** 2))
	return {
		"n": int(actual.size),
		"mae": float(np.mean(np.abs(error))),
		"rmse": float(np.sqrt(np.mean(error**2))),
		"r2": 1 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
		"mape_pct": float(np.mean(ape) * 100),
		"median_ape_pct": float(np.median(ape) * 100),
		"max_abs_error": float(np.max(np.abs(error))),
	}


def load_splits() -> dict[str, pd.DataFrame]:
	cleaned = pd.read_csv(INTERIM / "carbonset-cleaned.csv")
	# Products whose name maps to more than one Type cannot be joined unambiguously.
	type_counts = cleaned.groupby(GROUP)["Type"].nunique()
	ambiguous = set(type_counts[type_counts > 1].index)
	lookup = (
		cleaned[~cleaned[GROUP].isin(ambiguous)]
		.drop_duplicates(GROUP)
		.set_index(GROUP)[["Type", "Vendor", "Release Date"]]
	)
	splits = {}
	for name in ("train", "validation", "test"):
		frame = pd.read_csv(PROCESSED / f"carbonset-{name}.csv")
		frame = frame[~frame[GROUP].isin(ambiguous)].join(lookup, on=GROUP)
		frame["is_gpu"] = (frame["Type"] == "GPU").astype(int)
		splits[name] = frame.reset_index(drop=True)
	splits["_ambiguous_products"] = pd.DataFrame({GROUP: sorted(ambiguous)})
	return splits


def per_type_rows(model_name: str, split: str, frame: pd.DataFrame, predicted: np.ndarray) -> list[dict]:
	rows = []
	for label, mask in (("ALL", np.ones(len(frame), bool)), ("CPU", frame["Type"].eq("CPU").to_numpy()), ("GPU", frame["Type"].eq("GPU").to_numpy())):
		if mask.sum() < 2:
			continue
		rows.append({"model": model_name, "split": split, "type": label, **metrics(frame.loc[mask, TARGET], predicted[mask])})
	return rows


def run() -> dict[str, pd.DataFrame]:
	splits = load_splits()
	train, validation, test = splits["train"], splits["validation"], splits["test"]
	predictions: dict[str, dict[str, np.ndarray]] = {}

	artifact = joblib.load(ARTIFACT)
	predictions["A_saved_artifact_no_type"] = {
		s: artifact["model"].predict(f[artifact["feature_columns"]]) for s, f in (("validation", validation), ("test", test))
	}

	refit = make_model().fit(train[FEATURES], train[TARGET])
	predictions["A2_refit_no_type"] = {s: refit.predict(f[FEATURES]) for s, f in (("validation", validation), ("test", test))}

	with_type = make_model().fit(train[FEATURES + ["is_gpu"]], train[TARGET])
	predictions["B_with_type_feature"] = {
		s: with_type.predict(f[FEATURES + ["is_gpu"]]) for s, f in (("validation", validation), ("test", test))
	}

	separate: dict[str, np.ndarray] = {}
	for split_name, frame in (("validation", validation), ("test", test)):
		out = np.zeros(len(frame))
		for kind in ("CPU", "GPU"):
			model = make_model().fit(train.loc[train["Type"].eq(kind), FEATURES], train.loc[train["Type"].eq(kind), TARGET])
			mask = frame["Type"].eq(kind).to_numpy()
			out[mask] = model.predict(frame.loc[mask, FEATURES])
		separate[split_name] = out
	predictions["C_separate_cpu_gpu_models"] = separate

	metric_rows = []
	for model_name, by_split in predictions.items():
		for split_name, frame in (("validation", validation), ("test", test)):
			metric_rows.extend(per_type_rows(model_name, split_name, frame, by_split[split_name]))
	metrics_frame = pd.DataFrame(metric_rows)

	# Largest test errors per type for the saved artifact.
	errors = test[[GROUP, "Type", "Vendor"] + FEATURES + [TARGET]].copy()
	errors["predicted_saved_model"] = predictions["A_saved_artifact_no_type"]["test"]
	errors["predicted_with_type"] = predictions["B_with_type_feature"]["test"]
	errors["abs_error_saved_model"] = (errors["predicted_saved_model"] - errors[TARGET]).abs()
	errors["ape_pct_saved_model"] = errors["abs_error_saved_model"] / errors[TARGET] * 100
	largest = (
		errors.sort_values("abs_error_saved_model", ascending=False)
		.groupby("Type", group_keys=False)
		.head(10)
		.sort_values(["Type", "abs_error_saved_model"], ascending=[True, False])
	)

	# Out-of-range: any test feature outside the min/max of training rows of the same Type.
	range_rows = []
	for idx, row in test.iterrows():
		same_type = train[train["Type"].eq(row["Type"])]
		outside = [c for c in FEATURES if row[c] < same_type[c].min() or row[c] > same_type[c].max()]
		outside_all = [c for c in FEATURES if row[c] < train[c].min() or row[c] > train[c].max()]
		if outside or outside_all:
			range_rows.append({
				GROUP: row[GROUP], "Type": row["Type"], "Vendor": row["Vendor"],
				"outside_all_train_range": ", ".join(outside_all) or "-",
				"outside_same_type_train_range": ", ".join(outside) or "-",
				TARGET: row[TARGET],
				"predicted_saved_model": float(errors.loc[idx, "predicted_saved_model"]),
				"abs_error": float(errors.loc[idx, "abs_error_saved_model"]),
			})
	out_of_range = pd.DataFrame(range_rows)

	# Leave-one-vendor-out on all prepared rows (vendor groups are disjoint by construction).
	full = pd.concat([train, validation, test], ignore_index=True)
	lovo_rows = []
	for vendor in sorted(full["Vendor"].dropna().unique()):
		held = full["Vendor"].eq(vendor)
		for feature_set, cols in (("no_type", FEATURES), ("with_type", FEATURES + ["is_gpu"])):
			model = make_model().fit(full.loc[~held, cols], full.loc[~held, TARGET])
			predicted = model.predict(full.loc[held, cols])
			held_frame = full.loc[held].reset_index(drop=True)
			for row in per_type_rows(f"LOVO_{feature_set}", f"held_out={vendor}", held_frame, predicted):
				row["train_types"] = ", ".join(sorted(full.loc[~held, "Type"].unique()))
				lovo_rows.append(row)
	lovo = pd.DataFrame(lovo_rows)

	# Die-signature leakage check: the target is a deterministic function of the die
	# parameters, so products sharing a die must not sit on both sides of a split.
	die_cols = ["Process Size (nm)", "DieSizeValue", "#dies", "Avg Die Area"]
	full["die_signature"] = full[die_cols].astype(str).agg("|".join, axis=1)
	signature_targets = full.groupby("die_signature")[TARGET].nunique()
	train_sigs = set(train[die_cols].astype(str).agg("|".join, axis=1))
	test_sigs = test[die_cols].astype(str).agg("|".join, axis=1)
	leakage = pd.DataFrame([
		{"check": "rows (prepared, unambiguous Type)", "value": len(full)},
		{"check": "unique die signatures", "value": int(signature_targets.size)},
		{"check": "die signatures with more than one target value", "value": int((signature_targets > 1).sum())},
		{"check": "test rows whose die signature also appears in train", "value": int(test_sigs.isin(train_sigs).sum())},
		{"check": "test rows", "value": len(test)},
	])

	from sklearn.model_selection import GroupKFold

	die_cv_rows = []
	for feature_set, cols in (("no_type", FEATURES), ("with_type", FEATURES + ["is_gpu"])):
		predicted = np.zeros(len(full))
		for train_idx, test_idx in GroupKFold(n_splits=5).split(full, groups=full["die_signature"]):
			model = make_model().fit(full.iloc[train_idx][cols], full.iloc[train_idx][TARGET])
			predicted[test_idx] = model.predict(full.iloc[test_idx][cols])
		die_cv_rows.extend(per_type_rows(f"DieGroupKFold5_{feature_set}", "5-fold by die signature", full, predicted))
	die_cv = pd.DataFrame(die_cv_rows)

	counts = (
		pd.concat({s: splits[s]["Type"].value_counts() for s in ("train", "validation", "test")}, axis=1)
		.fillna(0).astype(int).rename_axis("Type").reset_index()
	)
	return {
		"metrics": metrics_frame,
		"largest_errors": largest,
		"out_of_range": out_of_range,
		"lovo": lovo,
		"leakage": leakage,
		"die_cv": die_cv,
		"counts": counts,
		"ambiguous": splits["_ambiguous_products"],
	}


if __name__ == "__main__":
	results = run()
	pd.set_option("display.width", 200)
	print(results["metrics"].round(3).to_string(index=False))
	print(json.dumps({k: len(v) for k, v in results.items()}, indent=2))
	sys.exit(0)
