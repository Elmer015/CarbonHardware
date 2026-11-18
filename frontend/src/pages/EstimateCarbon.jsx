import { useEffect, useState } from "react";
import HardwareForm from "../components/HardwareForm";
import CarbonReplacementComparison from "../components/CarbonReplacementComparison";
import "./EstimateCarbon.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

function formatRange(minimum, maximum, unit, digits = 2) {
  const low = Number(minimum);
  const high = Number(maximum);
  if (!Number.isFinite(low) || !Number.isFinite(high)) return "Not available";
  const value = low === high ? low.toFixed(digits) : `${low.toFixed(digits)}–${high.toFixed(digits)}`;
  return `${value} ${unit}`;
}

function getStecScenarioTotals(stec, operationalCarbonKgCo2e) {
  if (!stec || !["point", "range"].includes(stec.status)) return null;
  const minimumStec = Number(stec.status === "point" ? stec.value : stec.min);
  const maximumStec = Number(stec.status === "point" ? stec.value : stec.max);
  const operationalCarbon = Number(operationalCarbonKgCo2e);
  if (![minimumStec, maximumStec, operationalCarbon].every(Number.isFinite)) return null;
  return {
    min: minimumStec + operationalCarbon,
    max: maximumStec + operationalCarbon,
  };
}

