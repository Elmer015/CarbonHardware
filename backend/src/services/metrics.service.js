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
