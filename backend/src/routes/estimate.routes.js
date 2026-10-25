import { Router } from "express";
import { embodiedEstimate, operationalEnergy, stecEstimate } from "../controllers/estimate.controller.js";

const router = Router();
router.post("/embodied", embodiedEstimate);
router.post("/operational-energy", operationalEnergy);
router.post("/stec", stecEstimate);
export default router;