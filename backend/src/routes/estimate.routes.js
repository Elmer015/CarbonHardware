import { Router } from "express";
import { embodiedEstimate, operationalEnergy, stecEstimate, stecProcessorEstimate, stecRegions, cciEstimate, uncertaintyEstimate, lifecycleEstimate, gridRegions } from "../controllers/estimate.controller.js";

const router = Router();
router.post("/embodied", embodiedEstimate);
router.post("/operational-energy", operationalEnergy);
router.post("/stec", stecEstimate);
router.post("/stec/processor", stecProcessorEstimate);
router.get("/stec/regions", stecRegions);
router.post("/lifecycle", lifecycleEstimate);
router.get("/grid/regions", gridRegions);
router.post("/cci", cciEstimate);
router.post("/uncertainty", uncertaintyEstimate);
export default router;