import { AppError } from "../middleware/errorHandler.js";

const MIN_CANDIDATE_TDP_RATIO = 0.5;
const MAX_CANDIDATES = 3;
const RECENT_CATALOG_YEARS = 5;

function finiteNonnegative(value, field) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new AppError(400, `${field} must be finite and non-negative`);
  }
  return parsed;
}

export function calculateCarbonReplacementComparison({
  currentProcessor,
  candidates,
  currentReleaseDate,
  hoursPerDay,
  utilization,
  daysPerYear,
  gridIntensityKgCo2ePerKwh,
}) {
  const processorType = String(currentProcessor.type || "").toUpperCase();
  if (!["CPU", "GPU"].includes(processorType)) {
    throw new AppError(400, "processorType must be CPU or GPU");
  }

  const currentTdpW = finiteNonnegative(currentProcessor.tdpW, "tdpW");
  const currentReleaseTimestamp = Date.parse(currentReleaseDate || "");
  const hours = finiteNonnegative(hoursPerDay, "hoursPerDay");
  const days = finiteNonnegative(daysPerYear, "daysPerYear");
  const utilizationValue = Number(utilization);
  const gridIntensity = finiteNonnegative(gridIntensityKgCo2ePerKwh, "gridIntensityKgCo2ePerKwh");
  if (!Number.isFinite(utilizationValue) || utilizationValue < 0 || utilizationValue > 1) {
    throw new AppError(400, "utilization must be between 0 and 1");
  }
  if (hours > 24 || days > 366) {
    throw new AppError(400, "hoursPerDay must be <= 24 and daysPerYear must be <= 366");
  }

  const annualCarbonPerWatt = hours * days * utilizationValue / 1000 * gridIntensity;
  const currentAnnualOperationalCarbonKgCo2e = currentTdpW * annualCarbonPerWatt;
  const sameTypeCandidates = candidates.filter((candidate) =>
    candidate.name !== currentProcessor.name && String(candidate.type).toUpperCase() === processorType);
  if (Number.isNaN(currentReleaseTimestamp)) {
    return {
      status: "current_release_date_unavailable",
      currentProcessorTdpW: currentTdpW,
      currentAnnualOperationalCarbonKgCo2e,
      candidates: [],
    };
  }

  const newerCandidates = sameTypeCandidates.filter((candidate) => {
    const candidateReleaseTimestamp = Date.parse(candidate.releaseDate || "");
    return Number.isFinite(candidateReleaseTimestamp) && candidateReleaseTimestamp > currentReleaseTimestamp;
  });
  const catalogReleaseYears = candidates
    .map((candidate) => new Date(candidate.releaseDate || "").getUTCFullYear())
    .filter((year) => Number.isInteger(year) && year >= 1900);
  const latestCatalogYear = Math.max(...catalogReleaseYears);
  const minimumCandidateYear = latestCatalogYear - RECENT_CATALOG_YEARS + 1;
  const recentCandidates = newerCandidates.filter((candidate) =>
    new Date(candidate.releaseDate).getUTCFullYear() >= minimumCandidateYear);
  const similarTdpCandidates = recentCandidates.filter((candidate) =>
    Number.isFinite(candidate.tdpW)
      && candidate.tdpW >= currentTdpW * MIN_CANDIDATE_TDP_RATIO
      && candidate.tdpW < currentTdpW);
  const viableCandidates = annualCarbonPerWatt > 0 ? similarTdpCandidates
    .filter((candidate) => Number.isFinite(candidate.embodiedCarbonMeanKgCo2e)
      && candidate.embodiedCarbonMeanKgCo2e >= 0)
    .map((candidate) => {
      const annualOperationalCarbonKgCo2e = candidate.tdpW * annualCarbonPerWatt;
      const annualCarbonSavingsKgCo2e = currentAnnualOperationalCarbonKgCo2e - annualOperationalCarbonKgCo2e;
      return {
        name: candidate.name,
        type: processorType,
        releaseDate: candidate.releaseDate,
        tdpW: candidate.tdpW,
        embodiedCarbonKgCo2e: candidate.embodiedCarbonMeanKgCo2e,
        embodiedCarbonMinKgCo2e: candidate.embodiedCarbonMinKgCo2e,
        embodiedCarbonMaxKgCo2e: candidate.embodiedCarbonMaxKgCo2e,
        annualOperationalCarbonKgCo2e,
        annualCarbonSavingsKgCo2e,
        yearsToCarbonPayback: candidate.embodiedCarbonMeanKgCo2e / annualCarbonSavingsKgCo2e,
      };
    })
    .sort((left, right) =>
      left.yearsToCarbonPayback - right.yearsToCarbonPayback
      || left.name.localeCompare(right.name))
    .slice(0, MAX_CANDIDATES) : [];

  if (viableCandidates.length === 0) {
    return {
      status: !sameTypeCandidates.length
        ? "no_same_type_candidate"
        : !newerCandidates.length
          ? "no_newer_candidate"
          : !recentCandidates.length
            ? "no_recent_candidate"
          : !similarTdpCandidates.length
            ? "no_similar_tdp_candidate"
            : "no_operational_carbon_savings",
      currentAnnualOperationalCarbonKgCo2e,
      currentProcessorTdpW: currentTdpW,
      candidates: [],
    };
  }

  return {
    status: "estimated",
    currentProcessorTdpW: currentTdpW,
    currentAnnualOperationalCarbonKgCo2e,
    candidates: viableCandidates,
    metadata: {
      candidateSelection: "up to three same-type CarbonSet processors newer than the selected processor and within the catalog's latest five release years, with TDP from 50% to below 100% of the current processor, ranked by estimated carbon payback",
      minimumCandidateTdpRatio: MIN_CANDIDATE_TDP_RATIO,
      minimumCandidateReleaseYear: minimumCandidateYear,
      catalogLatestReleaseYear: latestCatalogYear,
      candidateEmbodiedCarbonSource: "CarbonSet Emb_Carbon_Mean",
      annualOperationalCarbonMethod: "TDP proxy with the submitted usage pattern and grid intensity",
      equivalentWorkloadAssumed: true,
      performanceEvaluated: false,
      endOfLifeCarbonIncluded: false,
    },
  };
}
