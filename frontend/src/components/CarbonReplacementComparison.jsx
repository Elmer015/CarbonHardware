import "./CarbonReplacementComparison.css";

function formatNumber(value, digits = 1) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(value);
}

function formatPayback(years) {
  if (years < 1 / 365) return "less than 1 day";
  if (years < 1 / 12) return `${formatNumber(years * 365)} days`;
  if (years < 1) return `${formatNumber(years * 12)} months`;
  return `${formatNumber(years)} years`;
}

export default function CarbonReplacementComparison({ comparison, error }) {
  return <section className="assumption-card replacement-comparison" aria-labelledby="replacement-comparison-title">
    <span className="eyebrow">CARBON-BASED REPLACEMENT RECOMMENDATIONS</span>
    <h3 id="replacement-comparison-title">Replacement hardware recommendations</h3>
    {error && <p className="replacement-error" role="alert">{error}</p>}
    {!error && comparison?.status === "no_same_type_candidate" && (
      <p>No same-type comparison options are available in CarbonSet for this processor.</p>
    )}
    {!error && comparison?.status === "current_release_date_unavailable" && (
      <p>The current processor's release date is unavailable, so newer options cannot be filtered. Automatic comparisons are available for CarbonSet processors with a release date.</p>
    )}
    {!error && comparison?.status === "no_newer_candidate" && (
      <p>No newer processor of the same type was found for comparison.</p>
    )}
    {!error && comparison?.status === "no_recent_candidate" && (
      <p>No newer same-type processor was found within the five most recent release years covered by CarbonSet.</p>
    )}
    {!error && comparison?.status === "no_similar_tdp_candidate" && (
      <p>Newer same-type processors were found, but none have a TDP from 50% to below 100% of the current processor's TDP.</p>
    )}
    {!error && comparison?.status === "no_operational_carbon_savings" && (
      <p>Eligible processors were found, but the current usage pattern or grid intensity does not produce measurable operational-carbon savings.</p>
    )}
    {!error && comparison?.status === "estimated" && <>
      <p>Up to three newer same-type processors are shown from the five most recent release years covered by CarbonSet. Their TDP is at least 50% but below the current processor's TDP.</p>
      <div className="replacement-candidates">
        {comparison.candidates.map((candidate, index) => <article className="replacement-candidate" key={candidate.name}>
          <p className="replacement-label">Recommendation {index + 1} · {candidate.releaseDate}</p>
          <h4>{candidate.name}</h4>
          <p className="replacement-label">Operational savings vs. current processor</p>
          <p className="replacement-savings">{formatNumber(candidate.annualCarbonSavingsKgCo2e)} kg CO₂e/year</p>
          <p className="replacement-break-even">For lower total emissions, use this processor for at least <strong>{formatPayback(candidate.yearsToCarbonPayback)}</strong>.</p>
          <div className="replacement-details">
            <span>Current TDP<strong>{formatNumber(comparison.currentProcessorTdpW)} W</strong></span>
            <span>Candidate TDP<strong>{formatNumber(candidate.tdpW)} W</strong></span>
            <span>Candidate operational carbon<strong>{formatNumber(candidate.annualOperationalCarbonKgCo2e)} kg CO₂e/year</strong></span>
            <span>Candidate manufacturing emissions<strong>{formatNumber(candidate.embodiedCarbonKgCo2e)} kg CO₂e</strong></span>
          </div>
        </article>)}
      </div>
      <p className="replacement-caveat">
        These recommendations consider estimated carbon only, not compatibility or performance.
        Catalog age and TDP limits are preliminary filters, not technical standards.
        TDP is used as a power proxy, embodied carbon uses the CarbonSet mean, the current
        processor's past manufacturing emissions are not counted again, and end-of-life emissions are excluded.
      </p>
    </>}
  </section>;
}
