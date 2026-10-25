import { config } from "./config/config.js";
import { createApp } from "./app.js";
import { loadHardware } from "./services/hardware.service.js";

const hardware = await loadHardware(config.carbonSetPath);
const app = createApp(hardware);
app.listen(config.port, () => {
  console.log(`CarbonHardware backend listening on http://localhost:${config.port}`);
  console.log(`Loaded ${hardware.length} unique processors from CarbonSet`);
});