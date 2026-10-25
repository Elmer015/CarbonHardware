import { useState } from "react";

export default function HardwareForm({ form, setForm, mode, setMode, processors, loadingProcessors, onSubmit }) {
  const [processorSearch, setProcessorSearch] = useState("");
  const [showProcessorOptions, setShowProcessorOptions] = useState(false);
  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  const searchTerm = processorSearch.trim().toLowerCase();
  const filteredProcessors = processors.filter((processor) =>
    `${processor.name} ${processor.vendor}`.toLowerCase().includes(searchTerm));

  function searchProcessors(event) {
    const value = event.target.value;
    setProcessorSearch(value);
    const selected = processors.find((processor) => processor.name === form.name);
    if (selected && !`${selected.name} ${selected.vendor}`.toLowerCase().includes(value.trim().toLowerCase())) {
      setForm((current) => ({ ...current, name: "", processSize: "", tdp: "", dieSize: "", dies: "", avgDieArea: "" }));
    }
  }

  return <form className="form-card" onSubmit={onSubmit}><div className="form-heading"><div><span className="eyebrow">PROCESSOR PROFILE</span><h2>{mode === "existing" ? "Choose a processor" : "Custom processor"}</h2></div><span className="step-count">REQUIRED</span></div>
    <p className="form-intro">Existing processors use their five model features directly from CarbonSet. Switch to custom only for hardware that is not in the dataset.</p>
    <div className="mode-switch" role="group" aria-label="Processor input mode"><button type="button" className={mode === "existing" ? "mode-button active" : "mode-button"} onClick={() => setMode("existing")}>Existing processor</button><button type="button" className={mode === "custom" ? "mode-button active" : "mode-button"} onClick={() => setMode("custom")}>Custom processor</button></div>
    {mode === "existing" ? <><label>Search processor<div className="processor-search-control" onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) setShowProcessorOptions(false);
    }}>
      <input type="search" value={processorSearch} onFocus={() => setShowProcessorOptions(true)} onChange={(event) => {
        searchProcessors(event);
        setShowProcessorOptions(true);
      }} onKeyDown={(event) => { if (event.key === "Enter") event.preventDefault(); }} placeholder="Search by processor or vendor..." aria-label="Search CarbonSet processors" aria-expanded={showProcessorOptions} />
      {showProcessorOptions && <div className="processor-search-results" role="listbox" aria-label="Matching CarbonSet processors">
        {loadingProcessors
          ? <span className="processor-search-empty">Loading processors...</span>
          : filteredProcessors.length
            ? filteredProcessors.map((processor) => <button type="button" role="option" aria-selected={processor.name === form.name} className="processor-search-option" key={processor.name} onMouseDown={(event) => event.preventDefault()} onClick={() => {
            setForm({ ...form, ...processor });
              setProcessorSearch(processor.name);
            setShowProcessorOptions(false);
          }}>{processor.name} <span>{processor.vendor}</span></button>)
            : <span className="processor-search-empty">No matching processors</span>}
      </div>}
    </div><span className="unit">{filteredProcessors.length} matches</span></label></> : <label>Processor name<input value={form.name} onChange={update("name")} placeholder="e.g. Research CPU" required /></label>}
    {mode === "custom" && <><div className="form-grid"><label>Process size <span className="unit">nm</span><input type="number" min="0" step="any" value={form.processSize} onChange={update("processSize")} required /></label><label>TDP <span className="unit">W</span><input type="number" min="0" step="any" value={form.tdp} onChange={update("tdp")} required /></label></div>
      <div className="form-grid"><label>Die size <span className="unit">mm²</span><input type="number" min="0" step="any" value={form.dieSize} onChange={update("dieSize")} required /></label><label>Number of dies <span className="unit">count</span><input type="number" min="0" step="1" value={form.dies} onChange={update("dies")} required /></label></div>
      <label>Average die area <span className="unit">mm²</span><input type="number" min="0" step="any" value={form.avgDieArea} onChange={update("avgDieArea")} required /></label>
    </>}
    <div className="section-heading"><span className="eyebrow">OPERATIONAL CARBON</span><span className="step-count">SCENARIO INPUT</span></div><p className="form-intro">These values describe how long the processor is used. They are separate from the embodied-carbon model features.</p>
    <div className="form-grid"><label>Usage per day <span className="unit">hours</span><input type="number" min="0" max="24" step="0.5" value={form.hoursPerDay} onChange={update("hoursPerDay")} required /></label><label>Usage lifetime <span className="unit">years</span><input type="number" min="0" step="0.5" value={form.usageYears} onChange={update("usageYears")} required /></label></div>
    <div className="form-grid"><label>Average utilization <span className="unit">%</span><input type="number" min="0" max="100" step="1" value={form.utilizationPercent} onChange={update("utilizationPercent")} required /></label><label>Usage days per year <span className="unit">days</span><input type="number" min="0" max="366" step="1" value={form.daysPerYear} onChange={update("daysPerYear")} required /></label></div>
    <div className="form-grid"><label>Usage region <span className="unit">grid lookup</span><input value={form.region} onChange={update("region")} placeholder="e.g. Indonesia" required /></label><label>Analysis year <span className="unit">year</span><input type="number" min="1990" max="2025" step="1" value={form.analysisYear} onChange={update("analysisYear")} required /></label></div>
    <div className="section-heading"><span className="eyebrow">CCI WORKLOAD</span><span className="step-count">REQUIRED</span></div><p className="form-intro">CCI is carbon per completed workload. Define the unit and amount so the result is comparable.</p>
    <div className="form-grid"><label>Completed workload <span className="unit">count</span><input type="number" min="0.000001" step="any" value={form.completedWork} onChange={update("completedWork")} required /></label><label>Workload unit<input value={form.workloadUnit} onChange={update("workloadUnit")} placeholder="e.g. inference request" required /></label></div>
    <button className="button primary" type="submit">Prepare carbon estimate <span>→</span></button>
  </form>;
}