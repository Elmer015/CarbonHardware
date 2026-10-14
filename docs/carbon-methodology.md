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

`stec.py` is deliberately marked **incomplete**. The repository contains only the title of the cited spatial-temporal embodied-carbon and dual carbon attribution paper; it does not contain the verified equation, attribution definitions, spatial/temporal datasets, allocation rule, or correction factors. `calculate_stec()` raises `STECIncompleteError` instead of returning an invented value.

Before implementation, obtain and verify:

1. the exact spatial-temporal embodied-carbon equation and functional unit;
2. the two attribution definitions and their non-overlap rule;
3. spatial location/grid/manufacturing inputs and time-period inputs;
4. allocation, boundary, and unit conventions;
5. any correction factors and their empirical sources.

No STEC number should be reported until these items are available and tested against the cited methodology.

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
