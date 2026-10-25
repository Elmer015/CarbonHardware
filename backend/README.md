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
- `POST /api/estimates/stec`
- `POST /api/estimates/cci`
- `POST /api/estimates/uncertainty`

`operational-energy` returns kWh only. It deliberately returns
`carbonStatus: "pending_grid_intensity"` because no grid factor is assumed.
`stec` delegates to `ml-engine/carbon/stec.py` and returns location-based,
cradle-to-gate die STEC with its assumptions.

`cci` requires `totalCarbonKgCo2e`, `completedComputeWork`, `workloadUnit`,
`lifecycleBoundary`, and `analysisPeriod`. It returns carbon per completed
workload unit.

`uncertainty` accepts either `lowerValue`, `centralValue`, and `upperValue`,
or an array of at least two `samples`. It returns an evidence-bounded interval
and never claims calibrated confidence coverage.

The embodied endpoint runs the experimental Random Forest artifact at
`ml-engine/artifacts/embodied_carbon_model.joblib` and returns a
`model_prediction` with its unit, boundary, dataset version, and model type.
This remains an experimental estimator, not a reported or measured LCA value.
