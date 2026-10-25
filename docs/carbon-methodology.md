# Phase 5: Carbon Accounting Engine

**Status:** implemented with explicit evidence boundaries; STEC remains incomplete.  
**Date:** 2026-10-15

## Accounting Principles

The engine keeps four quantities separate:

- embodied carbon: `kg CO2e` for a processor or hardware lifecycle;
- operational carbon: `kg CO2e` from electricity and an externally supplied grid factor;
- CCI: `kg CO2e / completed workload unit`;
- e-waste: physical hardware mass in `kg`.

No e-waste mass is converted to carbon, and no carbon result is counted as waste mass. Each result carries source, boundary, functional unit, or analysis-period metadata where applicable.

## Embodied Carbon

`embodied_carbon.py` loads the validated Phase 4 `joblib` artifact and returns values marked `model_prediction`. It never labels predictions as measured or reported LCA values. Separately, `reported_lca_value()` records a source-reported or measured value only when its unit, source, functional unit, and boundary are supplied.

The current validated model uses CarbonSet's `Emb_Carbon_Mean` in `kg CO2e`, based on the supplied CarbonSet paper (arXiv:2506.10373v1). The paper describes this as a mean from 10,000 ECO-CHIP simulations across the modeled lifecycle. This is modeled output, not a direct measurement. The Phase 4 model is an experimental Random Forest estimator and is not claimed to reproduce SCARIF.

### Custom-PC inventory

`custom_pc.py` accounts for a custom PC as an explicit bill of materials: CPU, GPU, RAM, storage, motherboard, PSU, case, cooling, or other supplied component types. It has no built-in factors. Populate `data/embodied-carbon-factors.template.csv` only with verified, source-backed values, retaining the source, functional unit, and lifecycle boundary for each record.

The calculator reports a final `total_kg_co2e` only if every requested component has a matching factor. Otherwise it reports the resolved subtotal and an `unresolved` entry for each missing component. A proxy is permitted only when explicitly selected and of the same component type; the output labels it `explicit_proxy_factor`. This prevents an A100-specific LCA value from silently becoming a generic GPU factor.

## Operational Carbon

The implemented equation is:

```text
operational_carbon_kg_co2e = electricity_kwh * grid_intensity_kg_co2e_per_kwh
```

Power can be converted explicitly using:

```text
electricity_kwh = power_w / 1000 * runtime_hours * utilization
```

The caller must provide the grid-intensity source and analysis period. The engine does not contain a default grid value and does not download or invent one. Electricity assumptions such as TDP as a power proxy, runtime, utilization, cooling overhead, and PUE must be recorded by the caller in `assumptions`; they are not silently inferred.

## Compute Carbon Intensity (CCI)

The implemented equation is:

```text
CCI = total_carbon_kg_co2e / completed_compute_work
```

`completed_compute_work` must be positive, and the caller must define its workload unit, for example completed equivalent training runs or inference tokens. Hardware comparisons are valid only when the workload definition, lifecycle boundary, and analysis period are equivalent. The engine does not assume that raw runtime, peak FLOPS, or hardware count is an equivalent workload.

## E-waste

`e_waste.py` allocates hardware mass in `kg` across reuse, recycling, and disposal fractions. Fractions must be in `[0, 1]` and sum to exactly one. The result verifies mass conservation and stores the scenario source and assumptions. Recycling or disposal emission factors are intentionally not applied because no approved e-waste factors are available in this repository.

Required evidence for a project scenario includes hardware mass, replacement/discard event, lifetime, reuse/refurbishment route, recycling route, disposal route, and the source/boundary for each fraction. These records must remain separate from carbon accounting.

## STEC and Dual Carbon Attribution

`stec.py` now implements location-based, country-year STEC for one CPU/GPU die using the verified workbook contract:

```text
intensity_g_per_cm2 = GPS + MPS + CI * EPS
stec_kg_co2e = intensity_g_per_cm2 * die_area_mm2 / 100 / 1000
```

An optional yield correction divides the result by `yield_factor`. Node parameters for the paper's table are included; 22 nm uses the 20 nm parameters and 12 nm (GlobalFoundries 12LP IO dies) uses the 14 nm parameters, both labeled `explicit_proxy_node`. The function requires a caller-supplied country-year grid intensity and manufacturing region/year; it never invents either value. Unknown nodes, invalid values, and unsupported evidence fail explicitly.

The implementation boundary remains **cradle-to-gate die manufacturing**. It does not include packaging, board, memory, cooling, use, or end-of-life.

### Market-based and multi-die STEC

