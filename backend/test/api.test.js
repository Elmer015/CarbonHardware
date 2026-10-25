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
}];
const gridIntensity = [{
  region: "Indonesia",
  code: "IDN",
  year: 2020,
  gramsCo2ePerKwh: 685.15,
  kgCo2ePerKwh: 0.68515,
}];

test("hardware and metric endpoints validate requests", async () => {
  const server = createServer(createApp(hardware, gridIntensity));
  await new Promise((resolve) => server.listen(0, resolve));
  const { port } = server.address();
  const url = `http://127.0.0.1:${port}`;
  try {
    const processors = await fetch(`${url}/api/hardware/processors`);
    assert.equal(processors.status, 200);
    const processorList = await processors.json();
    assert.equal(processorList.length, 1);
    assert.equal("carbonSet" in processorList[0], false);

    const grid = await fetch(`${url}/api/grid-intensity?region=Indonesia&year=2020`);
    assert.equal(grid.status, 200);
    assert.equal((await grid.json()).kgCo2ePerKwh, 0.68515);

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

    const operationalCarbon = await fetch(`${url}/api/estimates/operational-carbon`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        tdpW: 180,
        hoursPerDay: 8,
        usageYears: 5,
        utilization: 0.7,
        daysPerYear: 365,
        region: "Indonesia",
        analysisYear: 2020,
      }),
    });
    assert.equal(operationalCarbon.status, 200);
    const operationalResult = await operationalCarbon.json();
    assert.equal(operationalResult.energy.electricityKwh, 1839.6);
    assert.equal(operationalResult.operationalCarbonKgCo2e, 1260.40194);

    const unavailable = await fetch(`${url}/api/estimates/operational-carbon`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ tdpW: 180, hoursPerDay: 8, usageYears: 5, utilization: 0.7, daysPerYear: 365, region: "Indonesia", analysisYear: 2025 }),
    });
    assert.equal(unavailable.status, 404);

    for (const endpoint of ["/uncertainty", "/uncertainty/total", "/uncertainty/custom"]) {
      const response = await fetch(`${url}/api/estimates${endpoint}`, { method: "POST" });
      assert.equal(response.status, 404);
    }
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
});
