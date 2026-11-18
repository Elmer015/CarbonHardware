import { useEffect, useState } from "react";
import HardwareForm from "../components/HardwareForm";
import CarbonReplacementComparison from "../components/CarbonReplacementComparison";
import "./EstimateCarbon.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

export default function EstimateCarbon() {
  const [mode, setMode] = useState("existing");
  const [processors, setProcessors] = useState([]);
  const [processorSearch, setProcessorSearch] = useState("");
  const [loadingProcessors, setLoadingProcessors] = useState(true);
  const [submitted, setSubmitted] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [replacementError, setReplacementError] = useState("");
  const [form, setForm] = useState({
    name: "",
    processorType: "CPU",
    processSize: "",
    tdp: "",
    dieSize: "",
    dies: "",
    avgDieArea: "",
    hoursPerDay: 8,
    usageYears: 5,
    utilizationPercent: 70,
    daysPerYear: 365,
    region: "Indonesia",
    analysisYear: 2020,
    completedWork: 1,
    workloadUnit: "completed workload unit",
  });

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/hardware/processors`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("CarbonSet could not be loaded");
        return response.json();
      })
      .then((items) => {
        setProcessors(items.map((item) => ({
          name: item.name,
          processorType: item.type,
          releaseDate: item.releaseDate,
          vendor: item.vendor,
          processSize: item.processSizeNm,
          tdp: item.tdpW,
          dieSize: item.dieSizeValue,
          dies: item.dies,
          avgDieArea: item.avgDieAreaMm2,
        })));
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingProcessors(false);
      });
    return () => controller.abort();
  }, []);

  async function calculate(event) {
    event.preventDefault();
    setError("");
    setReplacementError("");
    setSubmitted(true);
    const hardwarePayload = mode === "existing"
      ? { inputMode: "existing", processorName: form.name }
      : {
        inputMode: "custom",
        processorName: form.name,
        processorType: form.processorType,
        processSizeNm: Number(form.processSize),
        tdpW: Number(form.tdp),
        dieSizeMm2: Number(form.dieSize),
        dies: Number(form.dies),
        avgDieAreaMm2: Number(form.avgDieArea),
      };
    const energyPayload = {
      tdpW: Number(form.tdp),
      hoursPerDay: Number(form.hoursPerDay),
      usageYears: Number(form.usageYears),
      utilization: Number(form.utilizationPercent) / 100,
      daysPerYear: Number(form.daysPerYear),
    };
    const operationalPayload = {
      ...energyPayload,
      region: form.region,
      analysisYear: Number(form.analysisYear),
    };
    try {
      const embodiedResponse = await fetch(`${API_URL}/api/estimates/embodied`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(hardwarePayload),
      });
      if (!embodiedResponse.ok) {
        throw new Error((await embodiedResponse.json()).error || "Embodied prediction failed");
      }
      const embodied = await embodiedResponse.json();
      const operationalResponse = await fetch(`${API_URL}/api/estimates/operational-carbon`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(operationalPayload),
      });
      if (!operationalResponse.ok) {
        throw new Error((await operationalResponse.json()).error || "Operational carbon calculation failed");
      }
      const operational = await operationalResponse.json();
      const cciResponse = await fetch(`${API_URL}/api/estimates/cci`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          totalCarbonKgCo2e: embodied.value + operational.operationalCarbonKgCo2e,
          completedComputeWork: Number(form.completedWork),
          workloadUnit: form.workloadUnit,
          lifecycleBoundary: "embodied plus lifecycle operational",
          analysisPeriod: `${form.usageYears} years`,
        }),
      });
      if (!cciResponse.ok) {
        throw new Error((await cciResponse.json()).error || "CCI calculation failed");
      }
      const cci = await cciResponse.json();
      let replacementComparison = null;
      try {
        const comparisonResponse = await fetch(`${API_URL}/api/estimates/carbon-replacement-comparison`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            processorName: form.name,
            processorType: form.processorType,
            currentReleaseDate: mode === "existing"
              ? processors.find((processor) => processor.name === form.name)?.releaseDate
              : undefined,
            tdpW: Number(form.tdp),
            hoursPerDay: Number(form.hoursPerDay),
            utilization: Number(form.utilizationPercent) / 100,
            daysPerYear: Number(form.daysPerYear),
            region: form.region,
            analysisYear: Number(form.analysisYear),
          }),
        });
        if (!comparisonResponse.ok) {
          throw new Error((await comparisonResponse.json()).error || "Carbon replacement comparison could not be calculated");
        }
        replacementComparison = await comparisonResponse.json();
      } catch (comparisonError) {
        setReplacementError(comparisonError.message);
      }
      setResults({ embodied, energy: operational.energy, operational, cci, replacementComparison });
    } catch (requestError) {
      setError(requestError.message);
      setResults(null);
    }
  }

  return <div className="page">
    <header className="topbar compact">
      <div>
        <span className="eyebrow">CARBON HARDWARE / EMBODIED MODEL</span>
        <h1>Estimate processor carbon.</h1>
        <p className="lede">Choose known hardware or enter custom specifications, then describe its usage history and current operating pattern.</p>
      </div>
      <span className="page-number">01</span>
    </header>
    <div className="estimate-layout">
      <HardwareForm
        form={form}
        setForm={setForm}
        mode={mode}
        setMode={setMode}
        processors={processors}
        loadingProcessors={loadingProcessors}
        processorSearch={processorSearch}
        setProcessorSearch={setProcessorSearch}
        onSubmit={calculate}
      />
      <section className="result-column">
        <div className={`result-card ${submitted ? "has-result" : ""}`}>
          <span className="eyebrow">ESTIMATE STATUS</span>
          <div className={submitted ? "empty-result submitted" : "empty-result"}>
            {error ? "!" : results ? (results.embodied.value + results.operational.operationalCarbonKgCo2e).toFixed(2) : "—"}
          </div>
          <p>{error || (submitted
            ? "Embodied and operational carbon calculated."
            : "Submit the processor and usage scenario to calculate embodied carbon, operational carbon, energy, and CCI.")}</p>
          {results && <div className="result-meta">
            <span>Embodied<strong>{results.embodied.value.toFixed(2)} {results.embodied.unit}</strong></span>
            <span>Operational ({form.usageYears} years)<strong>{results.operational.operationalCarbonKgCo2e.toFixed(2)} kg CO₂e</strong></span>
            <span>Operational / year<strong>{results.operational.annualOperationalCarbonKgCo2e.toFixed(2)} kg CO₂e</strong></span>
            <span>Energy<strong>{results.energy.electricityKwh.toFixed(2)} kWh</strong></span>
            {results.cci && <span>CCI<strong>{results.cci.cciKgCo2ePerWorkload.toFixed(4)} kg/workload</strong></span>}
          </div>}
        </div>

        {results && <CarbonReplacementComparison comparison={results.replacementComparison} error={replacementError} />}

        <div className="assumption-card">
          <span className="eyebrow">MODEL CONTRACT</span>
          <h3>Carbon metrics</h3>
          <p>Embodied carbon is an experimental model prediction. Operational carbon uses the selected lifecycle grid intensity for {form.region} in {form.analysisYear}.</p>
          {results && <p className="warning-copy">Grid source: {results.operational.gridIntensity.metadata.source}; factor: {results.operational.gridIntensity.gramsCo2ePerKwh.toFixed(2)} gCO₂e/kWh.</p>}
        </div>
      </section>
    </div>
  </div>;
}
