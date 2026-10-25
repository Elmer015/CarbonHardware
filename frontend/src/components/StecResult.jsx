const levelLabels = {
  product_sourced: "Product-level source",
  chiplet_sourced: "Per-die chiplet source",
  vendor_node_assumption: "Vendor/node assumption",
  user_input: "User input",
  unresolved: "Unresolved",
};

const yearLabels = {
  sourced: "sourced",
  release_year_proxy: "release year used as proxy",
  user_input: "user input",
};

const kg = (value) => (value === null || value === undefined ? "—" : `${value.toFixed(2)} kg`);

export default function StecResult({ stec, error }) {
  if (error) return <div className="assumption-card"><span className="eyebrow">STEC · LOCATION-BASED</span><h3>Die manufacturing carbon</h3><p className="warning-copy">{error}</p></div>;
  if (!stec) return null;
  const headline = stec.status === "range" ? `${kg(stec.stecMinKgCo2e)} – ${kg(stec.stecMaxKgCo2e)}` : kg(stec.stecKgCo2e);
  const regions = stec.regions.filter((item) => item.status === "complete");
  const market = regions.map((item) => item.marketBased).find((item) => item.status === "computed");
  return <div className="assumption-card">
    <span className="eyebrow">STEC · LOCATION-BASED · {stec.status.toUpperCase()}</span>
    <h3>{headline}</h3>
    <p>Cradle-to-gate die manufacturing for one chip, {stec.nodeNm} nm, manufactured {stec.manufacturingYear} ({yearLabels[stec.manufacturingYearStatus] || stec.manufacturingYearStatus}).</p>
    <div className="result-meta">
      <span>Fab evidence<strong>{levelLabels[stec.location.level] || stec.location.level}{stec.location.confidence ? ` · ${stec.location.confidence}` : ""}</strong></span>
      {!stec.chiplet.applied && regions.map((item) => <span key={item.region}>{item.region}<strong>{kg(item.stecKgCo2e)} · {Math.round(item.ciGCo2ePerKwh)} g/kWh</strong></span>)}
      {stec.chiplet.applied && stec.chiplet.components.map((item) => <span key={item.dieRole}>{item.dieCount}× {item.dieRole} · {item.nodeNm} nm · {item.region}<strong>{kg(item.stecKgCo2e)}</strong></span>)}
      {stec.globalBaseline.stecKgCo2e !== null && <span>Global baseline (STEC-GY)<strong>{kg(stec.globalBaseline.stecKgCo2e)}</strong></span>}
      <span>Market-based<strong>{market ? kg(market.stecKgCo2e) : "not available"}</strong></span>
    </div>
    {stec.location.basis && <p>Basis: {stec.location.basis}</p>}
    {stec.warnings.map((warning) => <p key={warning} className="warning-copy">{warning}</p>)}
    <p>Grid source: {stec.gridSource}. Location- and market-based values are reported separately and never summed.</p>
  </div>;
}
