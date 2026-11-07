import { config } from "./config/config.js";
import { createApp } from "./app.js";
import { loadHardware } from "./services/hardware.service.js";
import { loadGridIntensity } from "./services/grid-intensity.service.js";
import { loadStecDataset } from "./services/stec-dataset.service.js";
import { loadResnet50BenchmarkDataset } from "./services/resnet50-benchmark.service.js";

const hardware = await loadHardware(config.carbonSetPath);
const gridIntensity = await loadGridIntensity(config.gridIntensityPath);
const stecResults = await loadStecDataset();
const resnet50Benchmarks = await loadResnet50BenchmarkDataset(config.resnet50BenchmarkPath, config.carbonSetPath);
const app = createApp(hardware, gridIntensity, stecResults, { resnet50Benchmarks });
app.listen(config.port, () => {
  console.log(`CarbonHardware backend listening on http://localhost:${config.port}`);
  console.log(`Loaded ${hardware.length} unique processors from CarbonSet`);
  console.log(`Loaded ${gridIntensity.length} grid intensity records`);
  console.log(`Calculated STEC for ${stecResults.length} processors`);
  console.log(`Loaded ${resnet50Benchmarks.length} CarbonSet-mapped ResNet50 benchmark rows`);
});