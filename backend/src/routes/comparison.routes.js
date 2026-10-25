import { Router } from "express";
import { getProcessorComparison } from "../controllers/comparison.controller.js";

const router = Router();
router.get("/", getProcessorComparison);
export default router;