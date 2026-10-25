import { Router } from "express";
import { embodiedEstimate, operationalEnergy, operationalCarbon, stecEstimate, cciEstimate, uncertaintyEstimate } from "../controllers/estimate.controller.js";

const router = Router();
router.post("/embodied", embodiedEstimate);
router.post("/operational-energy", operationalEnergy);
router.post("/operational-carbon", operationalCarbon);
router.post("/stec", stecEstimate);
router.post("/cci", cciEstimate);
router.post("/uncertainty", uncertaintyEstimate);
export default router;