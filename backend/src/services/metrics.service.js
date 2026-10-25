import { AppError } from "../middleware/errorHandler.js";

function finite(value, field) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) throw new AppError(400, `${field} must be finite`);
  return parsed;
}

function nonnegative(value, field) {
  const parsed = finite(value, field);
  if (parsed < 0) throw new AppError(400, `${field} must be non-negative`);
  return parsed;
}

export function calculateCci({ totalCarbonKgCo2e, completedComputeWork, workloadUnit, lifecycleBoundary, analysisPeriod }) {
  const carbon = nonnegative(totalCarbonKgCo2e, "totalCarbonKgCo2e");
  const work = finite(completedComputeWork, "completedComputeWork");
  if (work <= 0) throw new AppError(400, "completedComputeWork must be greater than zero");
  if (![workloadUnit, lifecycleBoundary, analysisPeriod].every((value) => typeof value === "string" && value.trim())) {
    throw new AppError(400, "workloadUnit, lifecycleBoundary, and analysisPeriod are required");
  }
  return {
    cciKgCo2ePerWorkload: carbon / work,
    totalCarbonKgCo2e: carbon,
    completedComputeWork: work,
    workloadUnit,
    lifecycleBoundary,
    analysisPeriod,
    valueKind: "compute_carbon_intensity",
  };
}

export function summarizeUncertainty({ lowerValue, centralValue, upperValue, samples, unit, source, uncertaintyKind, method, confidenceLevel = 0.95 }) {
  if (!unit || !source || !uncertaintyKind) throw new AppError(400, "unit, source, and uncertaintyKind are required");
  if (Array.isArray(samples)) {
    if (samples.length < 2) throw new AppError(400, "at least two samples are required");
    const values = samples.map((value) => nonnegative(value, "samples"));
    const sorted = [...values].sort((a, b) => a - b);
    const level = finite(confidenceLevel, "confidenceLevel");
    if (level <= 0 || level >= 1) throw new AppError(400, "confidenceLevel must be between 0 and 1");
    const quantile = (position) => {
      const index = (sorted.length - 1) * position;
      const lower = Math.floor(index);
      const upper = Math.ceil(index);
      return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower);
    };
    return {
      centralValue: values.reduce((sum, value) => sum + value, 0) / values.length,
      lowerValue: quantile((1 - level) / 2),
      upperValue: quantile(1 - (1 - level) / 2),
      unit, source, uncertaintyKind, method: `empirical quantiles at ${level.toFixed(3)}; not calibrated coverage`,
      sampleCount: values.length, valueKind: "uncertainty_summary",
    };
  }
  const lower = nonnegative(lowerValue, "lowerValue");
  const central = nonnegative(centralValue, "centralValue");
  const upper = nonnegative(upperValue, "upperValue");
  if (lower > central || central > upper) throw new AppError(400, "values must satisfy 0 <= lowerValue <= centralValue <= upperValue");
  return { centralValue: central, lowerValue: lower, upperValue: upper, unit, source, uncertaintyKind, method: method || "source-provided interval", sampleCount: null, valueKind: "uncertainty_summary" };
}
