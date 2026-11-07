import { Router } from "express";
import { getResnet50Benchmarks, getResnet50Recommendations } from "../controllers/resnet50-benchmark.controller.js";

const router = Router();
router.get("/resnet50/recommendations", getResnet50Recommendations);
router.get("/resnet50", getResnet50Benchmarks);
export default router;
