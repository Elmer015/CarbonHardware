import test from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { createApp } from "../src/app.js";
import { calculateCarbonReplacementComparison } from "../src/services/carbon-replacement.service.js";

const hardware = [
  { name: "Current CPU", type: "CPU", releaseDate: "2017-01-01", tdpW: 1000, embodiedCarbonMeanKgCo2e: 20, embodiedCarbonMinKgCo2e: 10, embodiedCarbonMaxKgCo2e: 30 },
  { name: "Quick payback CPU", type: "CPU", releaseDate: "2021-01-01", tdpW: 800, embodiedCarbonMeanKgCo2e: 20, embodiedCarbonMinKgCo2e: 10, embodiedCarbonMaxKgCo2e: 30 },
  { name: "Lower power CPU", type: "CPU", releaseDate: "2022-01-01", tdpW: 500, embodiedCarbonMeanKgCo2e: 100, embodiedCarbonMinKgCo2e: 80, embodiedCarbonMaxKgCo2e: 120 },
  { name: "Third candidate CPU", type: "CPU", releaseDate: "2023-01-01", tdpW: 700, embodiedCarbonMeanKgCo2e: 100, embodiedCarbonMinKgCo2e: 80, embodiedCarbonMaxKgCo2e: 120 },
  { name: "Fourth candidate CPU", type: "CPU", releaseDate: "2023-06-01", tdpW: 600, embodiedCarbonMeanKgCo2e: 180, embodiedCarbonMinKgCo2e: 150, embodiedCarbonMaxKgCo2e: 200 },
  { name: "Too low TDP CPU", type: "CPU", releaseDate: "2024-01-01", tdpW: 400, embodiedCarbonMeanKgCo2e: 1, embodiedCarbonMinKgCo2e: 1, embodiedCarbonMaxKgCo2e: 1 },
  { name: "Older CPU", type: "CPU", releaseDate: "2018-01-01", tdpW: 800, embodiedCarbonMeanKgCo2e: 1, embodiedCarbonMinKgCo2e: 1, embodiedCarbonMaxKgCo2e: 1 },
  { name: "Different type GPU", type: "GPU", releaseDate: "2024-01-01", tdpW: 500, embodiedCarbonMeanKgCo2e: 1, embodiedCarbonMinKgCo2e: 1, embodiedCarbonMaxKgCo2e: 1 },
];

const usage = {
  currentProcessor: { name: "Current CPU", type: "CPU", tdpW: 1000 },
  candidates: hardware,
  currentReleaseDate: "2017-01-01",
  hoursPerDay: 1,
  utilization: 1,
  daysPerYear: 100,
  gridIntensityKgCo2ePerKwh: 1,
};

test("returns only newer same-type candidates in the comparable TDP range, ranked by payback", () => {
  const result = calculateCarbonReplacementComparison(usage);

  assert.equal(result.status, "estimated");
  assert.equal(result.currentAnnualOperationalCarbonKgCo2e, 100);
  assert.deepEqual(result.candidates.map((candidate) => candidate.name), ["Quick payback CPU", "Lower power CPU", "Third candidate CPU"]);
  assert.equal(result.candidates.length, 3);
  assert.equal(result.candidates[0].annualOperationalCarbonKgCo2e, 80);
  assert.equal(result.candidates[0].annualCarbonSavingsKgCo2e, 20);
  assert.equal(result.candidates[0].yearsToCarbonPayback, 1);
  assert.equal(result.metadata.minimumCandidateTdpRatio, 0.5);
  assert.equal(result.metadata.minimumCandidateReleaseYear, 2020);
  assert.equal(result.metadata.performanceEvaluated, false);
});

test("reports when no newer processor has TDP in the comparison range", () => {
  const result = calculateCarbonReplacementComparison({
    ...usage,
    candidates: hardware.filter((candidate) =>
      !["Quick payback CPU", "Lower power CPU", "Third candidate CPU", "Fourth candidate CPU"].includes(candidate.name)),
  });

  assert.equal(result.status, "no_similar_tdp_candidate");
  assert.deepEqual(result.candidates, []);
});

test("excludes newer processors outside the catalog's latest five-year release window", () => {
  const result = calculateCarbonReplacementComparison({
    ...usage,
    candidates: hardware.filter((candidate) =>
      ["Current CPU", "Older CPU", "Different type GPU"].includes(candidate.name)),
  });

  assert.equal(result.status, "no_recent_candidate");
  assert.deepEqual(result.candidates, []);
});

test("does not calculate a payback when the usage scenario produces no operational emissions", () => {
  const result = calculateCarbonReplacementComparison({
    ...usage,
    gridIntensityKgCo2ePerKwh: 0,
  });

  assert.equal(result.status, "no_operational_carbon_savings");
  assert.deepEqual(result.candidates, []);
});

test("does not compare custom hardware without a release date", () => {
  const result = calculateCarbonReplacementComparison({
    ...usage,
    currentReleaseDate: undefined,
  });

  assert.equal(result.status, "current_release_date_unavailable");
  assert.deepEqual(result.candidates, []);
});

test("carbon replacement API returns an automatic reference candidate", async () => {
  const gridIntensity = [{
    region: "Test",
    year: 2020,
    gramsCo2ePerKwh: 1000,
    kgCo2ePerKwh: 1,
  }];
  const server = createServer(createApp(hardware, gridIntensity));
  await new Promise((resolve) => server.listen(0, resolve));
  const { port } = server.address();
  try {
    const response = await fetch(`http://127.0.0.1:${port}/api/estimates/carbon-replacement-comparison`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        processorName: "Current CPU",
        processorType: "CPU",
        currentReleaseDate: "2017-01-01",
        tdpW: 1000,
        hoursPerDay: 1,
        utilization: 1,
        daysPerYear: 100,
        region: "Test",
        analysisYear: 2020,
      }),
    });

    assert.equal(response.status, 200);
    const result = await response.json();
    assert.equal(result.candidates[0].name, "Quick payback CPU");
    assert.equal(result.candidates[0].yearsToCarbonPayback, 1);
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
});
