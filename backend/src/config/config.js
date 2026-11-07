import path from "node:path";

export const config = {
  port: Number(process.env.PORT || 3000),
  carbonSetPath: path.resolve(process.cwd(), process.env.CARBONSET_PATH || "../data/raw/carbonset/CarbonSet.csv"),
  gridIntensityPath: path.resolve(process.cwd(), process.env.GRID_INTENSITY_PATH || "../data/raw/environmental/owid-lifecycle-carbon-intensity.csv"),
  resnet50BenchmarkPath: path.resolve(process.cwd(), "../data/processed/resnet50-carbonset-benchmark.csv"),
  pythonCommand: process.env.PYTHON_COMMAND || "python",
  pythonEnginePath: path.resolve(process.cwd(), "../ml-engine/carbon"),
  embodiedModelPath: path.resolve(process.cwd(), "../ml-engine/artifacts/embodied_carbon_model.joblib"),
};
