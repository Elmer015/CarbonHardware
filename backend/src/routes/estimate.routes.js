import { Router } from "express";
import { embodiedEstimate, operationalEnergy, operationalCarbon, carbonReplacementComparison, upgradeTimelineEstimate, stecEstimate, cciEstimate } from "../controllers/estimate.controller.js";

const router = Router();
router.post("/embodied", embodiedEstimate);
router.post("/operational-energy", operationalEnergy);
router.post("/operational-carbon", operationalCarbon);
router.post("/carbon-replacement-comparison", carbonReplacementComparison);
router.post("/upgrade-timeline", upgradeTimelineEstimate);
router.post("/stec", stecEstimate);
router.post("/cci", cciEstimate);
export default router;