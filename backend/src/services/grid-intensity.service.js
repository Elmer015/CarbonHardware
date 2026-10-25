import fs from "node:fs/promises";
import { AppError } from "../middleware/errorHandler.js";

const sourceMetadata = {
  source: "Ember (2026), via Our World in Data",
  dataset: "Lifecycle carbon intensity of electricity",
  basis: "lifecycle location-based",
  originalUnit: "gCO2e/kWh",
  convertedUnit: "kgCO2e/kWh",
  conversion: "value / 1000",
  snapshot: "data/raw/environmental/owid-lifecycle-carbon-intensity.csv",
};

function parseCsvLine(line) {
  const values = [];
  let value = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    if (character === "\"") {
      if (quoted && line[index + 1] === "\"") { value += "\""; index += 1; } else quoted = !quoted;
    } else if (character === "," && !quoted) { values.push(value); value = ""; } else value += character;
  }
  values.push(value);
  return values;
}

export async function loadGridIntensity(filePath) {
  const content = await fs.readFile(filePath, "utf8");
  const lines = content.split(/\r?\n/).filter(Boolean);
  const headers = parseCsvLine(lines.shift() || "");
  const expected = ["Entity", "Code", "Year", "Carbon intensity"];
  if (!expected.every((header, index) => headers[index] === header)) {
    throw new AppError(500, "Grid intensity dataset has an unsupported schema", { expectedHeaders: expected, actualHeaders: headers });
  }
  return lines.map((line) => {
    const [region, code, yearText, intensityText] = parseCsvLine(line);
    const year = Number(yearText);
    const grams = Number(intensityText);
    if (!region || !Number.isInteger(year) || !Number.isFinite(grams) || grams < 0) {
      throw new AppError(500, "Grid intensity dataset contains an invalid row");
    }
    return { region, code: code || null, year, gramsCo2ePerKwh: grams, kgCo2ePerKwh: grams / 1000 };
  });
}

export function findGridIntensity(rows, region, year) {
  const match = rows.find((row) => row.region.toLowerCase() === String(region).trim().toLowerCase() && row.year === year);
  if (!match) {
    throw new AppError(404, `No grid intensity data for region "${region}" and year ${year}`);
  }
  return { ...match, metadata: sourceMetadata };
}

export function listGridRegions(rows) {
  return [...new Set(rows.map((row) => row.region))].sort();
}
