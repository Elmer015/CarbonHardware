import { AppError } from "../middleware/errorHandler.js";

export function buildComparisonRows(hardware, stecResults, predictions) {
  if (!Array.isArray(predictions) || predictions.length !== hardware.length) {
    throw new AppError(502, "Embodied model returned an incomplete processor comparison");
  }

  const predictionsByName = new Map(predictions.map((prediction) => [prediction.name, prediction]));
  const stecByName = new Map(stecResults.map((result) => [result.product, result]));

  return hardware.map((processor) => {
    const baseline = predictionsByName.get(processor.name);
    if (!baseline || !Number.isFinite(baseline.value)) {
      throw new AppError(502, `Embodied model prediction is missing for ${processor.name}`);
    }
    const stec = stecByName.get(processor.name);

    return {
      name: processor.name,
      type: processor.type,
      vendor: processor.vendor,
      baseline: {
        value: baseline.value,
        unit: baseline.unit,
        valueKind: baseline.valueKind,
        functionalUnit: baseline.functionalUnit,
        boundary: baseline.boundary,
        metadata: baseline.metadata,
      },
      stec: stec ? {
        status: stec.status,
        value: stec.stec_kg_co2e,
        min: stec.stec_min_kg_co2e,
        max: stec.stec_max_kg_co2e,
        unit: "kg_co2e",
        boundary: "cradle-to-gate die manufacturing",
        nodeNm: stec.node_nm,
        candidateRegions: stec.candidate_regions,
        locationConfidence: stec.location_confidence,
        warnings: stec.warnings,
      } : {
        status: "unavailable",
        value: null,
        min: null,
        max: null,
        unit: "kg_co2e",
        boundary: "cradle-to-gate die manufacturing",
      },
    };
  });
}
