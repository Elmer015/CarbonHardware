# Phase 5: Carbon Accounting Engine

**Status:** implemented with explicit evidence boundaries; product-level fab and chiplet evidence remains incomplete for some processors.
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

`stec.py` implements location-based, country-year STEC for one CPU/GPU die.
`stec_batch.py` applies that equation to the deduplicated CarbonSet processor
list using the workbook and supplied fab/chiplet evidence:

```text
intensity_g_per_cm2 = GPS + MPS + CI * EPS
stec_kg_co2e = intensity_g_per_cm2 * die_area_mm2 / 100 / 1000
```

The batch uses the supplied country-year lifecycle electricity intensity in
`data/raw/environmental/owid-lifecycle-carbon-intensity.csv`, fab inputs under
`data/raw/stec/evidence/`, and the methodology workbook at
`docs/research/Analisis_STEC_CPU_GPU.xlsx`. It does not apply yield correction
or market-based attribution. CarbonSet release year is explicitly labeled as a
manufacturing-year proxy when no product-specific override exists. The 22 nm
CarbonSet bucket explicitly uses the workbook's 20 nm parameters.

Rows with multiple candidate fab countries report min/max location scenarios,
not a statistical confidence interval. The batch calculates 1,272 unique
processors: 659 point estimates, 610 location ranges, and 3 incomplete
chiplet results. Three AMD chiplet records contain 12 nm I/O dies, for which
the workbook has no matching node parameter; those totals are not reported
until a sourced parameter or an explicitly approved proxy is supplied.

Chiplet products with supported node parameters are calculated die-by-die,
including each die's area, count, node, and manufacturing region. The
implementation boundary remains **cradle-to-gate die manufacturing**; it
does not include packaging, board, memory, cooling, use, or end-of-life.
Market-based attribution remains unavailable because no sourced contractual
factors were supplied. The generated batch is reproducible with:

```powershell
python ml-engine/carbon/stec_batch.py
```

It writes `data/processed/stec-per-chip.csv`. The backend recalculates the
inventory at startup and exposes it through `GET /api/stec/processors`.

## Tests

`ml-engine/tests/test_carbon_accounting.py` covers model-prediction labeling,
operational-carbon equations and invalid inputs, CCI workload validation,
e-waste mass conservation and carbon separation, and the explicit incomplete
STEC path. `ml-engine/tests/test_stec_batch.py` verifies the supplied batch,
product-specific fab evidence, location ranges, node proxies, and unsupported
chiplet handling.
