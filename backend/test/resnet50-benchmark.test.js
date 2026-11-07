import test from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { fileURLToPath } from "node:url";
import { createApp } from "../src/app.js";
import { loadResnet50BenchmarkDataset } from "../src/services/resnet50-benchmark.service.js";

const datasetPath = fileURLToPath(new URL("../../data/processed/resnet50-carbonset-benchmark.csv", import.meta.url));
const carbonSetPath = fileURLToPath(new URL("../../data/raw/carbonset/CarbonSet.csv", import.meta.url));

test("CarbonSet-mapped ResNet50 rows join CarbonSet embodied carbon without power data", async () => {
  const rows = await loadResnet50BenchmarkDataset(datasetPath, carbonSetPath);
  assert.equal(rows.length, 38);
  assert.equal(rows.filter((row) => row.recommendationEligible).length, 20);
  assert.equal(new Set(rows.map((row) => row.product)).size, 6);
  assert.ok(rows.every((row) => row.product));
  assert.ok(rows.every((row) => row.embodiedCarbonPerDeviceMeanKg > 0));
  assert.ok(rows.every((row) => row.systemEmbodiedCarbonMeanKg === row.embodiedCarbonPerDeviceMeanKg * row.deviceCount));
  assert.ok(rows.every((row) => !("averagePowerW" in row) && !("cciGPerMillionImages" in row)));
  assert.ok(rows.filter((row) => row.product === "Intel Xeon Platinum 8592+").every((row) => !row.recommendationEligible));
  const firstGpu = rows.find((row) => row.product === "NVIDIA A100 PCIe 40 GB");
  assert.ok(Math.abs(firstGpu.embodiedCarbonPerDeviceMeanKg - 68.076154237871) < 1e-10);
  assert.ok(Math.abs(firstGpu.systemEmbodiedCarbonMeanKg - 204.228462713613) < 1e-9);
});

test("ResNet50 benchmark endpoint reports comparison scope and matched products", async () => {
  const rows = await loadResnet50BenchmarkDataset(datasetPath, carbonSetPath);
  const server = createServer(createApp([], [], [], { resnet50Benchmarks: rows }));
  await new Promise((resolve) => server.listen(0, resolve));
  const { port } = server.address();
  try {
    const response = await fetch(`http://127.0.0.1:${port}/api/benchmarks/resnet50`);
    assert.equal(response.status, 200);
    const payload = await response.json();
    assert.equal(payload.results.length, 38);
    assert.equal(payload.metadata.comparableRows, 20);
    assert.equal(payload.metadata.matchedProducts, 6);
    assert.equal(payload.metadata.notRankedRows, 18);
    assert.equal(payload.metadata.embodiedCarbonUnit, "kg CO2e per inference processor");
    assert.equal(payload.metadata.performanceUnit, "completed inference images per second for the whole benchmark system");
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
});

test("recommendations require lower-or-equal embodied carbon and higher throughput in matched cohorts", async () => {
  const rows = await loadResnet50BenchmarkDataset(datasetPath, carbonSetPath);
  const server = createServer(createApp([], [], [], { resnet50Benchmarks: rows }));
  await new Promise((resolve) => server.listen(0, resolve));
  const { port } = server.address();
  try {
    const response = await fetch(`http://127.0.0.1:${port}/api/benchmarks/resnet50/recommendations?processorName=${encodeURIComponent("NVIDIA A100 PCIe 40 GB")}`);
    assert.equal(response.status, 200);
    const payload = await response.json();
    assert.equal(payload.metadata.baselineRows, 3);
    assert.ok(payload.results.length > 0);
    for (const candidate of payload.results) {
      assert.notEqual(candidate.product, "NVIDIA A100 PCIe 40 GB");
      assert.equal(candidate.comparisonGroup, candidate.baseline.comparisonGroup);
      assert.ok(candidate.systemEmbodiedCarbonMeanKg <= candidate.baseline.systemEmbodiedCarbonMeanKg);
      assert.ok(candidate.throughputSamplesPerS > candidate.baseline.throughputSamplesPerS);
    }
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
});

test("recommendation endpoint requires the selected CarbonSet processor", async () => {
  const rows = await loadResnet50BenchmarkDataset(datasetPath, carbonSetPath);
  const server = createServer(createApp([], [], [], { resnet50Benchmarks: rows }));
  await new Promise((resolve) => server.listen(0, resolve));
  const { port } = server.address();
  try {
    const response = await fetch(`http://127.0.0.1:${port}/api/benchmarks/resnet50/recommendations`);
    assert.equal(response.status, 400);
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
});

test("recommendations explain when a processor has no comparable benchmark cohort", async () => {
  const rows = await loadResnet50BenchmarkDataset(datasetPath, carbonSetPath);
  const server = createServer(createApp([], [], [], { resnet50Benchmarks: rows }));
  await new Promise((resolve) => server.listen(0, resolve));
  const { port } = server.address();
  try {
    const response = await fetch(`http://127.0.0.1:${port}/api/benchmarks/resnet50/recommendations?processorName=${encodeURIComponent("Intel Xeon Platinum 8592+")}`);
    assert.equal(response.status, 200);
    const payload = await response.json();
    assert.equal(payload.results.length, 0);
    assert.equal(payload.metadata.baselineRows, 0);
    assert.match(payload.metadata.message, /No comparable ResNet50 benchmark cohort/);
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
});
