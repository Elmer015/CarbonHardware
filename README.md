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

### Grid intensity

Snapshot lokal OWID/Ember digunakan sebagai sumber lifecycle grid intensity:

```text
data/raw/environmental/owid-lifecycle-carbon-intensity.csv
```

Lookup dilakukan berdasarkan lokasi dan tahun, bukan input angka mentah user:

```http
GET /api/grid-intensity?region=Indonesia&year=2020
GET /api/grid-intensity/regions
```

Nilai asli dalam `gCO2e/kWh` dikonversi ke `kgCO2e/kWh` dengan membagi 1.000.
Jika region/tahun tidak tersedia, API mengembalikan `404` dan tidak memakai
fallback diam-diam.

### Operational carbon

```http
POST /api/estimates/operational-carbon
```

Contoh request:

```json
{
  "tdpW": 180,
  "hoursPerDay": 8,
  "usageYears": 5,
  "utilization": 0.7,
  "daysPerYear": 365,
  "region": "Indonesia",
  "analysisYear": 2020
}
```

Contoh hasil utama:

```json
{
  "electricityKwh": 1839.6,
  "gridIntensityKgCo2ePerKwh": 0.68515,
  "operationalCarbonKgCo2e": 1260.93294
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

## Status implementasi

Sudah tersedia:

- lookup processor dari CarbonSet;
- mode existing dan custom pada kontrak API;
- validasi input backend;
- perhitungan operational energy tanpa grid intensity default;
- kalkulasi STEC location-based;
- integrasi Node.js ke Python STEC engine;
- metadata boundary, unit, dan asumsi.
- snapshot OWID/Ember lifecycle grid intensity;
- lookup grid intensity berdasarkan region dan tahun;
- operational carbon dalam `kg CO2e`;
- CCI yang menggabungkan embodied dan operational carbon.

Belum tersedia:

- integrasi model embodied `joblib`;
- batch pipeline seluruh workbook STEC;
- market-based attribution;
- provenance lokasi fab yang lengkap per produk;
- pemodelan chiplet dengan node dan fab berbeda.

## Catatan metodologi

Operational energy tidak sama dengan operational carbon. Tanpa grid intensity
yang memiliki sumber dan periode, aplikasi hanya melaporkan `kWh` dan tidak
menghasilkan `kg CO2e`.

STEC saat ini merupakan estimasi location-based pada level die. Hasil dapat
menggunakan asumsi lokasi fab, proxy process node, atau tahun rilis sebagai
proxy tahun manufaktur. Semua asumsi tersebut harus tetap dicatat saat hasil
digunakan dalam laporan penelitian.