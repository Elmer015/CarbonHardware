# CarbonHardware

CarbonHardware adalah aplikasi penelitian untuk mengestimasi embodied carbon,
operational energy, dan STEC (Spatial-Temporal Embodied Carbon) pada hardware
processor.

## Struktur project

```text
backend/       Node.js/Express API
frontend/      React/Vite user interface
ml-engine/     Python calculation and modeling engine
data/          CarbonSet dan artefak data penelitian
database/      Schema dan seed database
docs/          Dokumentasi metodologi dan hasil penelitian
```

## Menjalankan backend

Pastikan Node.js dan Python tersedia, lalu jalankan:

```powershell
cd backend
npm install
npm start
```

Backend berjalan pada:

```text
http://localhost:3000
```

Endpoint root menampilkan daftar endpoint:

```text
GET http://localhost:3000/
```

## Endpoint backend

### Health check

```http
GET /health
```

### Processor dari CarbonSet

```http
GET /api/hardware/processors
GET /api/hardware/processors?search=Threadripper
GET /api/hardware/processors/:name
```

Backend membaca data dari:

```text
data/raw/carbonset/CarbonSet.csv
```

### Embodied carbon

```http
POST /api/estimates/embodied
```

Existing processor:

```json
{
  "inputMode": "existing",
  "processorName": "AMD Ryzen 9 5950X"
}
```

Custom processor:

```json
{
  "inputMode": "custom",
  "processorName": "Research CPU",
  "processSizeNm": 7,
  "tdpW": 250,
  "dieSizeMm2": 400,
  "dies": 2,
  "avgDieAreaMm2": 200
}
```

Endpoint ini menjalankan artifact Random Forest eksperimental dan
mengembalikan `model_prediction` beserta unit, boundary, dataset version, dan
model type. Nilai tersebut bukan reported atau measured LCA.

### Operational energy

```http
POST /api/estimates/operational-energy
```

Contoh request:

```json
{
  "tdpW": 180,
  "hoursPerDay": 8,
  "usageYears": 5,
  "utilization": 0.7,
  "daysPerYear": 365
}
```

Endpoint ini menghasilkan estimasi listrik dalam `kWh`. Grid intensity belum
digunakan, sehingga response memiliki:

```json
{
  "carbonStatus": "pending_grid_intensity"
}
```

### STEC

```http
POST /api/estimates/stec
```

Contoh request:

```json
{
  "inputMode": "custom",
  "processorName": "Research CPU",
  "processNodeNm": 28,
  "dieAreaMm2": 100,
  "gridIntensityGCo2ePerKwh": 561,
  "manufacturingRegion": "Taiwan",
  "manufacturingYear": 2022
}
```

Endpoint ini meneruskan kalkulasi ke
[`ml-engine/carbon/stec.py`](./ml-engine/carbon/stec.py) dan menghasilkan
location-based die STEC dengan boundary `cradle-to-gate die manufacturing`.

### STEC per processor (CI otomatis dari evidence)

```http
GET  /api/estimates/stec/regions
POST /api/estimates/stec/processor
```

```json
{
  "inputMode": "existing",
  "processorName": "AMD Ryzen 9 5950X",
  "manufacturingRegion": null,
  "manufacturingYear": null
}
```

Grid intensity diambil dari `data/raw/grid` (OWID/Ember), lokasi fab dari
`data/stec` (provenance produk, chiplet, atau aturan vendor/node), dan tahun
rilis dipakai sebagai proxy tahun manufaktur jika tidak ada data. Response
memuat `status` (`point`, `range`, `incomplete`), `location.level`, rincian
per region atau per die chiplet, baseline global, status market-based, dan
`warnings`. Untuk processor custom, `manufacturingRegion` dan
`manufacturingYear` wajib.

Backend memanggil Python melalui `PYTHON_COMMAND` (default `python`). Jika
`python` di Windows hanya alias Microsoft Store, set path Python yang benar:

```powershell
$env:PYTHON_COMMAND = "C:\path\ke\python.exe"
npm start
```

### Batch dan workbook STEC

```powershell
python ml-engine/carbon/stec_batch.py
python ml-engine/experiments/build_stec_workbook.py
```

Menghasilkan `data/processed/stec-per-chip.csv`,
`data/processed/stec-batch-summary.json`, dan
`data/processed/Analisis_STEC_CPU_GPU.xlsx`.

### CCI

```http
POST /api/estimates/cci
```

```json
{
  "totalCarbonKgCo2e": 20,
  "completedComputeWork": 4,
  "workloadUnit": "completed training run",
  "lifecycleBoundary": "embodied plus operational",
  "analysisPeriod": "2025"
}
```

Response utamanya adalah `5 kg CO2e per completed training run`. Workload
harus didefinisikan agar CCI dapat dibandingkan secara valid.

### Uncertainty

```http
POST /api/estimates/uncertainty
```

Untuk interval CarbonSet:

```json
{
  "lowerValue": 5.65,
  "centralValue": 7.74,
  "upperValue": 13.14,
  "unit": "kg_co2e",
  "source": "CarbonSet modeled range",
  "uncertaintyKind": "source_range",
  "method": "CarbonSet min/mean/max"
}
```

