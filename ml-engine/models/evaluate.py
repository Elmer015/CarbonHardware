"""Evaluation utilities for embodied-carbon regression experiments."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def regression_metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float | None]:
	"""Calculate held-out regression metrics without hiding undefined R-squared."""
	actual_values = np.asarray(actual, dtype=float)
	predicted_values = np.asarray(predicted, dtype=float)
	metrics: dict[str, float | None] = {
		"mae": float(mean_absolute_error(actual_values, predicted_values)),
		"rmse": float(np.sqrt(mean_squared_error(actual_values, predicted_values))),
		"r2": None,
	}
	if len(actual_values) >= 2 and np.unique(actual_values).size > 1:
		metrics["r2"] = float(r2_score(actual_values, predicted_values))
	return metrics


def residual_report(
	frame: pd.DataFrame,
	*,
	actual_column: str,
	predicted: np.ndarray,
	group_column: str | None = None,
) -> dict[str, Any]:
	"""Summarize residual magnitude and optional hardware-group error patterns."""
	residuals = pd.DataFrame(
		{
			"actual": pd.to_numeric(frame[actual_column], errors="raise"),
			"predicted": np.asarray(predicted, dtype=float),
		}
	)
	residuals["residual"] = residuals["actual"] - residuals["predicted"]
	residuals["absolute_error"] = residuals["residual"].abs()
	summary = {
		"mean_residual": float(residuals["residual"].mean()),
		"residual_std": float(residuals["residual"].std(ddof=0)),
		"mean_absolute_error": float(residuals["absolute_error"].mean()),
		"max_absolute_error": float(residuals["absolute_error"].max()),
		"residual_quantiles": {
			str(level): float(residuals["residual"].quantile(level))
			for level in (0.05, 0.5, 0.95)
		},
	}
	result: dict[str, Any] = {"summary": summary}
	if group_column and group_column in frame:
		by_group = residuals.assign(_group=frame[group_column].to_numpy()).groupby("_group")
		result["by_group"] = {
			str(group): {
				"rows": int(group_frame.shape[0]),
				"mae": float(group_frame["absolute_error"].mean()),
				"mean_residual": float(group_frame["residual"].mean()),
			}
			for group, group_frame in by_group
		}
	return result


def evaluate_predictions(
	frame: pd.DataFrame,
	*,
	target_column: str,
	predicted: np.ndarray,
	group_column: str | None = None,
) -> dict[str, Any]:
	return {
		"metrics": regression_metrics(frame[target_column], predicted),
		"residuals": residual_report(
			frame,
			actual_column=target_column,
			predicted=predicted,
			group_column=group_column,
		),
	}
