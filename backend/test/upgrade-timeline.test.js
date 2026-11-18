import test from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { createApp } from "../src/app.js";

const hardware = [
];
const gridIntensity = [{
  region: "Indonesia",
  code: "IDN",
  year: 2020,
  gramsCo2ePerKwh: 500,
  kgCo2ePerKwh: 0.5,
}];

async function withServer(run) {
  const server = createServer(createApp(hardware, gridIntensity));
  await new Promise((resolve) => server.listen(0, resolve));
  const { port } = server.address();
  try {
    await run(`http://127.0.0.1:${port}`);
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
}

test("upgrade timeline estimates years until the user carbon budget is reached", async () => {
  await withServer(async (url) => {
    const response = await fetch(`${url}/api/estimates/upgrade-timeline`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        carbonBudgetKgCo2e: 500,
        embodiedCarbonKgCo2e: 5,
        tdpW: 100,
        hoursPerDay: 1,
        usageYears: 1,
        utilization: 1,
        daysPerYear: 365,
        region: "Indonesia",
        analysisYear: 2020,
      }),
    });
    assert.equal(response.status, 200);
    const result = await response.json();
    assert.equal(result.carbonBudgetKgCo2e, 500);
    assert.ok(Math.abs(result.annualOperationalCarbonKgCo2e - 18.25) < 1e-10);
    assert.ok(Math.abs(result.yearsToBudget - (500 - 23.25) / 18.25) < 1e-10);
    assert.equal(result.status, "estimated");
  });
});

test("upgrade timeline reports a reached budget and zero-emission scenarios explicitly", async () => {
  await withServer(async (url) => {
    const basePayload = {
      carbonBudgetKgCo2e: 200,
      embodiedCarbonKgCo2e: 300,
      tdpW: 0,
      hoursPerDay: 8,
      usageYears: 5,
      utilization: 0.7,
      daysPerYear: 365,
      region: "Indonesia",
      analysisYear: 2020,
    };
    const reached = await fetch(`${url}/api/estimates/upgrade-timeline`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(basePayload),
    });
    assert.equal(reached.status, 200);
    const reachedResult = await reached.json();
    assert.equal(reachedResult.status, "budget_already_reached");
    assert.equal(reachedResult.yearsToBudget, 0);

    const noEmissions = await fetch(`${url}/api/estimates/upgrade-timeline`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ...basePayload, carbonBudgetKgCo2e: 500, embodiedCarbonKgCo2e: 10 }),
    });
    assert.equal(noEmissions.status, 200);
    const result = await noEmissions.json();
    assert.equal(result.status, "no_annual_operational_carbon");
    assert.equal(result.yearsToBudget, null);
  });
});

test("upgrade timeline requires a positive carbon budget", async () => {
  await withServer(async (url) => {
    const response = await fetch(`${url}/api/estimates/upgrade-timeline`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        carbonBudgetKgCo2e: 0,
        embodiedCarbonKgCo2e: 0,
        tdpW: 0,
        hoursPerDay: 0,
        usageYears: 0,
        utilization: 0,
        daysPerYear: 0,
        region: "Indonesia",
        analysisYear: 2020,
      }),
    });
    assert.equal(response.status, 400);
  });
});