Endpoint juga menerima `samples` untuk menghasilkan empirical quantiles. Hasil
sample-based diberi label `not calibrated coverage`.

### Lifecycle: operational carbon, CCI final, dan uncertainty

```http
GET  /api/estimates/grid/regions
POST /api/estimates/lifecycle
```

```json
{
  "inputMode": "existing",
  "processorName": "AMD Ryzen Threadripper 1900X",
  "usage": { "hoursPerDay": 8, "daysPerYear": 365, "usageYears": 5, "utilization": 0.7,
             "usageRegion": "Indonesia", "gridYear": 2024 },
  "workload": { "completedComputeWork": 14600, "workloadUnit": "compute-hour" },
  "distributions": {
    "tdpW": { "min": 150, "mostLikely": 180, "max": 220 },
    "utilization": { "min": 0.4, "mostLikely": 0.7, "max": 0.95 },
    "gridIntensityKgCo2ePerKwh": { "min": 0.55, "max": 0.8 }
  }
}
```

Perhitungan (Python, `ml-engine/carbon/lifecycle.py`):

```text
electricity_kwh = TDP_W / 1000 * hours_per_day * days_per_year * usage_years * utilization
operational_kg  = electricity_kwh * grid_g_per_kwh / 1000
total_kg        = embodied_kg + operational_kg
CCI_final       = total_kg / completed_compute_work
```

- Grid intensity diambil dari `data/grid/grid-intensity.csv`
  (`region,year,grid_intensity_g_co2e_per_kwh,source,basis`; Our World in Data /
  Ember, location-based). Tidak ada interpolasi; region/tahun yang tidak ada
  menghasilkan `status: operational_pending_grid` dan CCI `embodied_only`.
  Nilai grid lain boleh dikirim lewat `gridIntensityKgCo2ePerKwh` asalkan
  disertai `gridIntensitySource`.
- Uncertainty: Monte Carlo (default 10.000 sampel, seed 42) dengan distribusi
  segitiga `{min, mostLikely, max}`. Input tanpa distribusi ditahan konstan.
  Untuk grid, `mostLikely` default adalah nilai bersumber dari tabel.
- Rentang embodied: CarbonSet min/max untuk processor existing; untuk custom,
  interval empiris 90% dari residual out-of-fold model
  (`ml-engine/artifacts/embodied_prediction_interval.json`, dibuat oleh
  `ml-engine/experiments/prediction_interval.py`).
- Output memuat P2.5–P97.5 untuk embodied, electricity, operational, total, dan
  CCI, serta korelasi rank tiap input terhadap total. Interval ini adalah
  propagasi input, bukan confidence interval terkalibrasi.

Membangun ulang tabel grid dari data mentah OWID:

```powershell
python ml-engine/carbon/grid_intensity.py --build
```

## Status implementasi

Sudah tersedia:

- lookup processor dari CarbonSet;
- mode existing dan custom pada kontrak API;
- validasi input backend;
- perhitungan operational energy tanpa grid intensity default;
- kalkulasi STEC location-based;
- integrasi Node.js ke Python STEC engine;
- metadata boundary, unit, dan asumsi;
- resolver evidence STEC (lokasi fab, tahun, yield, market-based, chiplet);
- batch pipeline STEC untuk seluruh CarbonSet dan workbook yang dapat dibangun ulang;
- integrasi frontend ke API STEC (form lokasi/tahun dan kartu hasil STEC);
- market-based attribution (hanya dengan faktor bersumber);
- pemodelan chiplet dengan node dan fab berbeda (4 produk AMD);
- operational carbon (kg CO2e) dengan grid intensity location-based bersumber;
- total carbon dan CCI final (embodied + operational);
- uncertainty custom processor (interval empiris model) dan propagasi Monte
  Carlo untuk operational, total, dan CCI.

Belum / ditunda:

- definisi workload penelitian final (saat ini unit workload diisi pengguna);
- uncertainty STEC (STEC di-hold);
- database (ditunda).

Mekanisme siap, data bersumber belum ada:

- tahun manufaktur aktual (`data/stec/manufacturing-years.csv`);
- yield per node/foundry/tahun (`data/stec/yields.csv`);
- faktor market-based per foundry/tahun (`data/stec/market-factors.csv`);
- provenance fab per produk untuk produk di luar `fab-provenance.csv`
  (masih memakai asumsi `fab-rules.csv`).

## Catatan metodologi

Operational energy tidak sama dengan operational carbon. Tanpa grid intensity
yang memiliki sumber dan periode, aplikasi hanya melaporkan `kWh` dan tidak
menghasilkan `kg CO2e`. Grid intensity satu tahun ditahan konstan sepanjang
usage lifetime; ini dicatat di `warnings` setiap hasil.

STEC saat ini merupakan estimasi location-based pada level die. Hasil dapat
menggunakan asumsi lokasi fab, proxy process node, atau tahun rilis sebagai
proxy tahun manufaktur. Semua asumsi tersebut harus tetap dicatat saat hasil
digunakan dalam laporan penelitian.