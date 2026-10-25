export class AppError extends Error {
  constructor(statusCode, message, details = undefined) {
    super(message);
    this.statusCode = statusCode;
    this.details = details;
  }
}

export function notFoundHandler(_request, response) {
  response.status(404).json({ error: "Route not found" });
}

export function errorHandler(error, _request, response, _next) {
  const statusCode = Number.isInteger(error.statusCode) ? error.statusCode : 500;
  if (statusCode === 500) console.error(error);
  response.status(statusCode).json({
    error: statusCode === 500 ? "Internal server error" : error.message,
    ...(error.details ? { details: error.details } : {}),
  });
}