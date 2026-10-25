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

`operational-energy` returns kWh only. It deliberately returns
`carbonStatus: "pending_grid_intensity"` because no grid factor is assumed.
`stec` delegates to `ml-engine/carbon/stec.py` and returns location-based,
cradle-to-gate die STEC with its assumptions.

The embodied endpoint currently validates the request contract and returns
`202 model_pending`; the trained model integration will be added separately.
