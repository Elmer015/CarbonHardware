import { useEffect, useState } from "react";
import HardwareForm from "../components/HardwareForm";
import LifecycleResult from "../components/LifecycleResult";
import StecResult from "../components/StecResult";
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

const postJson = (path, body) => fetch(`${API_URL}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

function rangeOf(min, mostLikely, max, scale = 1) {
  if (min === "" || max === "" || min === undefined || max === undefined) return undefined;
  return { min: Number(min) * scale, mostLikely: Number(mostLikely) * scale, max: Number(max) * scale };
}

export default function EstimateCarbon() {
  const [mode, setMode] = useState("existing"); const [processors, setProcessors] = useState([]); const [loadingProcessors, setLoadingProcessors] = useState(true); const [submitted, setSubmitted] = useState(false); const [results, setResults] = useState(null); const [error, setError] = useState(""); const [regions, setRegions] = useState([]); const [gridRegions, setGridRegions] = useState([]); const [stec, setStec] = useState(null); const [stecError, setStecError] = useState("");
  const [form, setForm] = useState({ name: "", processSize: "", tdp: "", dieSize: "", dies: "", avgDieArea: "", embodiedMin: "", embodiedMean: "", embodiedMax: "", hoursPerDay: 8, usageYears: 5, utilizationPercent: 70, daysPerYear: 365, completedWork: 1, workloadUnit: "completed workload unit", manufacturingRegion: "", manufacturingYear: "", usageRegion: "Indonesia", gridYear: 2024, tdpMin: "", tdpMax: "", utilizationMin: "", utilizationMax: "", gridMin: "", gridMax: "" });
  useEffect(() => { fetch(`${API_URL}/api/estimates/stec/regions`).then((response) => (response.ok ? response.json() : { regions: [] })).then((data) => setRegions(data.regions.filter((item) => item.lastYear >= 2011))).catch(() => setRegions([])); }, []);
  useEffect(() => { fetch(`${API_URL}/api/estimates/grid/regions`).then((response) => (response.ok ? response.json() : { regions: [] })).then((data) => setGridRegions(data.regions.filter((item) => item.lastYear >= 2011))).catch(() => setGridRegions([])); }, []);
  useEffect(() => { fetch(`${API_URL}/api/hardware/processors`).then((response) => { if (!response.ok) throw new Error("CarbonSet could not be loaded"); return response.json(); }).then((items) => { setProcessors(items.map((item) => ({ name: item.name, vendor: item.vendor, processSize: item.processSizeNm, tdp: item.tdpW, dieSize: item.dieSizeValue, dies: item.dies, avgDieArea: item.avgDieAreaMm2, embodiedMin: item.carbonSet.embodiedMinKgCo2e, embodiedMean: item.carbonSet.embodiedMeanKgCo2e, embodiedMax: item.carbonSet.embodiedMaxKgCo2e }))); }).catch(() => setProcessors([])).finally(() => setLoadingProcessors(false)); }, []);

  async function calculateStec(hardwarePayload) { setStec(null); setStecError(""); try { const response = await postJson("/api/estimates/stec/processor", { ...hardwarePayload, manufacturingRegion: form.manufacturingRegion || null, manufacturingYear: form.manufacturingYear === "" ? null : Number(form.manufacturingYear) }); const data = await response.json(); if (!response.ok) throw new Error(data.error || "STEC calculation failed"); setStec(data); } catch (requestError) { setStecError(requestError.message); } }

  async function calculate(event) {
    event.preventDefault(); setError(""); setSubmitted(true); setResults(null);
    const hardwarePayload = mode === "existing" ? { inputMode: "existing", processorName: form.name } : { inputMode: "custom", processorName: form.name, processSizeNm: Number(form.processSize), tdpW: Number(form.tdp), dieSizeMm2: Number(form.dieSize), dies: Number(form.dies), avgDieAreaMm2: Number(form.avgDieArea) };
    const utilization = Number(form.utilizationPercent) / 100;
    const distributions = Object.fromEntries(Object.entries({
      tdpW: rangeOf(form.tdpMin, form.tdp, form.tdpMax),
      utilization: rangeOf(form.utilizationMin, form.utilizationPercent, form.utilizationMax, 0.01),
      gridIntensityKgCo2ePerKwh: form.gridMin !== "" && form.gridMax !== "" ? { min: Number(form.gridMin), max: Number(form.gridMax) } : undefined,
    }).filter(([, value]) => value));
    calculateStec(hardwarePayload);
    try {
      const [embodiedResponse, lifecycleResponse] = await Promise.all([
        postJson("/api/estimates/embodied", hardwarePayload),
        postJson("/api/estimates/lifecycle", { ...hardwarePayload, usage: { hoursPerDay: Number(form.hoursPerDay), daysPerYear: Number(form.daysPerYear), usageYears: Number(form.usageYears), utilization, usageRegion: form.usageRegion || null, gridYear: form.gridYear === "" ? null : Number(form.gridYear) }, workload: { completedComputeWork: Number(form.completedWork), workloadUnit: form.workloadUnit }, distributions }),
      ]);
      const failed = [embodiedResponse, lifecycleResponse].find((response) => !response.ok);
      if (failed) throw new Error((await failed.json()).error || "Calculation failed");
      setResults({ embodied: await embodiedResponse.json(), lifecycle: await lifecycleResponse.json() });
    } catch (requestError) { setError(requestError.message); }
  }

  const lifecycle = results?.lifecycle;
  const status = lifecycle?.status === "complete" ? "Embodied, operational carbon, and final CCI computed." : lifecycle ? "Operational carbon pending: choose a usage country and grid year." : "Model prediction completed.";
  return <div className="page"><header className="topbar compact"><div><span className="eyebrow">CARBON HARDWARE / LIFECYCLE MODEL</span><h1>Estimate processor carbon.</h1><p className="lede">Choose known hardware or switch to custom input, then define its operational usage scenario and grid.</p></div><span className="page-number">01</span></header><div className="estimate-layout"><HardwareForm form={form} setForm={setForm} mode={mode} setMode={setMode} processors={processors} loadingProcessors={loadingProcessors} regions={regions} gridRegions={gridRegions} onSubmit={calculate} /><section className="result-column">
    <div className={`result-card ${submitted ? "has-result" : ""}`}><span className="eyebrow">ESTIMATE STATUS · TOTAL kg CO₂e</span><div className={submitted ? "empty-result submitted" : "empty-result"}>{error ? "!" : lifecycle ? (lifecycle.totalKgCo2e ?? lifecycle.embodied.valueKgCo2e).toFixed(2) : "—"}</div><p>{error || (submitted ? (lifecycle ? status : "Calculating…") : "Submit the processor and usage scenario to calculate embodied, operational, and total carbon with uncertainty and CCI.")}</p>{results && <div className="result-meta"><span>Embodied (model)<strong>{results.embodied.value.toFixed(2)} {results.embodied.unit}</strong></span><span>Energy<strong>{lifecycle.electricityKwh.toFixed(1)} kWh</strong></span>{lifecycle.operational && <span>Operational<strong>{lifecycle.operational.carbonKgCo2e.toFixed(2)} kg</strong></span>}{lifecycle.cci && <span>CCI ({lifecycle.cci.status === "final" ? "final" : "embodied only"})<strong>{lifecycle.cci.cciKgCo2ePerWorkload.toFixed(4)} kg/{lifecycle.cci.workloadUnit}</strong></span>}</div>}</div>
    <LifecycleResult lifecycle={lifecycle} />
    <StecResult stec={stec} error={stecError} />
    <div className="assumption-card"><span className="eyebrow">MODEL CONTRACT</span><h3>Carbon metrics</h3><p>Embodied carbon is an experimental model prediction. Its range comes from CarbonSet min/max for existing processors and from the model's out-of-fold error (90% empirical interval) for custom processors.</p><p>Operational carbon = electricity × location-based grid intensity of the chosen country and year (Our World in Data / Ember). Final CCI = (embodied + operational) ÷ completed workload.</p><p className="warning-copy">Uncertainty bands come from Monte Carlo propagation of the ranges you supply; they are not calibrated confidence intervals.</p></div>
    <div className="feature-note"><span className="eyebrow">CCI DEFINITION</span><p>CCI unit: <strong>kg CO₂e per {form.workloadUnit}</strong>. Comparisons are valid only for the same workload definition, boundary, and analysis period.</p></div>
  </section></div></div>;
}