export default function EstimateCarbon() {
  const [mode, setMode] = useState("existing");
  const [processors, setProcessors] = useState([]);
  const [stecRegions, setStecRegions] = useState([]);
  const [processorSearch, setProcessorSearch] = useState("");
  const [loadingProcessors, setLoadingProcessors] = useState(true);
  const [submitted, setSubmitted] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [replacementError, setReplacementError] = useState("");
  const [stecError, setStecError] = useState("");
  const [stecRegionError, setStecRegionError] = useState("");
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
    stecProcessNodeNm: "7",
    manufacturingRegion: "Taiwan",
    manufacturingYear: 2020,
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

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/grid-intensity/regions`, { signal: controller.signal })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Manufacturing regions could not be loaded");
        return data;
      })
      .then((data) => {
        const regions = data.regions || [];
        setStecRegions(regions);
        setForm((current) => ({
          ...current,
          manufacturingRegion: regions.includes(current.manufacturingRegion)
            ? current.manufacturingRegion
            : regions[0] || "",
        }));
        if (!regions.length) setStecRegionError("No manufacturing regions are available.");
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setStecRegionError(requestError.message);
      });
    return () => controller.abort();
  }, []);

  async function calculate(event) {
    event.preventDefault();
    setError("");
    setReplacementError("");
    setStecError("");
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
      let stec = null;
      try {
        let stecResponse;
        if (mode === "existing") {
          stecResponse = await fetch(
            `${API_URL}/api/stec/processors/${encodeURIComponent(form.name)}`,
          );
        } else {
          if (!form.manufacturingRegion) {
            throw new Error(stecRegionError || "Select a manufacturing region to calculate STEC.");
          }
          stecResponse = await fetch(`${API_URL}/api/estimates/stec`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              inputMode: "custom",
              processorName: form.name,
              processNodeNm: form.stecProcessNodeNm,
              dieAreaMm2: Number(form.dieSize),
              manufacturingRegion: form.manufacturingRegion,
              manufacturingYear: Number(form.manufacturingYear),
            }),
          });
        }

        const stecData = await stecResponse.json();
        if (!stecResponse.ok) {
          throw new Error(stecData.error || "STEC scenario could not be calculated");
        }
        stec = mode === "existing"
          ? {
            status: stecData.status,
            value: stecData.stec_kg_co2e,
            min: stecData.stec_min_kg_co2e,
            max: stecData.stec_max_kg_co2e,
            nodeNm: stecData.node_nm,
            candidateRegions: stecData.candidate_regions,
            manufacturingYear: stecData.manufacturing_year,
            manufacturingYearStatus: stecData.manufacturing_year_status,
            locationConfidence: stecData.location_confidence,
            warnings: stecData.warnings,
          }
          : {
            status: "point",
            value: stecData.value,
            min: stecData.value,
            max: stecData.value,
            nodeNm: stecData.nodeNm,
            candidateRegions: stecData.manufacturingRegion,
            manufacturingYear: stecData.manufacturingYear,
            manufacturingYearStatus: "user_supplied",
            locationConfidence: "user_supplied",
            warnings: "",
          };
        if (stec.status === "point" && !Number.isFinite(Number(stec.value))) {
          throw new Error("STEC returned an invalid point estimate.");
        }
        if (stec.status === "range"
          && ![stec.min, stec.max].every((value) => Number.isFinite(Number(value)))) {
          throw new Error("STEC returned an invalid location range.");
        }
      } catch (requestError) {
        setStecError(requestError.message);
      }

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
      setResults({ embodied, energy: operational.energy, operational, cci, stec, replacementComparison });
    } catch (requestError) {
      setError(requestError.message);
      setResults(null);
    }
  }

  const stecScenarioTotals = results
    ? getStecScenarioTotals(results.stec, results.operational.operationalCarbonKgCo2e)
    : null;
  const cciUnit = results ? `kg CO₂e / ${results.cci.workloadUnit}` : "";

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
        stecRegions={stecRegions}
        stecRegionError={stecRegionError}
        onSubmit={calculate}
      />
      <section className="result-column">
        {results ? <div className="scenario-result-grid">
          <section className="result-card has-result">
            <span className="eyebrow">STANDARD ESTIMATE</span>
            <div className="empty-result submitted">
              {(results.embodied.value + results.operational.operationalCarbonKgCo2e).toFixed(2)}
              <small> kg CO₂e</small>
            </div>
            <p>Experimental embodied-carbon prediction plus operational carbon over {results.energy.assumptions.usageYears} years.</p>
            <div className="result-meta">
              <span>Embodied<strong>{results.embodied.value.toFixed(2)} {results.embodied.unit}</strong></span>
              <span>Operational<strong>{results.operational.operationalCarbonKgCo2e.toFixed(2)} kg CO₂e</strong></span>
              <span>Operational / year<strong>{results.operational.annualOperationalCarbonKgCo2e.toFixed(2)} kg CO₂e</strong></span>
              <span>Energy<strong>{results.energy.electricityKwh.toFixed(2)} kWh</strong></span>
              <span>CCI<strong>{results.cci.cciKgCo2ePerWorkload.toFixed(4)} {cciUnit}</strong></span>
            </div>
          </section>

          <section className="result-card stec-scenario-card">
            <span className="eyebrow">STEC-BASED SCENARIO</span>
            {stecError ? <p className="stec-scenario-message" role="alert">
              STEC could not be calculated: {stecError}
            </p> : results.stec?.status === "incomplete" ? <p className="stec-scenario-message">
              STEC is incomplete for this processor; the scenario total is not available.
              {results.stec.warnings ? ` ${results.stec.warnings}` : ""}
            </p> : stecScenarioTotals ? <>
              <div className="empty-result submitted">
                {formatRange(stecScenarioTotals.min, stecScenarioTotals.max, "kg CO₂e")}
              </div>
              <p>STEC die-manufacturing estimate plus operational carbon over {results.energy.assumptions.usageYears} years.</p>
              <div className="result-meta">
                <span>STEC · die manufacturing<strong>
                  {results.stec.status === "point"
                    ? formatRange(results.stec.value, results.stec.value, "kg CO₂e")
                    : formatRange(results.stec.min, results.stec.max, "kg CO₂e")}
                </strong></span>
                <span>STEC status<strong>{results.stec.status}</strong></span>
                <span>Operational<strong>{results.operational.operationalCarbonKgCo2e.toFixed(2)} kg CO₂e</strong></span>
                <span>CCI · STEC boundary<strong>
                  {formatRange(
                    stecScenarioTotals.min / results.cci.completedComputeWork,
                    stecScenarioTotals.max / results.cci.completedComputeWork,
                    cciUnit,
                    4,
                  )}
                </strong></span>
              </div>
              <p className="stec-scenario-caveat">
                Separate, partial boundary: STEC covers die manufacturing and does not replace the full embodied-model estimate.
                Do not add this scenario to the standard estimate.
                {results.stec.candidateRegions ? ` Fab: ${results.stec.candidateRegions}.` : ""}
                {results.stec.manufacturingYear ? ` Manufacturing year: ${results.stec.manufacturingYear}${results.stec.manufacturingYearStatus === "release_year_proxy" ? " (release-year proxy)" : ""}.` : ""}
                {results.stec.warnings ? ` ${results.stec.warnings}` : ""}
              </p>
            </> : <p className="stec-scenario-message">
              STEC scenario is not available for this processor.
            </p>}
          </section>
        </div> : <div className={`result-card ${submitted ? "has-result" : ""}`}>
          <span className="eyebrow">ESTIMATE STATUS</span>
          <div className={submitted ? "empty-result submitted" : "empty-result"}>{error ? "!" : "—"}</div>
          <p>{error || (submitted
            ? "The carbon estimate could not be completed."
            : "Submit the processor and usage scenario to calculate embodied carbon, operational carbon, energy, and CCI.")}</p>
        </div>}

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
