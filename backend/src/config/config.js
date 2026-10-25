import path from "node:path";

export const config = {
  port: Number(process.env.PORT || 3000),
  carbonSetPath: path.resolve(process.cwd(), process.env.CARBONSET_PATH || "../data/raw/carbonset/CarbonSet.csv"),
  pythonCommand: process.env.PYTHON_COMMAND || "python",
  pythonEnginePath: path.resolve(process.cwd(), "../ml-engine/carbon"),
  embodiedModelPath: path.resolve(process.cwd(), "../ml-engine/artifacts/embodied_carbon_model.joblib"),
};
