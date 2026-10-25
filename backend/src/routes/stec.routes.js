import { Router } from "express";
import { getStecProcessor, listStecProcessorOptions, listStecProcessors } from "../controllers/stec.controller.js";

const router = Router();
router.get("/processors", listStecProcessors);
router.get("/processors/options", listStecProcessorOptions);
router.get("/processors/:name", getStecProcessor);
export default router;
