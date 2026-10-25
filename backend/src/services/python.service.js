import { spawn } from "node:child_process";
import { config } from "../config/config.js";
import { AppError } from "../middleware/errorHandler.js";

export function calculateStec(input) {
  const script = [
    "import json, sys",
    `sys.path.insert(0, ${JSON.stringify(config.pythonEnginePath)})`,
    `sys.path.insert(0, ${JSON.stringify(config.pythonEnginePath.replace(/carbon$/, "models"))})`,
    "from stec import calculate_stec",
    "result = calculate_stec(**json.loads(sys.stdin.read()))",
    "print(json.dumps({'stecKgCo2e': result.stec_kg_co2e, 'dieAreaCm2': result.die_area_cm2, 'intensityGPerCm2': result.intensity_g_per_cm2, 'nodeNm': result.node_nm, 'ciGCo2ePerKwh': result.ci_g_co2e_per_kwh, 'manufacturingRegion': result.manufacturing_region, 'manufacturingYear': result.manufacturing_year, 'yieldFactor': result.yield_factor, 'assumptions': result.assumptions}))",
  ].join("\n");
  return new Promise((resolve, reject) => {
    const child = spawn(config.pythonCommand, ["-c", script], { cwd: config.pythonEnginePath });
    let stdout = ""; let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", (error) => reject(new AppError(503, `Python engine unavailable: ${error.message}`)));
    child.on("close", (code) => {
      if (code !== 0) return reject(new AppError(400, stderr.trim() || "STEC calculation failed"));
      try { return resolve(JSON.parse(stdout)); } catch { return reject(new AppError(502, "Python engine returned invalid JSON")); }
    });
    child.stdin.end(JSON.stringify(input));
  });
}

export function predictEmbodied(input) {
  const script = [
    "import json, sys",
    `sys.path.insert(0, ${JSON.stringify(config.pythonEnginePath)})`,
    `sys.path.insert(0, ${JSON.stringify(config.pythonEnginePath.replace(/carbon$/, "models"))})`,
    "from pathlib import Path",
    "import pandas as pd",
    "from embodied_carbon import predict_embodied_carbon",
    "payload = json.loads(sys.stdin.read())",
    "features = pd.DataFrame([payload['features']])",
    `result = predict_embodied_carbon(Path(${JSON.stringify(config.embodiedModelPath)}), features)[0]`,
    "print(json.dumps({'value': result.value, 'unit': result.unit, 'valueKind': result.value_kind, 'source': result.source, 'functionalUnit': result.functional_unit, 'boundary': result.boundary, 'metadata': result.metadata}))",
  ].join("\n");
  return runPythonJson(script, input);
}

export function predictEmbodiedBatch(processors) {
  const script = [
    "import json, sys",
    `sys.path.insert(0, ${JSON.stringify(config.pythonEnginePath)})`,
    `sys.path.insert(0, ${JSON.stringify(config.pythonEnginePath.replace(/carbon$/, "models"))})`,
    "from pathlib import Path",
    "import pandas as pd",
    "from embodied_carbon import predict_embodied_carbon",
    "payload = json.loads(sys.stdin.read())",
    "features = pd.DataFrame([item['features'] for item in payload])",
    `results = predict_embodied_carbon(Path(${JSON.stringify(config.embodiedModelPath)}), features)`,
    "print(json.dumps([{'name': item['name'], 'value': result.value, 'unit': result.unit, 'valueKind': result.value_kind, 'source': result.source, 'functionalUnit': result.functional_unit, 'boundary': result.boundary, 'metadata': result.metadata} for item, result in zip(payload, results, strict=True)]))",
  ].join("\n");
  return runPythonJson(script, processors);
}

function runPythonJson(script, input) {
  return new Promise((resolve, reject) => {
    const child = spawn(config.pythonCommand, ["-c", script], { cwd: config.pythonEnginePath });
    let stdout = ""; let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", (error) => reject(new AppError(503, `Python engine unavailable: ${error.message}`)));
    child.on("close", (code) => {
      if (code !== 0) return reject(new AppError(400, stderr.trim() || "Python calculation failed"));
      try { return resolve(JSON.parse(stdout)); } catch { return reject(new AppError(502, "Python engine returned invalid JSON")); }
    });
    child.stdin.end(JSON.stringify(input));
  });
}