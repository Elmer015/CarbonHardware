import { AppError } from "../middleware/errorHandler.js";
import { buildComparisonRows } from "../services/comparison.service.js";

export async function getProcessorComparison(request, response) {
  const app = request.app;
  if (!app.locals.comparisonDataPromise) {
    const promise = app.locals.predictEmbodiedBatch(app.locals.hardware.map((processor) => ({
      name: processor.name,
      features: {
        "Process Size (nm)": processor.processSizeNm,
        "TDP (W)": processor.tdpW,
        DieSizeValue: processor.dieSizeValue ?? processor.dieSizeMm2,
        "#dies": processor.dies,
        "Avg Die Area": processor.avgDieAreaMm2,
      },
    })))
      .then((predictions) => buildComparisonRows(app.locals.hardware, app.locals.stecResults, predictions));
    app.locals.comparisonDataPromise = promise;
    promise.catch(() => {
      if (app.locals.comparisonDataPromise === promise) app.locals.comparisonDataPromise = null;
    });
  }

  const results = await app.locals.comparisonDataPromise;
  if (!results.length) throw new AppError(503, "No processor data is available for comparison");
  response.json({
    results,
    metadata: {
      baseline: "Experimental embodied-carbon model prediction",
      stec: "Location-based die-manufacturing estimate",
      valuesAreAdditive: false,
    },
  });
}