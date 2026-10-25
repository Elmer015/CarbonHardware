import { spawn } from "node:child_process";
import path from "node:path";
import { config } from "../config/config.js";
import { AppError } from "../middleware/errorHandler.js";

export function loadStecDataset() {
  const scriptPath = path.join(config.pythonEnginePath, "stec_batch.py");
  const repositoryRoot = path.resolve(config.pythonEnginePath, "..", "..");
  return new Promise((resolve, reject) => {
    const child = spawn(config.pythonCommand, [scriptPath, "--json"], { cwd: repositoryRoot });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", (error) => reject(new AppError(503, `Python STEC batch unavailable: ${error.message}`)));
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new AppError(500, stderr.trim() || "STEC batch calculation failed"));
        return;
      }
      try {
        const rows = JSON.parse(stdout);
        if (!Array.isArray(rows)) throw new Error("STEC batch output must be an array");
        resolve(rows);
      } catch (error) {
        reject(new AppError(502, `Python STEC batch returned invalid JSON: ${error.message}`));
      }
    });
  });
}
