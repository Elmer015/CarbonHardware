import { useEffect, useMemo, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

function formatCarbon(value) {
  return value === null || value === undefined || !Number.isFinite(Number(value))
    ? "Not reported"
    : `${Number(value).toFixed(3)} kg CO₂e`;
}

function stecLabel(stec) {
  if (stec.status === "point") return formatCarbon(stec.value);
  if (stec.status === "range") return `${Number(stec.min).toFixed(3)}–${Number(stec.max).toFixed(3)} kg CO₂e`;
  return "Not reported";
}

export default function Comparison() {
  const [results, setResults] = useState([]);
  const [selectedName, setSelectedName] = useState("");
  const [search, setSearch] = useState("");
  const [type, setType] = useState("");
  const [showOptions, setShowOptions] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/comparison`, { signal: controller.signal })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Comparison data could not be loaded");
        return data;
      })
      .then((data) => {
        setResults(data.results);
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const filtered = useMemo(() => results.filter((row) =>
    (!type || row.type === type)
    && `${row.name} ${row.vendor}`.toLowerCase().includes(search.trim().toLowerCase())),
  [results, search, type]);
  const selected = results.find((row) => row.name === selectedName);

  return <div className="page">
    <header className="topbar compact">
      <div>
        <span className="eyebrow">CARBON HARDWARE / MODEL COMPARISON</span>
        <h1>Baseline vs STEC.</h1>
        <p className="lede">Compare lifecycle embodied-carbon estimates with die-manufacturing STEC for the same processor.</p>
      </div>
      <span className="page-number">03</span>
    </header>

    <section className="panel comparison-panel">
      <div className="section-heading">
        <div><span className="eyebrow">PROCESSOR COMPARISON</span><h2>Select a processor</h2></div>
        <span className="muted">{results.length.toLocaleString()} processors</span>
      </div>
      <div className="comparison-selectors">
        <label>Processor type<select value={type} onChange={(event) => setType(event.target.value)}><option value="">All types</option><option value="CPU">CPU</option><option value="GPU">GPU</option></select></label>
        <label>Search processor<div className="processor-search-control" onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) setShowOptions(false);
        }}>
          <input type="search" value={search} onFocus={() => setShowOptions(true)} onChange={(event) => {
            setSearch(event.target.value);
            setShowOptions(true);
          }} placeholder="Search by processor or vendor..." aria-label="Search comparison processors" aria-expanded={showOptions} />
          {showOptions && <div className="processor-search-results" role="listbox" aria-label="Matching comparison processors">
            {loading
              ? <span className="processor-search-empty">Loading processors...</span>
              : filtered.length
                ? filtered.map((row) => <button type="button" role="option" aria-selected={row.name === selectedName} className="processor-search-option" key={row.name} onMouseDown={(event) => event.preventDefault()} onClick={() => {
                  setSelectedName(row.name);
                  setSearch(row.name);
                  setShowOptions(false);
                }}>{row.name} <span>{row.vendor} · {row.type}</span></button>)
                : <span className="processor-search-empty">No matching processors</span>}
          </div>}
        </div><span className="unit">{filtered.length} matches</span></label>
      </div>
      {error && <p className="stec-error" role="alert">{error}</p>}
      {loading && <p className="muted">Loading model predictions and STEC inventory…</p>}
      {selected && <>
        <div className="comparison-value-grid">
          <article className="comparison-value-card">
            <span className="eyebrow">BASELINE · EMBODIED MODEL</span>
            <strong>{formatCarbon(selected.baseline.value)}</strong>
            <span>Experimental model prediction · {selected.baseline.metadata?.model_type || "model type unavailable"}</span>
            <small>{selected.baseline.boundary}</small>
          </article>
          <article className="comparison-value-card stec">
            <span className="eyebrow">STEC · DIE MANUFACTURING</span>
            <strong>{stecLabel(selected.stec)}</strong>
            <span>Status: {selected.stec.status}{selected.stec.nodeNm ? ` · ${selected.stec.nodeNm} nm` : ""}</span>
            <small>{selected.stec.boundary}{selected.stec.candidateRegions ? ` · Fab: ${selected.stec.candidateRegions}` : ""}</small>
            {selected.stec.warnings && <small className="comparison-warning">{selected.stec.warnings}</small>}
          </article>
        </div>
        <p className="comparison-boundary-note"><strong>Perhatikan batas sistem:</strong> baseline memprediksi embodied carbon sepanjang lifecycle model, sedangkan STEC hanya mencakup pembuatan die. Keduanya ditampilkan berdampingan, tidak dijumlahkan dan tidak diperlakukan sebagai dua model yang memprediksi target identik.</p>
      </>}
    </section>
  </div>;
}
