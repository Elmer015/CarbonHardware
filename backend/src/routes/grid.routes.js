import { Router } from "express";
import { gridIntensityLookup, gridIntensityRegions } from "../controllers/grid.controller.js";

const router = Router();
router.get("/", gridIntensityLookup);
router.get("/regions", gridIntensityRegions);
export default router;
