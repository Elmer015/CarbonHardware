import { Router } from "express";
import { getProcessor, listProcessors } from "../controllers/hardware.controller.js";

const router = Router();
router.get("/processors", listProcessors);
router.get("/processors/:name", getProcessor);
export default router;