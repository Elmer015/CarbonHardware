import express from "express";
import cors from "cors";
import hardwareRoutes from "./routes/hardware.routes.js";
import estimateRoutes from "./routes/estimate.routes.js";
import gridRoutes from "./routes/grid.routes.js";
import { errorHandler, notFoundHandler } from "./middleware/errorHandler.js";

export function createApp(hardware = [], gridIntensity = []) {
  const app = express();
  app.locals.hardware = hardware;
  app.locals.gridIntensity = gridIntensity;
  app.use(cors());
  app.use(express.json({ limit: "100kb" }));
  app.get("/", (_request, response) => response.json({
    service: "carbon-hardware-backend",
    status: "ok",
    endpoints: {
      health: "GET /health",
      processors: "GET /api/hardware/processors",
      embodiedEstimate: "POST /api/estimates/embodied",
      operationalEnergy: "POST /api/estimates/operational-energy",
      operationalCarbon: "POST /api/estimates/operational-carbon",
      gridIntensity: "GET /api/grid-intensity?region=Indonesia&year=2020",
      stecEstimate: "POST /api/estimates/stec",
      cci: "POST /api/estimates/cci",
    },
  }));
  app.get("/health", (_request, response) => response.json({ status: "ok", service: "carbon-hardware-backend" }));
  app.use("/api/hardware", hardwareRoutes);
  app.use("/api/grid-intensity", gridRoutes);
  app.use("/api/estimates", estimateRoutes);
  app.use(notFoundHandler);
  app.use(errorHandler);
  return app;
}