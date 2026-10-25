import test from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { createApp } from "../src/app.js";

const hardware = [{
  name: "Test CPU",
  type: "CPU",
  vendor: "Test",
  processSizeNm: 28,
  tdpW: 100,
  dieSizeValue: 100,
  dieSizeMm2: "100",
  dies: 1,
  avgDieAreaMm2: 100,
  carbonSet: {
    embodiedMinKgCo2e: 1,
    embodiedMeanKgCo2e: 2,
    embodiedMaxKgCo2e: 3,
  },
}];

test("hardware and metric endpoints validate requests", async () => {
  const server = createServer(createApp(hardware));
  await new Promise((resolve) => server.listen(0, resolve));
  const { port } = server.address();
  const url = `http://127.0.0.1:${port}`;
  try {
    const processors = await fetch(`${url}/api/hardware/processors`);
    assert.equal(processors.status, 200);
    assert.equal((await processors.json()).length, 1);

    const cci = await fetch(`${url}/api/estimates/cci`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        totalCarbonKgCo2e: 20,
        completedComputeWork: 4,
        workloadUnit: "training run",
        lifecycleBoundary: "embodied",
        analysisPeriod: "2025",
      }),
    });
    assert.equal(cci.status, 200);
    assert.equal((await cci.json()).cciKgCo2ePerWorkload, 5);

    const invalid = await fetch(`${url}/api/estimates/cci`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ totalCarbonKgCo2e: 20, completedComputeWork: 0 }),
    });
    assert.equal(invalid.status, 400);
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
});
