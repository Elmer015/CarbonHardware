import { AppError } from "../middleware/errorHandler.js";
import { calculateOperationalCarbon, calculateOperationalEnergy } from "../services/carbon.service.js";
import { findGridIntensity } from "../services/grid-intensity.service.js";
import { findHardware } from "../services/hardware.service.js";
import { calculateStec, predictEmbodied } from "../services/python.service.js";
import { calculateCci } from "../services/metrics.service.js";

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

export function operationalCarbon(request, response) {
  const energy = calculateOperationalEnergy(request.body);
  const year = number(request.body.analysisYear, "analysisYear", { integer: true });
  const grid = findGridIntensity(request.app.locals.gridIntensity, required(request.body.region, "region"), year);
  response.json({
    ...calculateOperationalCarbon({ electricityKwh: energy.electricityKwh, gridIntensityKgCo2ePerKwh: grid.kgCo2ePerKwh }),
    energy,
    gridIntensity: grid,
    analysisYear: year,
  });
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
  const body = request.body;
  let processor;
  let dieAreaMm2;
  let processNodeNm;
  if (body.inputMode === "existing") {
    processor = findHardware(request.app.locals.hardware, required(body.processorName, "processorName"));
    if (!processor) throw new AppError(404, "Processor not found in CarbonSet");
    dieAreaMm2 = number(body.dieAreaMm2 ?? processor.dieSizeValue ?? processor.dieSizeMm2, "dieAreaMm2");
    processNodeNm = required(body.processNodeNm ?? processor.processSizeNm, "processNodeNm");
  } else if (body.inputMode === "custom") {
    processor = { name: required(body.processorName, "processorName") };
    dieAreaMm2 = number(body.dieAreaMm2, "dieAreaMm2");
    processNodeNm = required(body.processNodeNm, "processNodeNm");
  } else {
    throw new AppError(400, "inputMode must be existing or custom");
  }
  const manufacturingYear = number(body.manufacturingYear, "manufacturingYear", { integer: true });
  const manufacturingRegion = required(body.manufacturingRegion, "manufacturingRegion");
  const gridIntensity = findGridIntensity(request.app.locals.gridIntensity, manufacturingRegion, manufacturingYear);
  const result = await calculateStec({
    die_area_mm2: dieAreaMm2,
    node_nm: processNodeNm,
    grid_intensity_g_co2e_per_kwh: gridIntensity.gramsCo2ePerKwh,
    manufacturing_region: manufacturingRegion,
    manufacturing_year: manufacturingYear,
    source: body.source || "CarbonHardware API",
  });
  response.json({ value: result.stecKgCo2e, unit: "kg_co2e", valueKind: "estimated_location_based_die_stec", boundary: "cradle-to-gate die manufacturing", functionalUnit: "one chip", gridIntensity, processor, ...result });
}

export function cciEstimate(request, response) {
  response.json(calculateCci(request.body));
}