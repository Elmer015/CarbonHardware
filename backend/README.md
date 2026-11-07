# CarbonHardware backend

Node.js/Express API for the current CarbonHardware calculation contracts.

## Run

```powershell
cd backend
npm install
npm start
```

The server loads unique processor records from `data/raw/carbonset/CarbonSet.csv`.
Override the location with `CARBONSET_PATH` when starting from another working
directory.

## Endpoints

- `GET /health`
- `GET /api/hardware/processors?search=threadripper`
- `GET /api/hardware/processors/:name`
- `POST /api/estimates/embodied`
- `POST /api/estimates/operational-energy`
- `POST /api/estimates/operational-carbon`
- `GET /api/grid-intensity?region=Indonesia&year=2020`
- `GET /api/grid-intensity/regions`
- `GET /api/stec/processors?type=CPU&status=point&page=1&pageSize=50`
- `GET /api/stec/processors/options`
- `GET /api/stec/processors/:name`
- `GET /api/comparison`
- `GET /api/benchmarks/resnet50`
- `GET /api/benchmarks/resnet50/recommendations?processorName=<CarbonSet product>`
- `POST /api/estimates/stec`
- `POST /api/estimates/cci`

`operational-energy` returns kWh only. `operational-carbon` performs an explicit
region/year lookup from the OWID/Ember lifecycle snapshot at
`data/raw/environmental/owid-lifecycle-carbon-intensity.csv`, converts
gCO2e/kWh to kgCO2e/kWh, and returns provenance metadata. Missing region/year
data returns `404`; there is no silent fallback.
`stec` delegates to `ml-engine/carbon/stec.py` and returns location-based,
cradle-to-gate die STEC with its assumptions.
The server recomputes the CarbonSet STEC inventory at startup using
`ml-engine/carbon/stec_batch.py`. The list endpoint supports `search`, `type`
(`CPU`/`GPU`), `status` (`point`/`range`/`incomplete`), `page`, and `pageSize`
(maximum 200). A multi-country fab assumption returns min/max values and no
single point estimate. Unsupported chiplet node parameters are marked
incomplete. The options endpoint returns compact processor labels for the
frontend selector. `POST /api/estimates/stec` looks up the location-based
grid factor using `manufacturingRegion` and `manufacturingYear`; callers do
not pass an arbitrary grid factor.

`cci` requires `totalCarbonKgCo2e`, `completedComputeWork`, `workloadUnit`,
`lifecycleBoundary`, and `analysisPeriod`. It returns carbon per completed
workload unit.

The embodied endpoint runs the experimental Random Forest artifact at
`ml-engine/artifacts/embodied_carbon_model.joblib` and returns a
`model_prediction` with its unit, boundary, dataset version, and model type.
This remains an experimental estimator, not a reported or measured LCA value.

`GET /api/comparison` returns one record per CarbonSet processor, pairing its
embodied-model prediction with its batch STEC result. The endpoint predicts the
inventory in one Python batch and caches the result for the backend process.
These values have different lifecycle boundaries and must not be added or
interpreted as competing predictions for the same target.

`GET /api/benchmarks/resnet50` serves the CarbonSet-mapped rows from
`data/processed/resnet50-carbonset-benchmark.csv`, derived from the supplied
MLPerf ResNet50 Offline results and device mapping. It joins each exact
CarbonSet product to `Emb_Carbon_Mean` and Min/Max values, multiplies these by
the number of inference devices, and compares them with whole-system MLPerf
throughput. No power, TDP, operational carbon, or CCI is used. Rows are ranked
only in cohorts that include at least two CarbonSet products and share the
suite version, system type, configuration class (MaxQ/non-MaxQ), and input precision.
Host/server embodied carbon is excluded; results are screening trade-offs,
not a complete system footprint.

After an existing CarbonSet processor's carbon calculation, the frontend calls
`GET /api/benchmarks/resnet50/recommendations?processorName=...`. It suggests
only a different CarbonSet product from the same benchmark cohort whose
system-level inference-device embodied carbon is no higher and throughput is
higher than a benchmark system using the selected product. No matching cohort
or no qualifying candidate is reported explicitly; custom processors do not
receive benchmark recommendations.
