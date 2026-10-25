import { AppError } from "../middleware/errorHandler.js";
import { findHardware } from "../services/hardware.service.js";

export function listProcessors(request, response) {
  const query = String(request.query.search || "").toLowerCase();
  response.json(request.app.locals.hardware.filter((item) => !query || item.name.toLowerCase().includes(query)));
}

export function getProcessor(request, response) {
  const processor = findHardware(request.app.locals.hardware, request.params.name);
  if (!processor) throw new AppError(404, "Processor not found in CarbonSet");
  response.json(processor);
}