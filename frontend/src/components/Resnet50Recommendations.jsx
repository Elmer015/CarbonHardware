import { useEffect, useState } from "react";
import "./Resnet50Recommendations.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

function formatNumber(value, digits = 2) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(value);
}

export default function Resnet50Recommendations({ processorName }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ processorName });
    fetch(`${API_URL}/api/benchmarks/resnet50/recommendations?${query}`, { signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "Hardware recommendations could not be loaded");
        return payload;
      })
      .then(setData)
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      });
    return () => controller.abort();
  }, [processorName]);

  return <section className="assumption-card resnet-recommendations" aria-labelledby="resnet-recommendations-title">
    <span className="eyebrow">RESNET50 HARDWARE RECOMMENDATION</span>
    <h3 id="resnet-recommendations-title">Lower-carbon, faster benchmark systems</h3>
    <p className="recommendation-intro">
      Compared with {processorName}, recommendations must have equal-or-lower CarbonSet embodied carbon and higher ResNet50 throughput in the same benchmark cohort.
    </p>
    {error && <p className="stec-error" role="alert">{error}</p>}
    {!data && !error && <p className="muted">Checking comparable ResNet50 benchmark results…</p>}
    {data && data.results.length === 0 && <p className="muted">{data.metadata.message}</p>}
    {data?.results.map((candidate) => <article className="recommendation-card" key={candidate.benchmarkId}>
      <div className="recommendation-heading">
        <div><span className="recommendation-tag">RECOMMENDED SYSTEM</span><strong>{candidate.product}</strong></div>
        <span className="recommendation-version">{candidate.suiteVersion} · {candidate.systemType}</span>
      </div>
      <p className="recommendation-system">{candidate.systemName} · {candidate.deviceCount} × inference device</p>
      <div className="recommendation-comparison">
        <div><span>Embodied carbon · candidate</span><strong>{formatNumber(candidate.systemEmbodiedCarbonMeanKg)} kg CO₂e</strong><small>{formatNumber(candidate.systemEmbodiedCarbonMinKg)}–{formatNumber(candidate.systemEmbodiedCarbonMaxKg)} range</small></div>
        <div><span>Embodied carbon · selected</span><strong>{formatNumber(candidate.baseline.systemEmbodiedCarbonMeanKg)} kg CO₂e</strong><small>{candidate.baseline.product} · {candidate.baseline.deviceCount} devices</small></div>
        <div><span>ResNet50 throughput · candidate</span><strong>{formatNumber(candidate.throughputSamplesPerS)} images/s</strong><small>{candidate.configClass} · {candidate.inputDataTypes || "precision not specified"}</small></div>
        <div><span>ResNet50 throughput · selected</span><strong>{formatNumber(candidate.baseline.throughputSamplesPerS)} images/s</strong><small>{candidate.baseline.systemName}</small></div>
      </div>
      <p className="recommendation-gain">
        {candidate.embodiedCarbonDifferenceKg === 0
          ? "Equal embodied carbon"
          : `${formatNumber(Math.abs(candidate.embodiedCarbonDifferenceKg))} kg CO₂e lower embodied carbon`}
        {" · "}{formatNumber(candidate.throughputImprovementPercent)}% higher throughput
      </p>
      <a className="recommendation-source" href={candidate.sourceUrl} target="_blank" rel="noreferrer">View MLPerf result source</a>
    </article>)}
    {data?.results.length > 0 && <p className="recommendation-boundary">
      Carbon values use CarbonSet embodied-carbon mean/range multiplied by inference-device count. They do not include host/server parts or operational carbon; throughput is measured for the full benchmark system. This recommendation is separate from the carbon estimate above.
    </p>}
  </section>;
}
