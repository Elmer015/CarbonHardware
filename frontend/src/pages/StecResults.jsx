import { useEffect, useMemo, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";
const PROCESS_NODES = ["3", "5", "7", "7-EUV", "7-EUV-DP", "10", "14", "20", "22", "28"];
const YEARS = Array.from({ length: 36 }, (_, index) => 1990 + index);

function formatCarbon(value) {
  return value === null || value === undefined ? "—" : `${Number(value).toFixed(3)} kg CO₂e`;
}

async function readJson(response, fallbackMessage) {
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || fallbackMessage);
  return data;
}

export default function StecResults() {
  const [options, setOptions] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [processorSearch, setProcessorSearch] = useState("");
  const [showProcessorOptions, setShowProcessorOptions] = useState(false);
  const [processor, setProcessor] = useState(null);
  const [type, setType] = useState("");
  const [regions, setRegions] = useState([]);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [loadingProcessor, setLoadingProcessor] = useState(false);
  const [error, setError] = useState("");
  const [customForm, setCustomForm] = useState({
    processorName: "",
    processNodeNm: "7",
    dieAreaMm2: "",
    manufacturingRegion: "Taiwan",
    manufacturingYear: "2020",
  });
  const [customResult, setCustomResult] = useState(null);
  const [customError, setCustomError] = useState("");
  const [customLoading, setCustomLoading] = useState(false);

  const filteredOptions = useMemo(
    () => options.filter((option) =>
      (!type || option.type === type)
      && `${option.product} ${option.vendor} ${option.type}`.toLowerCase().includes(processorSearch.trim().toLowerCase())),
    [options, processorSearch, type],
  );

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetch(`${API_URL}/api/stec/processors/options`, { signal: controller.signal }).then((response) => readJson(response, "STEC processors could not be loaded")),
      fetch(`${API_URL}/api/grid-intensity/regions`, { signal: controller.signal }).then((response) => readJson(response, "Grid regions could not be loaded")),
    ])
      .then(([processorData, regionData]) => {
        setOptions(processorData.options);
        setRegions(regionData.regions);
        if (!regionData.regions.includes(customForm.manufacturingRegion) && regionData.regions.length) {
          setCustomForm((current) => ({ ...current, manufacturingRegion: regionData.regions[0] }));
        }
        if (processorData.options.length) setSelectedProduct(processorData.options[0].product);
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingOptions(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedProduct) {
      setProcessor(null);
      return undefined;
    }
    const controller = new AbortController();
    setLoadingProcessor(true);
    fetch(`${API_URL}/api/stec/processors/${encodeURIComponent(selectedProduct)}`, { signal: controller.signal })
      .then((response) => readJson(response, "STEC result could not be loaded"))
      .then(setProcessor)
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingProcessor(false);
      });
    return () => controller.abort();
  }, [selectedProduct]);

  function updateCustomForm(field) {
    return (event) => setCustomForm((current) => ({ ...current, [field]: event.target.value }));
  }

  async function calculateCustomStec(event) {
    event.preventDefault();
    setCustomLoading(true);
    setCustomError("");
    setCustomResult(null);
    try {
      const response = await fetch(`${API_URL}/api/estimates/stec`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inputMode: "custom",
          processorName: customForm.processorName,
          processNodeNm: customForm.processNodeNm,
          dieAreaMm2: Number(customForm.dieAreaMm2),
          manufacturingRegion: customForm.manufacturingRegion,
          manufacturingYear: Number(customForm.manufacturingYear),
        }),
      });
      setCustomResult(await readJson(response, "Custom STEC calculation failed"));
    } catch (requestError) {
      setCustomError(requestError.message);
    } finally {
      setCustomLoading(false);
    }
  }

  return <div className="page">
    <header className="topbar compact">
      <div>
        <span className="eyebrow">CARBON HARDWARE / LOCATION-BASED</span>
        <h1>STEC per processor.</h1>
        <p className="lede">Choose a CarbonSet processor to view its die-manufacturing estimate, or calculate a custom chip.</p>
      </div>
      <span className="page-number">02</span>
    </header>
    <section className="panel stec-panel">
      <div className="section-heading">
        <div><span className="eyebrow">CARBONSET INVENTORY</span><h2>Choose processor</h2></div>
        <span className="muted">{filteredOptions.length.toLocaleString()} processors</span>
      </div>
      <div className="stec-selectors">
        <label>Processor type<select value={type} onChange={(event) => setType(event.target.value)}><option value="">All types</option><option value="CPU">CPU</option><option value="GPU">GPU</option></select></label>
        <label>Search processor<div className="processor-search-control" onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) setShowProcessorOptions(false);
        }}>
          <input type="search" value={processorSearch} onFocus={() => setShowProcessorOptions(true)} onChange={(event) => {
            setProcessorSearch(event.target.value);
            setShowProcessorOptions(true);
          }} placeholder="Search by processor or vendor..." aria-label="Search STEC processors" aria-expanded={showProcessorOptions} />
          {showProcessorOptions && <div className="processor-search-results" role="listbox" aria-label="Matching STEC processors">
            {loadingOptions
              ? <span className="processor-search-empty">Loading processors...</span>
              : filteredOptions.length
                ? filteredOptions.map((option) => <button type="button" role="option" aria-selected={option.product === selectedProduct} className="processor-search-option" key={option.product} onMouseDown={(event) => event.preventDefault()} onClick={() => {
                setSelectedProduct(option.product);
                setProcessorSearch(option.product);
                setShowProcessorOptions(false);
                setError("");
              }}>{option.product} <span>{option.type} · {option.status}</span></button>)
                : <span className="processor-search-empty">No matching processors</span>}
          </div>}
        </div><span className="unit">{filteredOptions.length} matches</span></label>
      </div>
      {error && <p className="stec-error" role="alert">{error}</p>}
      {loadingProcessor && <p className="muted stec-message">Loading processor STEC…</p>}
      {processor && !loadingProcessor && <div className="stec-detail">
        <div className="stec-result-highlight">
          <span className="eyebrow">LOCATION-BASED DIE STEC</span>
          <strong>{processor.status === "point"
            ? formatCarbon(processor.stec_kg_co2e)
            : processor.status === "range"
              ? `${Number(processor.stec_min_kg_co2e).toFixed(3)}–${Number(processor.stec_max_kg_co2e).toFixed(3)} kg CO₂e`
              : "Not reported"}</strong>
          <span className={`pill ${processor.status === "point" ? "ready" : ""}`}>{processor.status}</span>
        </div>
        <dl className="stec-facts">
          <div><dt>Vendor / type</dt><dd>{processor.vendor} / {processor.type}</dd></div>
          <div><dt>Process node</dt><dd>{processor.node_nm} nm</dd></div>
          <div><dt>Total die area</dt><dd>{Number(processor.chiplet_die_area_mm2 || processor.carbonset_die_area_mm2).toFixed(1)} mm²{processor.chiplet_applied ? " (chiplet sum)" : ""}</dd></div>
          <div><dt>Manufacturing year</dt><dd>{processor.manufacturing_year || "Unavailable"}{processor.manufacturing_year_status === "release_year_proxy" ? " (release-year proxy)" : ""}</dd></div>
          <div><dt>Fab candidate(s)</dt><dd>{processor.candidate_regions || "Unresolved"}</dd></div>
          <div><dt>Fab evidence</dt><dd>{processor.location_level} / {processor.location_confidence}</dd></div>
        </dl>
        {(processor.warnings || processor.location_basis) && <div className="stec-evidence">
          {processor.warnings && <p>{processor.warnings}</p>}
          {processor.location_basis && <p>{processor.location_basis}</p>}
        </div>}
      </div>}
    </section>

    <section className="panel stec-custom-panel">
      <div className="section-heading">
        <div><span className="eyebrow">CUSTOM CALCULATION</span><h2>Calculate a custom chip</h2></div>
        <span className="muted">No yield correction</span>
      </div>
      <p className="form-intro">Enter die area, process node, and fab country/year. Grid intensity is looked up from the project lifecycle dataset.</p>
      <form className="stec-custom-form" onSubmit={calculateCustomStec}>
        <label>Chip name<input value={customForm.processorName} onChange={updateCustomForm("processorName")} placeholder="e.g. Research accelerator" required /></label>
        <label>Process node<select value={customForm.processNodeNm} onChange={updateCustomForm("processNodeNm")} required>{PROCESS_NODES.map((node) => <option key={node} value={node}>{node} nm{node === "22" ? " (20 nm parameter proxy)" : ""}</option>)}</select></label>
        <label>Die area <span className="unit">mm²</span><input type="number" min="0.000001" step="any" value={customForm.dieAreaMm2} onChange={updateCustomForm("dieAreaMm2")} required /></label>
        <label>Fab country<select value={customForm.manufacturingRegion} onChange={updateCustomForm("manufacturingRegion")} required>{regions.map((region) => <option key={region} value={region}>{region}</option>)}</select></label>
        <label>Manufacturing year<input type="number" min={YEARS[0]} max={YEARS[YEARS.length - 1]} step="1" value={customForm.manufacturingYear} onChange={updateCustomForm("manufacturingYear")} required /></label>
        <button className="button primary" type="submit" disabled={customLoading}>{customLoading ? "Calculating..." : "Calculate STEC"}</button>
      </form>
      {customError && <p className="stec-error" role="alert">{customError}</p>}
      {customResult && <div className="stec-custom-result">
        <strong>{formatCarbon(customResult.value)}</strong>
        <span>{customResult.processor.name} · {customResult.manufacturingRegion}, {customResult.manufacturingYear} · CI {Number(customResult.ciGCo2ePerKwh).toFixed(2)} gCO₂e/kWh</span>
        <small>{customResult.boundary}; {customResult.assumptions.parameter_source}{customResult.assumptions.explicit_proxy_node ? `; ${customResult.assumptions.explicit_proxy_node} nm uses a 20 nm parameter proxy` : ""}</small>
      </div>}
    </section>
    <p className="stec-footnote">Ranges represent candidate fab-location scenarios, not statistical confidence intervals. A point estimate may still depend on an assumed fab location; check its confidence and location basis. Incomplete rows are withheld when a required node parameter or source is unavailable. Release year is a labeled manufacturing-year proxy.</p>
  </div>;
}
