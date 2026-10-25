import { AppError } from "../middleware/errorHandler.js";
import { calculateOperationalEnergy } from "../services/carbon.service.js";
import { findHardware } from "../services/hardware.service.js";
import { calculateStec, predictEmbodied } from "../services/python.service.js";
import { calculateCci, summarizeUncertainty } from "../services/metrics.service.js";

function required(value, field) {
  if (value === undefined || value === null || value === "") throw new AppError(400, `${field} is required`);
  return value;
}

function number(value, field, { integer = false } = {}) {
  const parsed = Number(required(value, field));
  if (!Number.isFinite(parsed) || parsed < 0 || (integer && !Number.isInteger(parsed))) {
    throw new AppError(400, `${field} must be a finite non-negative${integer ? " integer" : ""}`);
  }
  return parsed;
}

function hardwareInput(body, hardware) {
  if (body.inputMode === "existing") {
    const processor = findHardware(hardware, required(body.processorName, "processorName"));
    if (!processor) throw new AppError(404, "Processor not found in CarbonSet");
    return processor;
  }
  if (body.inputMode !== "custom") throw new AppError(400, "inputMode must be existing or custom");
  return {
    name: required(body.processorName, "processorName"),
    processSizeNm: number(body.processSizeNm, "processSizeNm"),
    tdpW: number(body.tdpW, "tdpW"),
    dieSizeMm2: number(body.dieSizeMm2, "dieSizeMm2"),
    dies: number(body.dies ?? 1, "dies", { integer: true }),
    avgDieAreaMm2: number(body.avgDieAreaMm2 ?? body.dieSizeMm2, "avgDieAreaMm2"),
  };
}

export function operationalEnergy(request, response) {
  response.json({ ...calculateOperationalEnergy(request.body), valueKind: "electricity_estimate" });
}

export async function embodiedEstimate(request, response) {
  const processor = hardwareInput(request.body, request.app.locals.hardware);
  const result = await predictEmbodied({
    features: {
      "Process Size (nm)": processor.processSizeNm,
      "TDP (W)": processor.tdpW,
      DieSizeValue: processor.dieSizeValue ?? processor.dieSizeMm2,
      "#dies": processor.dies,
      "Avg Die Area": processor.avgDieAreaMm2,
    },
  });
  response.json({ status: "complete", ...result, processor });
}

export async function stecEstimate(request, response) {
  const processor = hardwareInput(request.body, request.app.locals.hardware);
  const result = await calculateStec({
    die_area_mm2: number(request.body.dieAreaMm2 ?? processor.dieSizeValue ?? processor.dieSizeMm2, "dieAreaMm2"),
    node_nm: required(request.body.processNodeNm ?? processor.processSizeNm, "processNodeNm"),
    grid_intensity_g_co2e_per_kwh: number(request.body.gridIntensityGCo2ePerKwh, "gridIntensityGCo2ePerKwh"),
    manufacturing_region: required(request.body.manufacturingRegion, "manufacturingRegion"),
    manufacturing_year: number(request.body.manufacturingYear, "manufacturingYear", { integer: true }),
    yield_factor: request.body.yieldFactor === undefined ? null : number(request.body.yieldFactor, "yieldFactor"),
    source: request.body.source || "CarbonHardware API",
  });
  response.json({ value: result.stecKgCo2e, unit: "kg_co2e", valueKind: "estimated_location_based_die_stec", boundary: "cradle-to-gate die manufacturing", functionalUnit: "one chip", ...result });
}

export function cciEstimate(request, response) {
  response.json(calculateCci(request.body));
}

export function uncertaintyEstimate(request, response) {
  response.json(summarizeUncertainty(request.body));
}