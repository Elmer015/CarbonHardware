import { AppError } from "../middleware/errorHandler.js";

const statuses = new Set(["point", "range", "incomplete"]);

export function listStecProcessors(request, response) {
  const search = String(request.query.search || "").trim().toLowerCase();
  const type = request.query.type === undefined ? "" : String(request.query.type).toUpperCase();
  const status = request.query.status === undefined ? "" : String(request.query.status).toLowerCase();
  const page = request.query.page === undefined ? 1 : Number(request.query.page);
  const pageSize = request.query.pageSize === undefined ? 50 : Number(request.query.pageSize);

  if (type && !["CPU", "GPU"].includes(type)) throw new AppError(400, "type must be CPU or GPU");
  if (status && !statuses.has(status)) throw new AppError(400, "status must be point, range, or incomplete");
  if (!Number.isInteger(page) || page < 1) throw new AppError(400, "page must be a positive integer");
  if (!Number.isInteger(pageSize) || pageSize < 1 || pageSize > 200) throw new AppError(400, "pageSize must be an integer between 1 and 200");

  const matching = request.app.locals.stecResults.filter((row) =>
    (!search || row.product.toLowerCase().includes(search) || row.vendor.toLowerCase().includes(search))
    && (!type || row.type.toUpperCase() === type)
    && (!status || row.status === status));
  const start = (page - 1) * pageSize;
  response.json({
    total: matching.length,
    page,
    pageSize,
    results: matching.slice(start, start + pageSize),
  });
}

export function listStecProcessorOptions(request, response) {
  const type = request.query.type === undefined ? "" : String(request.query.type).toUpperCase();
  if (type && !["CPU", "GPU"].includes(type)) throw new AppError(400, "type must be CPU or GPU");
  const options = request.app.locals.stecResults
    .filter((row) => !type || row.type.toUpperCase() === type)
    .map(({ product, type: deviceType, vendor, status }) => ({ product, type: deviceType, vendor, status }));
  response.json({ options });
}

export function getStecProcessor(request, response) {
  const product = request.app.locals.stecResults.find((row) => row.product === request.params.name);
  if (!product) throw new AppError(404, "Processor STEC result not found");
  response.json(product);
}