- `calculate_market_based_stec()` uses a contractual factor (PPA/REC) and requires `contract_type`, `factor_source`, and `foundry`. Its result is labeled `market-based` and is reported next to, never added to, the location-based value.
- `calculate_multi_die_stec()` sums dies that differ in node or fab (for example AMD CCD on TSMC 7 nm in Taiwan plus IO die on GlobalFoundries 12/14 nm in the United States). CarbonSet records only the CCDs of AMD chiplet products, so chiplet totals are computed from `data/stec/chiplets.csv` instead of the CarbonSet die area.

### Evidence resolution (`stec_evidence.py`)

`resolve_processor_stec()` assembles STEC inputs from `data/stec/*.csv` and the OWID/Ember country-year series in `data/raw/grid/`, labeling every evidence level:

| Input | Order of evidence |
|---|---|
| Fab region | user input → `fab-provenance.csv` (product source) → `chiplets.csv` (per die) → `fab-rules.csv` (vendor/node assumption; several candidates give a **range**) → unresolved |
| Manufacturing year | user input → `manufacturing-years.csv` → CarbonSet release year (labeled proxy) |
| Yield | `yields.csv` by node, foundry, year; otherwise not applied |
| Market-based factor | `market-factors.csv` by foundry and year; otherwise `not_available` |

`manufacturing-years.csv`, `yields.csv`, and `market-factors.csv` currently contain headers only: no sourced values are available yet, so results use the release-year proxy, no yield correction, and no market-based value.

### Batch, workbook, and API

- `python ml-engine/carbon/stec_batch.py` writes `data/processed/stec-per-chip.csv` and `stec-batch-summary.json` for every CarbonSet processor.
- `python ml-engine/experiments/build_stec_workbook.py` rebuilds `data/processed/Analisis_STEC_CPU_GPU.xlsx` from repository data only.
- The backend exposes `POST /api/estimates/stec/processor` and `GET /api/estimates/stec/regions`; the frontend form shows the STEC result with its evidence level, range, chiplet breakdown, and warnings.

Report every STEC value as an **estimated location-based die STEC** together with its `location.level`, manufacturing-year status, and warnings.

## Lifecycle Carbon, Final CCI, and Propagated Uncertainty

`carbon/lifecycle.py` combines the quantities for one processor scenario:

```text
electricity_kwh = tdp_w / 1000 * hours_per_day * days_per_year * usage_years * utilization
operational_kg  = electricity_kwh * grid_kg_co2e_per_kwh
total_kg        = embodied_kg + operational_kg
cci_final       = total_kg / completed_compute_work
```

- Grid intensity: `carbon/grid_intensity.py` reads `data/grid/grid-intensity.csv` (region, year, g CO2e/kWh, source, basis), built from the Our World in Data / Ember series in `data/raw/grid`. Values are location-based, never interpolated or extrapolated; a missing region/year leaves operational carbon pending and labels CCI `embodied_only`. One grid year is held constant over the usage lifetime and this is stated in the result warnings.
- Embodied range: CarbonSet `Emb_Carbon_Min/Max` for existing processors. Custom processors use a 90% empirical multiplicative interval from out-of-fold relative residuals of the same Random Forest configuration under 5-fold cross-validation grouped by die signature (`experiments/prediction_interval.py` → `artifacts/embodied_prediction_interval.json`); the interval is roughly -20% to +71% of the prediction and holds on CarbonSet only.
- Propagation: Monte Carlo with triangular distributions `{min, mostLikely, max}` for TDP, utilization, hours per day, days per year, usage years, and grid intensity. Undistributed inputs are held constant and listed as such. The result reports P2.5/P5/median/P95/P97.5 for embodied, electricity, operational, total, embodied share, and CCI, plus Spearman rank correlations of embodied, electricity, and grid intensity with total carbon. These are propagated input ranges, not calibrated confidence intervals.

## Uncertainty

`models/uncertainty.py` supports two evidence-preserving forms:

- `summarize_interval()` for a source-provided lower/central/upper range;
- `summarize_samples()` for supplied non-negative samples, reporting empirical quantiles.

The output records unit, source, uncertainty kind, method, and sample count. The sample method explicitly says its quantiles are **not calibrated coverage**. This is an uncertainty summary, not a claim that the model is probabilistically calibrated. The current CarbonSet provenance supports modeled min/max/mean outputs, while the project's separate uncertainty framework is still unavailable; those should not be conflated.

Uncertainty categories to preserve in future data are:

- input uncertainty: uncertain hardware, energy, lifetime, or grid inputs;
- parameter uncertainty: uncertain ECO-CHIP or accounting parameters;
- model uncertainty: uncertainty from using an experimental estimator rather than a validated physical/LCA model.

## Tests

`ml-engine/tests/test_carbon_accounting.py` covers model-prediction labeling, operational-carbon equations and invalid inputs, CCI workload validation, e-waste mass conservation and carbon separation, uncertainty interval/sample validation, and the explicit incomplete STEC path.
