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
const stecResults = [{
  product: "Test CPU",
  type: "CPU",
  vendor: "Test",
  status: "range",
  stec_kg_co2e: null,
  stec_min_kg_co2e: 1,
  stec_max_kg_co2e: 2,
}];
const comparisonPredictions = [{
  name: "Test CPU",
  value: 4,
  unit: "kg_co2e",
  valueKind: "model_prediction",
  functionalUnit: "one processor over modeled lifecycle",
  boundary: "modeled lifecycle",
  metadata: { model_type: "test-model" },
}];

test("hardware and metric endpoints validate requests", async () => {
  const server = createServer(createApp(hardware, gridIntensity, stecResults, {
    predictEmbodiedBatch: async () => comparisonPredictions,
  }));
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

    const stecList = await fetch(`${url}/api/stec/processors?type=CPU&status=range&pageSize=1`);
    assert.equal(stecList.status, 200);
    const stecListResult = await stecList.json();
    assert.equal(stecListResult.total, 1);
    assert.equal(stecListResult.results[0].stec_min_kg_co2e, 1);

    const stecOptions = await fetch(`${url}/api/stec/processors/options?type=CPU`);
    assert.equal(stecOptions.status, 200);
    assert.deepEqual((await stecOptions.json()).options, [{ product: "Test CPU", type: "CPU", vendor: "Test", status: "range" }]);

    const stecProcessor = await fetch(`${url}/api/stec/processors/Test%20CPU`);
    assert.equal(stecProcessor.status, 200);
    assert.equal((await stecProcessor.json()).status, "range");

    const comparison = await fetch(`${url}/api/comparison`);
    assert.equal(comparison.status, 200);
    const comparisonData = await comparison.json();
    assert.equal(comparisonData.results.length, 1);
    assert.equal(comparisonData.results[0].baseline.value, 4);
    assert.equal(comparisonData.results[0].stec.status, "range");
    assert.equal(comparisonData.metadata.valuesAreAdditive, false);

    const invalidStecFilter = await fetch(`${url}/api/stec/processors?type=server`);
    assert.equal(invalidStecFilter.status, 400);

    const customStec = await fetch(`${url}/api/estimates/stec`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        inputMode: "custom",
        processorName: "Custom STEC test chip",
        processNodeNm: 28,
        dieAreaMm2: 100,
        manufacturingRegion: "Indonesia",
        manufacturingYear: 2020,
      }),
    });
    assert.equal(customStec.status, 200);
    const customStecResult = await customStec.json();
    assert.ok(Math.abs(customStecResult.value - 1.216635) < 1e-9);
    assert.equal(customStecResult.gridIntensity.region, "Indonesia");

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
