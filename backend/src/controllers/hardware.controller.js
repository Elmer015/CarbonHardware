import { AppError } from "../middleware/errorHandler.js";
import { findHardware } from "../services/hardware.service.js";

function publicHardware(processor) {
  const {
    embodiedCarbonMinKgCo2e: _embodiedCarbonMinKgCo2e,
    embodiedCarbonMeanKgCo2e: _embodiedCarbonMeanKgCo2e,
    embodiedCarbonMaxKgCo2e: _embodiedCarbonMaxKgCo2e,
    totalCarbonMinKgCo2e: _totalCarbonMinKgCo2e,
    totalCarbonMaxKgCo2e: _totalCarbonMaxKgCo2e,
    totalCarbonMeanKgCo2e: _totalCarbonMeanKgCo2e,
    ...publicFields
  } = processor;
  return publicFields;
}

export function listProcessors(request, response) {
  const query = String(request.query.search || "").toLowerCase();
  response.json(request.app.locals.hardware
    .filter((item) => !query || item.name.toLowerCase().includes(query))
    .map(publicHardware));
}

export function getProcessor(request, response) {
  const processor = findHardware(request.app.locals.hardware, request.params.name);
  if (!processor) throw new AppError(404, "Processor not found in CarbonSet");
  response.json(publicHardware(processor));
}