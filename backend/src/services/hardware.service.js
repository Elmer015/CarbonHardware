import fs from "node:fs/promises";
import { AppError } from "../middleware/errorHandler.js";

const columns = ["name", "type", "releaseDate", "processSizeNm", "tdpW", "dieSizeValue", "dieSizeMm2", "vendor", "dies", "avgDieAreaMm2", "embodiedMin", "operationalMin", "totalMin", "embodiedMax", "operationalMax", "totalMax", "embodiedMean", "operationalMean", "totalMean"];

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

function numeric(value, field) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) throw new AppError(500, `Invalid numeric value in CarbonSet: ${field}`);
  return parsed;
}

function toHardware(values) {
  const row = Object.fromEntries(columns.map((column, index) => [column, values[index]]));
  return {
    name: row.name, type: row.type, releaseDate: row.releaseDate,
    processSizeNm: numeric(row.processSizeNm, "Process Size (nm)"), tdpW: numeric(row.tdpW, "TDP (W)"),
    dieSizeValue: numeric(row.dieSizeValue, "DieSizeValue"), dieSizeMm2: row.dieSizeMm2, vendor: row.vendor,
    dies: numeric(row.dies, "#dies"), avgDieAreaMm2: numeric(row.avgDieAreaMm2, "Avg Die Area"),
    carbonSet: { embodiedMinKgCo2e: numeric(row.embodiedMin, "Emb_Carbon_Min"), embodiedMaxKgCo2e: numeric(row.embodiedMax, "Emb_Carbon_Max"), embodiedMeanKgCo2e: numeric(row.embodiedMean, "Emb_Carbon_Mean") },
  };
}

export async function loadHardware(filePath) {
  const content = await fs.readFile(filePath, "utf8");
  const seen = new Set();
  return content.split(/\r?\n/).filter(Boolean).slice(1).map(parseCsvLine).map(toHardware).filter((item) => {
    if (seen.has(item.name)) return false;
    seen.add(item.name);
    return true;
  });
}

export function findHardware(hardware, name) {
  return hardware.find((item) => item.name === name);
}
