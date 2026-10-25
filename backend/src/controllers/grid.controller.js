import { AppError } from "../middleware/errorHandler.js";
import { findGridIntensity, listGridRegions } from "../services/grid-intensity.service.js";

export function gridIntensityLookup(request, response) {
  const region = request.query.region;
  const year = Number(request.query.year);
  if (!region) throw new AppError(400, "region is required");
  if (!Number.isInteger(year) || year < 1900) throw new AppError(400, "year must be an integer");
  response.json(findGridIntensity(request.app.locals.gridIntensity, region, year));
}

export function gridIntensityRegions(request, response) {
  response.json({ regions: listGridRegions(request.app.locals.gridIntensity) });
}
