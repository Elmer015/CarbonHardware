import { AppError } from "../middleware/errorHandler.js";

function nonnegative(value, field) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) {
    throw new AppError(400, `${field} must be finite and non-negative`);
  }
  return number;
}

export function calculateUpgradeTimeline({
  carbonBudgetKgCo2e,
  embodiedCarbonKgCo2e,
  annualOperationalCarbonKgCo2e,
  usageYears,
}) {
  const carbonBudget = nonnegative(carbonBudgetKgCo2e, "carbonBudgetKgCo2e");
  if (carbonBudget === 0) throw new AppError(400, "carbonBudgetKgCo2e must be greater than zero");
  const embodied = nonnegative(embodiedCarbonKgCo2e, "embodiedCarbonKgCo2e");
  const annualOperational = nonnegative(annualOperationalCarbonKgCo2e, "annualOperationalCarbonKgCo2e");
  const yearsUsed = nonnegative(usageYears, "usageYears");
  const currentCumulativeCarbonKgCo2e = embodied + annualOperational * yearsUsed;
  const budgetReached = currentCumulativeCarbonKgCo2e >= carbonBudget;

  if (annualOperational === 0) {
    return {
      status: budgetReached ? "budget_already_reached" : "no_annual_operational_carbon",
      currentCumulativeCarbonKgCo2e,
      annualOperationalCarbonKgCo2e: annualOperational,
      yearsToBudget: budgetReached ? 0 : null,
    };
  }

  return {
    status: budgetReached ? "budget_already_reached" : "estimated",
    currentCumulativeCarbonKgCo2e,
    annualOperationalCarbonKgCo2e: annualOperational,
    yearsToBudget: Math.max(0, (carbonBudget - currentCumulativeCarbonKgCo2e) / annualOperational),
  };
}
