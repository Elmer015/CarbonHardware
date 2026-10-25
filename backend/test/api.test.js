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

async function withServer(run) {
  const server = createServer(createApp(hardware));
  await new Promise((resolve) => server.listen(0, resolve));
  try {
    await run(`http://127.0.0.1:${server.address().port}`);
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
}

function postJson(url, body) {
  return fetch(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
}

test("STEC processor endpoint requires region and year for custom processors", async () => {
  await withServer(async (url) => {
    const response = await postJson(`${url}/api/estimates/stec/processor`, {
      inputMode: "custom", processorName: "Custom", processSizeNm: 7, tdpW: 100, dieSizeMm2: 100,
    });
    assert.equal(response.status, 400);
  });
});

test("STEC processor endpoint resolves CI from evidence through Python", { skip: !process.env.PYTHON_COMMAND && "set PYTHON_COMMAND to run the Python integration test" }, async () => {
  await withServer(async (url) => {
    const regions = await fetch(`${url}/api/estimates/stec/regions`);
    assert.equal(regions.status, 200);
    assert.ok((await regions.json()).regions.some((item) => item.region === "Taiwan"));

    const response = await postJson(`${url}/api/estimates/stec/processor`, {
      inputMode: "existing", processorName: "Test CPU", manufacturingRegion: "Taiwan", manufacturingYear: 2022,
    });
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.status, "point");
    assert.equal(body.location.level, "user_input");
    assert.ok(body.stecKgCo2e > 0);
  });
});

test("lifecycle endpoint returns operational carbon, final CCI, and uncertainty", { skip: !process.env.PYTHON_COMMAND && "set PYTHON_COMMAND to run the Python integration test" }, async () => {
  await withServer(async (url) => {
    const regions = await fetch(`${url}/api/estimates/grid/regions`);
    assert.equal(regions.status, 200);
    assert.ok((await regions.json()).regions.some((item) => item.region === "Indonesia"));

    const response = await postJson(`${url}/api/estimates/lifecycle`, {
      inputMode: "existing",
      processorName: "Test CPU",
      usage: { hoursPerDay: 8, daysPerYear: 365, usageYears: 5, utilization: 0.7, usageRegion: "Indonesia", gridYear: 2024 },
      workload: { completedComputeWork: 100, workloadUnit: "compute-hour" },
      distributions: { utilization: { min: 0.4, mostLikely: 0.7, max: 0.95 } },
      samples: 1000,
    });
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.status, "complete");
    assert.ok(Math.abs(body.electricityKwh - 100 / 1000 * 8 * 365 * 5 * 0.7) < 1e-9);
    assert.ok(Math.abs(body.totalKgCo2e - (body.embodied.valueKgCo2e + body.operational.carbonKgCo2e)) < 1e-9);
    assert.equal(body.cci.status, "final");
    assert.ok(body.uncertainty.total.p2_5 < body.uncertainty.total.p97_5);

    const missingGrid = await postJson(`${url}/api/estimates/lifecycle`, {
      inputMode: "existing", processorName: "Test CPU",
      usage: { hoursPerDay: 8, daysPerYear: 365, usageYears: 5, utilization: 0.7 },
    });
    assert.equal(missingGrid.status, 200);
    assert.equal((await missingGrid.json()).status, "operational_pending_grid");
  });
});

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
