import { config } from "./config/config.js";
import { createApp } from "./app.js";
import { loadHardware } from "./services/hardware.service.js";
import { loadGridIntensity } from "./services/grid-intensity.service.js";

const hardware = await loadHardware(config.carbonSetPath);
const gridIntensity = await loadGridIntensity(config.gridIntensityPath);
const app = createApp(hardware, gridIntensity);
app.listen(config.port, () => {
  console.log(`CarbonHardware backend listening on http://localhost:${config.port}`);
  console.log(`Loaded ${hardware.length} unique processors from CarbonSet`);
  console.log(`Loaded ${gridIntensity.length} grid intensity records`);
});