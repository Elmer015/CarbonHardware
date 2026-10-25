import { AppError } from "../middleware/errorHandler.js";

function nonnegative(value, field) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) throw new AppError(400, `${field} must be finite and non-negative`);
  return number;
}

export function calculateOperationalEnergy({ tdpW, hoursPerDay, usageYears, utilization, daysPerYear }) {
  const power = nonnegative(tdpW, "tdpW");
  const hours = nonnegative(hoursPerDay, "hoursPerDay");
  const years = nonnegative(usageYears, "usageYears");
  const days = nonnegative(daysPerYear, "daysPerYear");
  const use = Number(utilization);
  if (!Number.isFinite(use) || use < 0 || use > 1) throw new AppError(400, "utilization must be between 0 and 1");
  if (hours > 24 || days > 366) throw new AppError(400, "hoursPerDay must be <= 24 and daysPerYear must be <= 366");
  return {
    electricityKwh: power / 1000 * hours * days * years * use,
    unit: "kWh", calculationStatus: "complete", carbonStatus: "pending_grid_intensity",
    assumptions: { method: "TDP-based assumption", powerSource: "TDP as power proxy", powerToEnergy: "tdpW / 1000 * hoursPerDay * daysPerYear * usageYears * utilization", tdpW: power, hoursPerDay: hours, daysPerYear: days, usageYears: years, utilization: use },
  };
}