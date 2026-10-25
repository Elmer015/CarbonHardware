# STEC source data

`evidence/` contains the fab provenance, vendor/node fab rules, chiplet
inventory, and optional manufacturing-year overrides supplied for this
project. An empty manufacturing-year override file means release year remains
an explicitly labeled proxy.

The batch calculation also reads the deduplicated CarbonSet hardware rows and
the lifecycle location-based electricity intensity in
`data/raw/environmental/owid-lifecycle-carbon-intensity.csv`.

The workbook methodology is preserved at
`docs/research/Analisis_STEC_CPU_GPU.xlsx`. Batch results are reproducible with:

```powershell
python ml-engine/carbon/stec_batch.py
```

The generated CSV is `data/processed/stec-per-chip.csv`. It reports location
ranges where multiple fab countries are candidates and marks unsupported
chiplet node parameters as incomplete rather than silently substituting a
different node. Results exclude yield correction and market-based attribution.
