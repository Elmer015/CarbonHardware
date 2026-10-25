const fmt = (value, digits = 2) => (value === null || value === undefined ? "—" : value.toFixed(digits));
const band = (summary, digits = 2) => (summary ? `${fmt(summary.p2_5, digits)} – ${fmt(summary.p97_5, digits)}` : "—");

export default function LifecycleResult({ lifecycle }) {
  if (!lifecycle) return null;
  const { embodied, operational, grid, cci, uncertainty } = lifecycle;
  return <div className="assumption-card">
    <span className="eyebrow">LIFECYCLE CARBON · {lifecycle.status.replaceAll("_", " ").toUpperCase()}</span>
    <h3>{lifecycle.totalKgCo2e !== null ? `${fmt(lifecycle.totalKgCo2e)} kg CO₂e total` : `${fmt(embodied.valueKgCo2e)} kg CO₂e embodied only`}</h3>
    <div className="result-meta">
      <span>Embodied<strong>{fmt(embodied.valueKgCo2e)} kg ({fmt(embodied.lowerKgCo2e)}–{fmt(embodied.upperKgCo2e)})</strong></span>
      {operational && <span>Operational<strong>{fmt(operational.carbonKgCo2e)} kg · {fmt(operational.annualCarbonKgCo2e)} kg/yr</strong></span>}
      {grid && <span>Grid {grid.region} {grid.year}<strong>{fmt(grid.gCo2ePerKwh, 1)} g/kWh · {grid.basis}</strong></span>}
      {lifecycle.embodiedShare !== null && <span>Embodied share<strong>{fmt(lifecycle.embodiedShare * 100, 1)}%</strong></span>}
      {cci && <span>CCI {cci.status === "final" ? "final" : "(embodied only)"}<strong>{fmt(cci.cciKgCo2ePerWorkload, 4)} kg/{cci.workloadUnit}</strong></span>}
    </div>
    {uncertainty && <>
      <span className="eyebrow">95% PROPAGATED RANGE (P2.5–P97.5)</span>
      <div className="result-meta">
        <span>Embodied<strong>{band(uncertainty.embodied)} kg</strong></span>
        <span>Electricity<strong>{band(uncertainty.electricity, 1)} kWh</strong></span>
        {uncertainty.operational && <span>Operational<strong>{band(uncertainty.operational)} kg</strong></span>}
        {uncertainty.total && <span>Total<strong>{band(uncertainty.total)} kg</strong></span>}
        {uncertainty.cci && <span>CCI<strong>{band(uncertainty.cci, 4)}</strong></span>}
      </div>
      <p>Varied: {uncertainty.variedInputs.length ? uncertainty.variedInputs.join(", ") : "none"}. {uncertainty.method}. Embodied range source: {embodied.intervalSource}.</p>
      {uncertainty.drivers && <p>Rank correlation with total: {Object.entries(uncertainty.drivers).map(([name, value]) => `${name} ${fmt(value)}`).join(" · ")}</p>}
    </>}
    {grid && <p>Grid source: {grid.source}.</p>}
    {lifecycle.warnings.map((warning) => <p key={warning} className="warning-copy">{warning}</p>)}
  </div>;
}
