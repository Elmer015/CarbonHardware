import { AppError } from "../middleware/errorHandler.js";

export function getResnet50Benchmarks(request, response) {
  const results = request.app.locals.resnet50Benchmarks;
  const eligible = results.filter((row) => row.recommendationEligible);
  const productCount = new Set(results.map((row) => row.product)).size;

  response.json({
    results,
    metadata: {
      benchmark: "MLPerf Inference ResNet-50 Offline",
      carbonsetMappedRows: results.length,
      matchedProducts: productCount,
      comparableRows: eligible.length,
      notRankedRows: results.length - eligible.length,
      comparisonBasis: "Same MLPerf suite version, system type, configuration class, and input precision; cohorts require at least two CarbonSet products",
      embodiedCarbonSource: "Exact CarbonSet product match: Emb_Carbon_Mean, with CarbonSet Min/Max range",
      embodiedCarbonUnit: "kg CO2e per inference processor",
      performanceUnit: "completed inference images per second for the whole benchmark system",
      embodiedBoundary: "CarbonSet inference-processor embodied carbon only; multiplied by device count; host and other server components excluded",
    },
  });
}

export function getResnet50Recommendations(request, response) {
  const processorName = String(request.query.processorName || "").trim();
  if (!processorName) throw new AppError(400, "processorName is required");

  const rows = request.app.locals.resnet50Benchmarks;
  const baselineRows = rows.filter((row) =>
    row.product === processorName && row.recommendationEligible);
  const recommendations = new Map();

  for (const baseline of baselineRows) {
    const candidates = rows.filter((candidate) =>
      candidate.recommendationEligible
      && candidate.comparisonGroup === baseline.comparisonGroup
      && candidate.product !== processorName
      && candidate.systemEmbodiedCarbonMeanKg <= baseline.systemEmbodiedCarbonMeanKg
      && candidate.throughputSamplesPerS > baseline.throughputSamplesPerS);

    for (const candidate of candidates) {
      const current = recommendations.get(candidate.benchmarkId);
      if (!current || baseline.throughputSamplesPerS > current.baseline.throughputSamplesPerS) {
        recommendations.set(candidate.benchmarkId, { ...candidate, baseline });
      }
    }
  }

  const results = [...recommendations.values()]
    .map((candidate) => ({
      ...candidate,
      embodiedCarbonDifferenceKg: candidate.systemEmbodiedCarbonMeanKg - candidate.baseline.systemEmbodiedCarbonMeanKg,
      throughputImprovementPercent: (candidate.throughputSamplesPerS / candidate.baseline.throughputSamplesPerS - 1) * 100,
    }))
    .sort((left, right) =>
      right.throughputImprovementPercent - left.throughputImprovementPercent
      || left.systemEmbodiedCarbonMeanKg - right.systemEmbodiedCarbonMeanKg);

  response.json({
    results,
    metadata: {
      processorName,
      baselineRows: baselineRows.length,
      recommendationCount: results.length,
      comparisonBasis: "Same MLPerf suite version, system type, configuration class, and input precision",
      embodiedCarbonUnit: "kg CO2e for inference devices in the benchmark system",
      performanceUnit: "completed inference images per second for the whole benchmark system",
      selectionRule: "Candidate must use a different CarbonSet product, have equal or lower embodied carbon, and higher throughput than the selected processor's benchmark system",
      carbonSource: "CarbonSet Emb_Carbon_Mean multiplied by benchmark inference-device count",
      ...(baselineRows.length === 0 ? {
        message: "No comparable ResNet50 benchmark cohort is available for this CarbonSet processor.",
      } : {}),
      ...(baselineRows.length > 0 && results.length === 0 ? {
        message: "No benchmark system in the same cohorts has both equal-or-lower embodied carbon and higher throughput.",
      } : {}),
    },
  });
}
