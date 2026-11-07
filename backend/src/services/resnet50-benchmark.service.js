import fs from "node:fs/promises";
import { AppError } from "../middleware/errorHandler.js";
import { parseCsvLine } from "./hardware.service.js";

function parseCsv(content) {
  const rows = [];
  let row = [];
  let value = "";
  let quoted = false;

  for (let index = 0; index < content.length; index += 1) {
    const character = content[index];
    if (character === "\"") {
      if (quoted && content[index + 1] === "\"") {
        value += "\"";
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (character === "," && !quoted) {
      row.push(value);
      value = "";
    } else if ((character === "\n" || character === "\r") && !quoted) {
      if (character === "\r" && content[index + 1] === "\n") index += 1;
      row.push(value);
      if (row.some((cell) => cell !== "")) rows.push(row);
      row = [];
      value = "";
    } else {
      value += character;
    }
  }

  if (quoted) throw new AppError(500, "Unterminated quoted field in ResNet50 benchmark CSV");
  if (value !== "" || row.length) {
    row.push(value);
    if (row.some((cell) => cell !== "")) rows.push(row);
  }
  return rows;
}

function optionalNumber(value, field, benchmarkId) {
  if (value === "") return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new AppError(500, `Invalid ${field} in ResNet50 benchmark ${benchmarkId}`);
  }
  return parsed;
}

export async function loadResnet50BenchmarkDataset(filePath, carbonSetPath) {
  const [content, carbonSetContent] = await Promise.all([
    fs.readFile(filePath, "utf8"),
    fs.readFile(carbonSetPath, "utf8"),
  ]);
  const carbonSetRows = carbonSetContent.replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .filter(Boolean)
    .map(parseCsvLine);
  const carbonSetHeaders = carbonSetRows.shift();
  if (!carbonSetHeaders?.length) throw new AppError(500, "CarbonSet CSV has no header");
  const carbonSetIndexes = Object.fromEntries(
    ["Product", "Emb_Carbon_Mean", "Emb_Carbon_Min", "Emb_Carbon_Max"]
      .map((header) => [header, carbonSetHeaders.indexOf(header)]),
  );
  const missingCarbonSetHeaders = Object.entries(carbonSetIndexes)
    .filter(([, index]) => index < 0)
    .map(([header]) => header);
  if (missingCarbonSetHeaders.length) {
    throw new AppError(500, `CarbonSet is missing columns: ${missingCarbonSetHeaders.join(", ")}`);
  }
  const carbonByProduct = new Map();
  for (const values of carbonSetRows) {
    const product = values[carbonSetIndexes.Product];
    if (!carbonByProduct.has(product)) {
      carbonByProduct.set(product, {
        mean: Number(values[carbonSetIndexes.Emb_Carbon_Mean]),
        min: Number(values[carbonSetIndexes.Emb_Carbon_Min]),
        max: Number(values[carbonSetIndexes.Emb_Carbon_Max]),
      });
    }
  }

  const [headers, ...records] = parseCsv(content.replace(/^\uFEFF/, ""));
  if (!headers?.length) throw new AppError(500, "ResNet50 benchmark CSV has no header");

  const requiredHeaders = [
    "benchmark_id",
    "comparison_group",
    "carbonset_product",
    "throughput_samples_per_s",
  ];
  const missingHeaders = requiredHeaders.filter((header) => !headers.includes(header));
  if (missingHeaders.length) {
    throw new AppError(500, `ResNet50 benchmark CSV is missing columns: ${missingHeaders.join(", ")}`);
  }

  const seen = new Set();
  const results = records.map((values) => {
    if (values.length !== headers.length) {
      throw new AppError(500, "ResNet50 benchmark CSV contains a row with an invalid column count");
    }
    const row = Object.fromEntries(headers.map((header, index) => [header, values[index]]));
    const benchmarkId = row.benchmark_id;
    if (!benchmarkId || seen.has(benchmarkId)) {
      throw new AppError(500, `Missing or duplicate ResNet50 benchmark ID: ${benchmarkId || "(empty)"}`);
    }
    seen.add(benchmarkId);
    if (!row.carbonset_product) {
      throw new AppError(500, `ResNet50 benchmark ${benchmarkId} has no CarbonSet product mapping`);
    }
    const embodiedCarbon = carbonByProduct.get(row.carbonset_product);
    if (!embodiedCarbon
      || !Number.isFinite(embodiedCarbon.mean)
      || !Number.isFinite(embodiedCarbon.min)
      || !Number.isFinite(embodiedCarbon.max)) {
      throw new AppError(500, `CarbonSet embodied-carbon data is unavailable for ${row.carbonset_product}`);
    }

    const result = {
      benchmarkId,
      suiteVersion: row.suite_version,
      submitter: row.submitter,
      systemName: row.system_name,
      systemType: row.system_type,
      configClass: row.config_class,
      inputDataTypes: row.input_data_types,
      comparisonGroup: row.comparison_group,
      recommendationEligible: false,
      inferenceDevice: row.inference_device,
      product: row.carbonset_product,
      deviceType: row.inference_device_type,
      deviceCount: optionalNumber(row.device_count, "device_count", benchmarkId),
      embodiedCarbonPerDeviceMeanKg: embodiedCarbon.mean,
      embodiedCarbonPerDeviceMinKg: embodiedCarbon.min,
      embodiedCarbonPerDeviceMaxKg: embodiedCarbon.max,
      systemEmbodiedCarbonMeanKg: embodiedCarbon.mean * Number(row.device_count),
      systemEmbodiedCarbonMinKg: embodiedCarbon.min * Number(row.device_count),
      systemEmbodiedCarbonMaxKg: embodiedCarbon.max * Number(row.device_count),
      hostProcessor: row.host_processor_model_name,
      accuracyTop1Pct: optionalNumber(row.accuracy_top1_pct, "accuracy_top1_pct", benchmarkId),
      throughputSamplesPerS: optionalNumber(row.throughput_samples_per_s, "throughput_samples_per_s", benchmarkId),
      sourceUrl: row.source_url,
    };

    if (!(result.deviceCount > 0) || !Number.isInteger(result.deviceCount)) {
      throw new AppError(500, `Invalid device_count in ResNet50 benchmark ${benchmarkId}`);
    }
    if (!(result.throughputSamplesPerS > 0)) {
      throw new AppError(500, `Invalid throughput in ResNet50 benchmark ${benchmarkId}`);
    }
    return result;
  });

  const productsByGroup = new Map();
  for (const row of results) {
    if (!productsByGroup.has(row.comparisonGroup)) productsByGroup.set(row.comparisonGroup, new Set());
    productsByGroup.get(row.comparisonGroup).add(row.product);
  }
  for (const row of results) {
    row.recommendationEligible = productsByGroup.get(row.comparisonGroup).size > 1;
  }
  return results;
}
