# Dokumentasi Proyek CarbonHardware

## Status dokumen

Dokumentasi teknis dan metodologi ini diselaraskan dengan source code, dataset, model, dan tes yang tersedia pada **18 November 2026**. Dokumen ini menjelaskan perilaku implementasi saat ini, bukan rancangan masa depan. Nilai karbon adalah estimasi/model output sesuai batas masing-masing sumber, bukan pengukuran universal atau LCA lengkap. Panduan mencakup provenance data, pemrosesan, endpoint, tampilan, rumus, asumsi, dan cara membaca hasil.

## Daftar isi

1. Ringkasan eksekutif
2. Tujuan, ruang lingkup, dan batas klaim
3. Arsitektur aplikasi
4. Alur pengguna dan API
5. Dataset dan provenance
6. Pemrosesan data dan model embodied
7. Metode karbon dan metrik
8. STEC: metode dan evidence
9. Perbandingan karbon penggantian
10. Evaluasi, tes, dan reproducibility
11. Batasan dan interpretasi yang aman
12. Rekomendasi pengembangan
13. Glosarium
14. Peta file utama

## 1. Ringkasan eksekutif

CarbonHardware adalah aplikasi riset yang menggabungkan estimasi embodied carbon prosesor, estimasi listrik dan emisi fase penggunaan, lookup intensitas karbon grid, perhitungan STEC die manufacturing, Compute Carbon Intensity (CCI), serta skenario carbon payback untuk penggantian prosesor. Aplikasi terdiri dari frontend React/Vite, backend REST Node.js/Express, dan engine Python untuk prediksi embodied serta perhitungan STEC. CSV dan artifact model adalah sumber runtime; backend tidak menggunakan database untuk penyimpanan runtime.

Frontend memiliki tiga halaman navigasi: estimasi embodied/operational carbon, STEC per prosesor, dan perbandingan baseline embodied dengan STEC. Halaman estimasi juga dapat menampilkan perbandingan carbon payback untuk kandidat CarbonSet sejenis.

| Area | Kondisi implementasi | Interpretasi |
|---|---|---|
| Embodied baseline | Random Forest terintegrasi melalui artifact joblib; eksperimental | Prediksi atas label modeled CarbonSet, bukan LCA terukur untuk unit tertentu |
| Operational energy/carbon | Endpoint dan form tersedia; daya diproksikan dengan TDP | Skenario, bukan pengukuran daya aktual |
| STEC | Dataset batch per chip dan kalkulator tersedia | Location-based cradle-to-gate die manufacturing; hasil berstatus point, range, atau incomplete |
| CCI | Endpoint dan input workload tersedia | Valid hanya bila definisi kerja, periode, dan boundary konsisten |
| Perbandingan penggantian | Kandidat CPU/GPU sejenis dari CarbonSet dibandingkan berdasarkan carbon payback | Skenario karbon; kesetaraan workload, performa, form factor, dan kecocokan hardware tidak divalidasi |
| Database | Tidak digunakan pada alur runtime yang diperiksa | CSV lokal adalah sumber runtime |

Fokus saat ini adalah emisi karbon, bukan benchmark performa. Aplikasi tidak memakai dataset benchmark atau metrik performa untuk menghasilkan estimasi maupun menyaring rekomendasi. Label `CPU` atau `GPU` juga belum membedakan perangkat laptop dari desktop/workstation.

## 2. Tujuan, ruang lingkup, dan batas klaim

### 2.1 Tujuan

Produk membantu membandingkan besaran jejak karbon hardware komputasi dengan menampilkan sumber, unit, boundary, status evidence, serta asumsi. Embodied carbon, operational carbon, STEC, CCI, dan massa e-waste adalah besaran berbeda; angka-angka itu tidak boleh dijumlahkan atau dibandingkan tanpa memeriksa functional unit dan boundary.

### 2.2 Yang dihitung

- **Embodied baseline:** prediksi model atas `Emb_Carbon_Mean` CarbonSet dari lima fitur prosesor.
- **Operational energy/carbon:** listrik dan emisi penggunaan dari TDP sebagai proxy daya, skenario pemakaian, dan intensitas grid location-based lifecycle.
- **STEC:** estimasi location-based untuk manufaktur die berdasarkan node, luas die, parameter manufaktur, dan intensitas listrik lokasi-tahun.
- **CCI:** total karbon yang dikirim ke endpoint dibagi jumlah pekerjaan komputasi selesai yang didefinisikan pengguna.
- **E-waste dan custom PC:** modul Python tersedia untuk alokasi massa dan kalkulasi BOM, tetapi belum menjadi alur API/frontend utama.

### 2.3 Yang tidak boleh diklaim

Aplikasi bukan LCA lengkap untuk server; bukan pengukur konsumsi daya aktual; tidak menghitung otomatis workload selesai dari FLOPS/runtime; tidak menghitung emisi market-based kontrak listrik; dan tidak menjamin prediksi berlaku untuk semua vendor, generasi, node, atau produk di luar distribusi data. Tes yang lulus membuktikan kontrak teknis tertentu, bukan kebenaran seluruh input sumber atau validitas ilmiah universal.

Carbon payback bukan perkiraan sisa umur prosesor dan bukan ramalan tanggal kerusakan. Ia menjawab pertanyaan bersyarat: **setelah beralih ke kandidat tertentu, berapa lama penghematan operasional dalam skenario yang dimasukkan diperlukan untuk menutup embodied carbon kandidat?** Aplikasi tidak mengevaluasi performa, kompatibilitas, workload setara, harga, biaya penggantian, atau akhir masa pakai.

## 3. Arsitektur aplikasi

### 3.1 Komponen

| Komponen | Tanggung jawab |
|---|---|
| Frontend React 18 + Vite | Form existing/custom, hasil kalkulasi, STEC, dan perbandingan |
| Backend Node.js + Express | REST API, validasi input, load CSV, pencocokan data, serta perhitungan ringan |
| Python engine | Prediksi embodied dengan artifact model dan kalkulator STEC |
| CarbonSet CSV | Profil hardware serta embodied Min/Mean/Max |
| Grid-intensity CSV | Data intensitas listrik per entitas/wilayah dan tahun |
| STEC CSV/evidence | Hasil batch dan evidence fab, node, manufacturing year, serta chiplet |

Alur umumnya adalah **UI → REST API → layanan domain → CSV dan/atau subprocess Python**. Backend memuat CarbonSet, intensitas grid, dan inventori STEC saat startup. Prediksi embodied dan STEC custom dijalankan backend dengan Python sebagai subprocess; payload JSON dikirim lewat stdin dan hasil JSON dibaca dari stdout. Kegagalan load data atau proses kalkulasi harus terlihat sebagai error, bukan angka sukses pengganti.

### 3.2 Runtime dan konfigurasi

Backend berjalan pada port `3000` secara default. `PORT`, `CARBONSET_PATH`, `GRID_INTENSITY_PATH`, dan `PYTHON_COMMAND` dapat dioverride lewat environment. Jalankan backend dari direktori `backend/`, karena default path dataset relatif terhadap direktori kerja tersebut. Frontend memakai `VITE_API_URL` atau default `http://localhost:3000`.

Tidak ditemukan koneksi database aktif pada jalur runtime yang diperiksa. Adanya folder/schema database bukan bukti bahwa aplikasi menyimpan data ke database.

### 3.3 Urutan pemrosesan ketika aplikasi dijalankan

1. `backend/src/server.js` membaca CarbonSet dan snapshot intensitas grid ke memori.
2. Pada startup yang sama, backend menjalankan `ml-engine/carbon/stec_batch.py --json`. Engine menghitung ulang inventori STEC dari CarbonSet, CSV evidence, dan CSV intensitas grid; backend tidak hanya membaca salinan `data/processed/stec-per-chip.csv`.
3. Frontend meminta daftar prosesor, opsi STEC, daftar region, dan data halaman sesuai kebutuhan.
4. Prediksi embodied dan STEC custom dijalankan sebagai subprocess Python. Input dikirim sebagai JSON melalui stdin; hasil JSON dibaca dari stdout. Tidak ada job queue atau riwayat perhitungan yang disimpan.
5. Untuk `/api/comparison`, prediksi baseline seluruh prosesor dilakukan secara batch dan hasilnya di-cache dalam memori selama proses backend hidup. Cache ini bukan penyimpanan permanen.

Jika file wajib tidak ada, skema tidak cocok, atau Python tidak bisa dijalankan, server/API melaporkan kegagalan. Hasil tidak seharusnya ditafsirkan sebagai nol ketika proses gagal.

## 4. Alur pengguna dan API

### 4.1 Alur estimasi karbon

1. Pengguna memilih prosesor CarbonSet **existing** atau memasukkan lima fitur prosesor **custom**.
2. Pengguna memasukkan skenario operasional: jam/hari, tahun pemakaian, utilisasi, hari/tahun, wilayah grid, dan tahun analisis.
3. Pengguna memasukkan jumlah workload selesai dan unitnya untuk CCI.
4. Frontend meminta embodied prediction, operational carbon (yang menyertakan energy dan grid factor), lalu CCI standar.
5. Frontend juga mengambil hasil STEC inventori untuk prosesor **existing**, atau meminta kalkulasi STEC custom dari node, luas die, wilayah manufaktur, dan tahun manufaktur yang dimasukkan pengguna.
6. Setelah estimate utama berhasil, UI menampilkan dua skenario: embodied model + operational carbon; dan STEC + operational carbon. CCI dihitung terpisah untuk masing-masing skenario dan diberi boundary yang berbeda.
7. Jika mode **existing**, aplikasi dapat menampilkan perbandingan carbon payback dengan kandidat CarbonSet bertipe sama.

Nilai STEC **tidak ditambahkan** ke embodied model. STEC hanya mencakup die manufacturing dan tumpang tindih dengan embodied lifecycle estimate, sehingga skenario STEC ditampilkan sebagai alternatif partial-boundary, bukan sebagai tambahan total. Perbandingan penggantian adalah analisis skenario terpisah dari kedua CCI dan bukan rekomendasi tanggal penggantian yang tervalidasi. Detail logikanya ada pada Bagian 9.

### 4.2 Halaman frontend

| Halaman | Fungsi |
|---|---|
| `/` dan `/estimate` | Estimasi embodied/operational carbon, CCI, serta perbandingan carbon payback untuk kandidat prosesor existing |
| `/stec` | Pencarian/detail STEC dan kalkulator custom |
| `/comparison` | Perbandingan baseline embodied prediction dan STEC; keduanya ditampilkan terpisah |

Navigasi menggunakan History API di frontend. Perbandingan carbon payback berada pada halaman estimasi karbon.

### 4.3 Endpoint utama

| Endpoint | Fungsi | Batas penting |
|---|---|---|
| `GET /` | Metadata service dan daftar endpoint | Bukan halaman dokumentasi interaktif |
| `GET /health` | Health check | Status service |
| `GET /api/hardware/processors` | Daftar/pencarian prosesor CarbonSet | Sumber data lokal |
| `GET /api/hardware/processors/:name` | Detail prosesor | Tidak ditemukan menghasilkan 404 |
| `POST /api/estimates/embodied` | Prediksi embodied | Existing atau custom; Python + artifact model |
| `POST /api/estimates/operational-energy` | Energi listrik | Menghasilkan kWh dari TDP proxy dan skenario |
| `POST /api/estimates/operational-carbon` | Operational emissions | Mengembalikan emisi untuk durasi penggunaan dan estimasi emisi tahunan |
| `POST /api/estimates/carbon-replacement-comparison` | Perbandingan karbon penggantian | Kandidat CarbonSet bertipe sama; asumsi workload setara, tanpa evaluasi performa |
| `POST /api/estimates/stec` | Estimasi STEC | Existing/custom; memerlukan grid factor dan node tersedia |
| `POST /api/estimates/cci` | Karbon per workload | `completedComputeWork` wajib lebih dari nol |
| `GET /api/grid-intensity?region=...&year=...` | Lookup intensitas grid | Region dan tahun dicari; tidak ada fallback |
| `GET /api/grid-intensity/regions` | Daftar region | Dari snapshot lokal |
| `GET /api/stec/processors` | Daftar/filter STEC | Filter search/type/status; page size maksimum 200 |
| `GET /api/stec/processors/options` | Opsi dropdown STEC | Label ringkas produk/type/vendor/status |
| `GET /api/stec/processors/:name` | Detail STEC | Tidak ditemukan menghasilkan 404 |
| `GET /api/comparison` | Batch baseline + STEC | Dua hasil tidak additive |

### 4.4 Validasi input yang tampak pada UI

Form custom meminta process size (nm), TDP (W), die size (mm²), jumlah die, dan average die area (mm²). Agar skenario STEC custom dapat dihitung, pengguna juga memilih process node STEC secara eksplisit, manufacturing region, dan manufacturing year (1990–2025). Node STEC tidak otomatis disimpulkan dari process size. Skenario operasional meminta jam/hari (maksimum 24), umur pemakaian, utilisasi 0–100%, hari/tahun (maksimum 366), region, dan tahun analisis (UI membatasi 1990–2025 sesuai snapshot yang tersedia). CCI meminta workload positif dan unit berupa teks. Nilai operasional adalah asumsi pengguna, bukan telemetry.

Endpoint lookup grid memerlukan kecocokan region/tahun persis pada snapshot; data yang hilang memberi 404. Endpoint API menolak input invalid dengan error 4xx dan error handler menyampaikan kegagalan.

### 4.5 Kontrak request dan response estimasi

Semua endpoint POST menerima JSON. Contoh berikut menunjukkan field penting, bukan seluruh metadata response.

#### Prediksi embodied

Untuk perangkat katalog:

```json
{
  "inputMode": "existing",
  "processorName": "AMD Ryzen 9 5950X"
}
```

Untuk perangkat di luar katalog:

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

Response berisi `status`, `value`, `unit`, `valueKind`, `source`, `functionalUnit`, `boundary`, metadata model, dan objek `processor`. Lima nilai fitur wajib model adalah process size, TDP, `DieSizeValue`, jumlah die, dan average die area. Pada mode custom, `dies` default ke 1 dan `avgDieAreaMm2` default ke `dieSizeMm2` hanya jika field tersebut tidak dikirim. Custom estimate tidak memakai field `processorType` untuk memprediksi nilai, tetapi tipe itu tetap dipakai oleh tampilan/perbandingan.

#### Operational energy

```json
{
  "tdpW": 180,
  "hoursPerDay": 8,
  "usageYears": 5,
  "utilization": 0.7,
  "daysPerYear": 365
}
```

Response utama: `electricityKwh`, `unit`, `calculationStatus`, `carbonStatus`, dan objek `assumptions`. Utilisasi API adalah pecahan 0–1; UI menerima persen dan membaginya dengan 100. Endpoint ini hanya menghasilkan energi dan menandai `carbonStatus` sebagai `pending_grid_intensity`.

#### Operational carbon

Request memakai field operational energy di atas ditambah `region` dan `analysisYear`. Response menyertakan `operationalCarbonKgCo2e`, `electricityKwh`, `gridIntensityKgCo2ePerKwh`, `annualOperationalCarbonKgCo2e`, record `gridIntensity` beserta provenance, dan `analysisYear`. Nilai tahunan selalu dihitung memakai skenario yang sama dengan `usageYears: 1`; nilai total menggunakan periode `usageYears` dari request.

#### CCI

```json
{
  "totalCarbonKgCo2e": 100,
  "completedComputeWork": 10000000,
  "workloadUnit": "completed inference request",
  "lifecycleBoundary": "embodied plus lifecycle operational",
  "analysisPeriod": "5 years"
}
```

`completedComputeWork` wajib lebih besar dari nol. Response memberikan `cciKgCo2ePerWorkload` dan mengulang numerator, denominator, unit workload, boundary, serta periode agar angka dapat ditafsirkan. Endpoint menerima nilai karbon total dari pemanggil; pembentukan total embodied + operational dilakukan frontend untuk alur utama.

### 4.6 Kontrak API lain

| Endpoint | Parameter penting | Response atau perilaku |
|---|---|---|
| `GET /api/grid-intensity?region=Indonesia&year=2020` | Nama region dan tahun integer | Record dengan `gramsCo2ePerKwh`, `kgCo2ePerKwh`, `code`, dan metadata sumber |
| `GET /api/grid-intensity/regions` | Tidak ada | `{ "regions": [...] }` dari dataset lokal |
| `GET /api/stec/processors?type=CPU&status=range&page=1&pageSize=50&search=AMD` | `type`: CPU/GPU; `status`: point/range/incomplete; `pageSize`: 1–200 | `{ total, page, pageSize, results }`; search mencocokkan nama produk/vendor |
| `GET /api/stec/processors/options?type=GPU` | Filter tipe opsional | `{ options: [{ product, type, vendor, status }] }` untuk dropdown |
| `GET /api/stec/processors/:name` | Nama produk persis | Satu record inventori STEC; nama path perlu URL-encode |
| `GET /api/hardware/processors?search=Threadripper` | Search opsional | Array katalog; daftar tidak dipaginasi |
| `GET /api/hardware/processors/:name` | Nama produk persis | Profil hardware publik; nama path perlu URL-encode |
| `GET /api/comparison` | Tidak ada | `results` per produk dan metadata; baseline dengan STEC **tidak additive** |

Endpoint STEC custom menerima `inputMode`, `processorName`, `processNodeNm`, `dieAreaMm2`, `manufacturingRegion`, dan `manufacturingYear`. Mode existing menerima `processorName`; luas die dan node dapat dioverride, jika tidak backend mengambil nilai CarbonSet. Response menyertakan `value`, unit, functional unit, boundary, faktor grid, lokasi/tahun, node, luas, dan asumsi parameter.

Endpoint `POST /api/estimates/carbon-replacement-comparison` menerima nama/tipenya prosesor, TDP saat ini, tanggal rilis saat ini (bila tersedia), pola operasional tahunan, region, dan tahun analisis. Response membawa `status`, emisi operasional tahunan prosesor saat ini, maksimal tiga `candidates`, `unit: "years"`, serta metadata metode/filter. Bentuk status dan arti setiap kandidat dibahas pada Bagian 9.

Endpoint `POST /api/estimates/upgrade-timeline` terpisah dari perbandingan kandidat dan tidak dipakai oleh halaman estimate. Request mencakup `carbonBudgetKgCo2e`, `embodiedCarbonKgCo2e`, `usageYears`, input operasional tahunan, `region`, dan `analysisYear`. Response memuat `status`, `currentCumulativeCarbonKgCo2e`, `annualOperationalCarbonKgCo2e`, serta `yearsToBudget` yang dapat bernilai `null` jika emisi operasional tahunan nol dan anggaran belum tercapai.

### 4.7 Error API dan validasi

| Kelas error | Arti umum | Contoh |
|---|---|---|
| 400 | Field wajib hilang, tipe/nilai tidak valid, atau batas skenario dilanggar | Utilisasi di luar 0–1, workload nol, tipe CPU/GPU tidak dikenal |
| 404 | Resource atau pasangan region-tahun tidak tersedia | Nama prosesor tidak ada, grid factor tidak ditemukan |
| 500 | Error internal pada request/API | Kesalahan tak terduga dicatat di backend log; error saat load data startup dapat menghentikan proses sebelum server menerima request |
| 502/503 | Engine Python tidak tersedia atau outputnya bukan JSON valid | Python executable tidak ditemukan atau subprocess menghasilkan payload yang tidak dapat diparse |

Error JSON menggunakan field `error`; `details` hanya ada bila handler menerima detail tambahan. Error 500 ditampilkan ke klien sebagai `Internal server error`, sementara detail teknis dicatat di log. Subprocess Python yang keluar dengan exit code non-zero dipetakan sebagai error 400 oleh service saat ini, sehingga error dependency/script tidak selalu mendapat status HTTP khusus. Frontend mempertahankan hasil karbon utama bila request rekomendasi saja gagal, dan menampilkan pesan error rekomendasi secara terpisah.

### 4.8 Apa yang dilihat pengguna di tiap halaman

| Halaman | Alur tampilan |
|---|---|
| Estimate (`/`, `/estimate`) | Pilih prosesor existing atau custom; masukkan skenario; hasil/status berada setelah form. Menampilkan kartu standard (embodied model + operational) dan kartu STEC-based (STEC + operational), CCI masing-masing, status/rentang/provenance STEC, sumber grid, serta panel kandidat carbon payback. |
| STEC (`/stec`) | Cari produk CarbonSet, filter CPU/GPU, lihat point/range/incomplete dan provenance; atau hitung chip custom dengan node, luas die, fab country, dan tahun. |
| Baseline vs STEC (`/comparison`) | Pilih tipe dan prosesor; hasil model embodied dan STEC ditampilkan berdampingan dengan boundary masing-masing. Nilai tidak dijumlahkan. |

Frontend saat ini menempatkan profil prosesor dan bagian scenario/CCI di dalam form, lalu dua kartu hasil di bawahnya. Kartu standard menjumlahkan embodied-model prediction dan operational carbon. Kartu STEC menjumlahkan nilai/rentang STEC dengan operational carbon; status `incomplete` atau request error ditampilkan sebagai tidak tersedia, bukan nol. CCI STEC memakai denominator workload yang sama, tetapi hanya untuk boundary STEC + operational. Kedua kartu tidak dijumlahkan satu sama lain. Layout berubah responsif untuk layar sempit. Angka dan label antarmuka ditampilkan dalam bahasa Inggris; dokumen ini menggunakan bahasa Indonesia untuk menjelaskan implementasi.

## 5. Dataset dan provenance

### 5.1 CarbonSet

`data/raw/carbonset/CarbonSet.csv` memiliki 1.320 baris dan 19 kolom. Kolom meliputi nama produk, tipe, tanggal rilis, process size, TDP, die size, vendor, jumlah die, average die area, serta nilai embodied/operational/total carbon Min/Mean/Max. Komposisi raw: 741 CPU dan 579 GPU. Ada 17 duplikasi baris identik; setelah penghapusan tersisa 1.303 observasi untuk pipeline model. Nama produk unik: 1.272.

Target `Emb_Carbon_Mean` adalah rata-rata output modeled ECO-CHIP dari 10.000 simulasi, bukan pengukuran langsung atau EPD untuk semua chip. Unit target adalah kg CO₂e. Nilai pada snapshot berkisar sekitar 0,504–117,937 kg CO₂e; distribusinya skew, sehingga metrik error ekstrem juga perlu dilihat.

#### Data dictionary CarbonSet

| Kelompok | Kolom sumber | Makna/pemakaian |
|---|---|---|
| Identitas | `Product` | Nama produk; dipakai sebagai group untuk split model dan nama prosesor runtime. |
| Identitas | `Type` | Kategori katalog CPU atau GPU. Tidak menyatakan laptop, desktop, workstation, atau server. |
| Identitas | `Release Date` | Tanggal rilis; digunakan sebagai metadata dan penyaring kandidat yang lebih baru, bukan tahun manufaktur terverifikasi. |
| Hardware | `Process Size (nm)` | Ukuran process node nominal yang dicatat dataset; bukan pengukuran geometri transistor yang independen. |
| Hardware | `TDP (W)` | Thermal Design Power. Dipakai sebagai fitur model dan proxy daya dalam skenario penggunaan. |
| Hardware | `DieSizeValue` | Kolom luas die yang dipakai sebagai fitur model, runtime hardware, dan input STEC batch. |
| Hardware | `Die Size (mm^2)` | Kolom luas die lain di sumber. Tidak identik dengan jaminan bahwa seluruh arsitektur/chiplet tercakup; STEC dapat memakai evidence chiplet terpisah. |
| Hardware | `Vendor` | Nama vendor, digunakan dalam pencarian dan fallback aturan provenance fab STEC. |
| Hardware | `#dies` | Jumlah die pada konfigurasi sumber; fitur model. |
| Hardware | `Avg Die Area` | Luas die rata-rata dalam konfigurasi sumber; fitur model. |
| Karbon embodied | `Emb_Carbon_Min`, `Emb_Carbon_Mean`, `Emb_Carbon_Max` | Ringkasan modeled embodied carbon yang disimpan CarbonSet. `Emb_Carbon_Mean` adalah target model dan embodied reference kandidat penggantian. |
| Karbon operasional | `Ope_Carbon_Min`, `Ope_Carbon_Mean`, `Ope_Carbon_Max` | Nilai operasional yang sudah ada pada sumber. Alur estimate menghitung ulang operational carbon dari TDP, skenario pemakaian, dan lookup grid, bukan memakai kolom ini sebagai telemetry. |
| Karbon total | `Tot_Carbon_Min`, `Tot_Carbon_Mean`, `Tot_Carbon_Max` | Ringkasan total pada sumber CarbonSet; bukan target regresi baseline saat ini dan tidak menggantikan perhitungan total UI. |

Runtime backend mengubah nama field menjadi camelCase. Daftar API hardware membuang kolom embodied Min/Mean/Max dan total Min/Mean/Max dari response publik. Loader katalog juga menyimpan satu record pertama per nama produk. Dengan demikian, **1.303 baris model bersih**, **1.272 nama produk unik runtime**, dan **1.320 baris raw** adalah hitungan berbeda dengan tujuan berbeda.

### 5.2 Dataset split dan inventori STEC

| File | Baris | Peran |
|---|---:|---|
| `data/interim/carbonset-cleaned.csv` | 1.303 | Observasi bersih untuk training |
| `data/processed/carbonset-train.csv` | 776 | Melatih kandidat estimator |
| `data/processed/carbonset-validation.csv` | 261 | Memilih model/konfigurasi |
| `data/processed/carbonset-test.csv` | 266 | Held-out evaluation |
| `data/processed/stec-per-chip.csv` | 1.272 | Inventori STEC per produk unik |

Split menggunakan `GroupShuffleSplit`, kolom `Product`, seed 42. Tujuannya mencegah produk yang sama muncul di train/validation/test. Banyak baris bukan jumlah hardware unik dan pemisahan berdasarkan produk tidak membuktikan generalisasi ke vendor/arsitektur/node baru.

Inventori STEC mencakup 733 CPU dan 539 GPU: 659 status `point`, 610 `range`, 3 `incomplete`. Confidence lokasi: unresolved 531, medium 408, high 251, low 52, mixed 30. Label confidence ini kategori evidence, bukan probabilitas terkalibrasi.

### 5.3 Intensitas grid listrik

`data/raw/environmental/owid-lifecycle-carbon-intensity.csv` memuat 6.332 baris, 238 entitas, tahun 1990–2025. Metadata snapshot menyebut Ember (2026) melalui Our World in Data, lifecycle carbon intensity of electricity, update 2026-06-30, diunduh 2026-10-25. Sumber berunit gCO₂e/kWh; backend membagi angka dengan 1.000 menjadi kgCO₂e/kWh. Basisnya lifecycle location-based, bukan faktor market-based PPA/REC. Kolom `Carbon intensity` lengkap pada snapshot; ada 312 nilai kosong pada `Code`, yang tidak dipakai untuk lookup. Lookup menggunakan nama `Entity` dan tahun persis, tanpa pencocokan alias/fallback.

| Kolom grid | Makna/pemakaian |
|---|---|
| `Entity` | Nama negara/wilayah; menjadi kunci lookup setelah normalisasi huruf besar-kecil dan trimming spasi. |
| `Code` | Kode entitas bila tersedia; boleh kosong dan tidak digunakan oleh lookup runtime. |
| `Year` | Tahun faktor intensitas listrik. |
| `Carbon intensity` | Lifecycle intensity dalam gCO₂e/kWh; backend mengonversi ke kgCO₂e/kWh dengan membagi 1.000. |

### 5.4 Perbandingan karbon penggantian

Perbandingan penggantian menggunakan metadata prosesor dan embodied carbon dari CarbonSet, tanpa dataset benchmark terpisah. Backend memilih kandidat bertipe sama yang lebih baru, berada dalam rentang tahun rilis katalog, dan memiliki TDP 50% hingga kurang dari TDP prosesor saat ini. Kandidat diurutkan berdasarkan estimasi carbon payback. Aturan ini adalah penyaringan awal dan tidak membuktikan kesetaraan workload atau kecocokan perangkat.

### 5.5 Evidence STEC dan inventori

Input evidence berada di `data/raw/stec/evidence/`:

| File | Isi/fungsi | Jumlah saat snapshot |
|---|---|---:|
| `fab-provenance.csv` | Bukti fab spesifik produk yang lebih kuat daripada rule generik | 11 baris |
| `fab-rules.csv` | Kandidat wilayah fab berdasarkan vendor, tipe, dan node atau wildcard | 12 baris |
| `chiplets.csv` | Informasi struktur/luas die chiplet untuk produk yang didukung | 8 baris |
| `manufacturing-years.csv` | Override tahun manufaktur yang didukung sumber | Tidak ada override terisi |

Hasil tersimpan/ekspor berada di `data/processed/stec-per-chip.csv` (1.272 produk, 24 kolom). Backend membangunnya kembali ketika startup melalui batch Python agar hasil runtime berasal dari source/evidence terkini. Kolom output mencakup identitas produk, node/luas, tahun dan status tahun, tingkat/confidence lokasi, kandidat fab, status point/range/incomplete, nilai STEC, indikator chiplet/yield/market-based, referensi CarbonSet, basis lokasi, dan warning.

Snapshot inventori memiliki 659 `point`, 610 `range`, dan 3 `incomplete`. Pada baris `range`, `stec_min_kg_co2e` dan `stec_max_kg_co2e` mewakili kandidat lokasi; nilai tunggal `stec_kg_co2e` tidak diisi. Pada status `incomplete`, tidak ada nilai estimasi yang dapat ditampilkan. `location_confidence` berisi unresolved 531, medium 408, high 251, low 52, dan mixed 30. Kategori tersebut mengikuti bukti yang dicatat, bukan probabilitas terkalibrasi.

#### Makna field utama inventori STEC

| Field | Makna |
|---|---|
| `product`, `type`, `vendor` | Identitas prosesor dari CarbonSet. |
| `node_nm`, `carbonset_die_area_mm2` | Node dan luas referensi CarbonSet yang digunakan sebagai input batch. |
| `manufacturing_year`, `manufacturing_year_status` | Tahun yang dipakai dan asal/statusnya (override bersumber atau proxy tahun rilis). |
| `location_level`, `location_confidence`, `candidate_regions` | Metode resolusi lokasi, kategori evidence, dan kandidat fab yang digunakan. |
| `status` | `point`, `range`, atau `incomplete`. |
| `stec_kg_co2e`, `stec_min_kg_co2e`, `stec_max_kg_co2e` | Nilai tunggal atau rentang lokasi dalam kg CO₂e. |
| `chiplet_applied`, `chiplet_die_area_mm2` | Menjelaskan apakah evidence luas komponen chiplet digunakan. |
| `global_baseline_stec_kg_co2e` | Nilai skenario pembanding dengan intensitas World, jika tersedia. |
| `yield_applied` | Boolean bahwa koreksi yield diterapkan; nilainya `false` pada batch saat ini. |
| `market_based_status` | Status faktor market-based; saat ini `not_available`. |
| `carbonset_emb_mean_kg_co2e`, `carbonset_emb_min_kg_co2e`, `carbonset_emb_max_kg_co2e` | Referensi embodied CarbonSet untuk pembacaan berdampingan, bukan komponen STEC. |
| `location_basis` | Catatan dasar pemilihan lokasi/provenance. |
| `warnings` | Catatan konflik, proxy, atau batasan bukti; kosong bila tidak ada warning yang tercatat. |

### 5.6 Sumber yang berbeda menjawab pertanyaan berbeda

| Sumber/kolom | Dipakai untuk | Tidak boleh dianggap sebagai |
|---|---|---|
| CarbonSet `Emb_Carbon_Mean` | Target training, input embodied kandidat penggantian | Pengukuran aktual pabrik untuk unit hardware pengguna |
| Model Random Forest | Prediksi baseline embodied dari lima fitur | LCA independen yang diverifikasi atau hasil performa |
| Input TDP + usage | Skenario energi dan emisi fase penggunaan | Pengukuran meter/watt telemetry |
| OWID/Ember grid factor | Lifecycle carbon intensity regional per tahun | Faktor kontraktual listrik perusahaan atau emisi marginal |
| STEC evidence dan node parameters | Die manufacturing location-based | Lifecycle penuh produk atau semua komponen komputer |
| User workload count | Penyebut CCI | Workload yang otomatis diuji/diukur oleh aplikasi |

`docs/dataset-documentation.md` menyimpan catatan fase assessment dan mencakup observasi historis sebelum dataset/model saat ini tersedia. Bila kalimat lama di sana menyebut folder data kosong atau training terblokir, itu bukan status runtime sekarang; gunakan snapshot file dan angka pada panduan ini untuk implementasi yang sedang didokumentasikan.

### 5.7 Referensi provenance yang tersedia

| Sumber | Informasi yang dipakai | Lokasi/versi yang direkam |
|---|---|---|
| CarbonSet paper, arXiv:2506.10373v1 | Unit `kg CO₂e` dan penjelasan CFP sebagai mean dari 10.000 simulasi ECO-CHIP | Versi suplai tercatat pada metadata model: `CarbonSet-arXiv-2506.10373v1-2026-10-13`; [halaman arXiv](https://arxiv.org/abs/2506.10373v1) |
| Ember (2026) via Our World in Data | Lifecycle carbon intensity listrik, semua gas rumah kaca dalam gCO₂e/kWh | Snapshot lokal dan metadata; periode 1990–2025; unduhan 2026-10-25; [chart source](https://ourworldindata.org/grapher/electricity-mix) |
| Zhang et al., Table 7 | Parameter node STEC yang dipakai implementasi Python | Direferensikan oleh `ml-engine/carbon/stec.py`; interpretasi proyek dicatat di `docs/research/Analisis_STEC_CPU_GPU.xlsx` |
| Repository implementation | Validasi, rumus, pemetaan API, status dan asumsi aktif | Source code CarbonHardware pada revision yang sedang didokumentasikan |

Tautan dan atribusi di atas menjelaskan provenance yang dicatat lokal; hal tersebut bukan pengganti pemeriksaan versi sumber, lisensi, atau verifikasi independen atas setiap nilai hardware.

## 6. Pemrosesan data dan model embodied

### 6.1 Cleaning dan fitur

Pipeline memeriksa skema, dtype, missingness, duplikasi, statistik numerik, indikasi unit, serta kandidat target. Nama kolom saja bukan bukti ground truth. Cleaning menolak target yang tidak terverifikasi, hanya mengonversi unit bila dukungannya eksplisit, membuang baris dengan target/fitur wajib invalid atau missing, dan tidak mengimputasi missing secara diam-diam. Pada snapshot CarbonSet, tidak ada target/fitur model missing dan 17 exact duplicates dihapus.

Model memakai lima fitur numerik:

1. `Process Size (nm)`
2. `TDP (W)`
3. `DieSizeValue`
4. `#dies`
5. `Avg Die Area`

Tidak ada scaling/imputation pada alur fitur ini. Seleksi fitur menolak kolom target, kolom group, dan nama yang mengindikasikan leakage (misalnya carbon, label, ECFP/OCFP, `y_`).

### 6.2 Kandidat dan hasil evaluasi

Targetnya `Emb_Carbon_Mean` (kg CO₂e). Kandidat yang disimpan dalam metadata: DummyRegressor mean; Random Forest 100 tree, depth unlimited; Random Forest 100 tree dengan `max_depth=10`; Random Forest 100 tree dengan `min_samples_leaf=2`. Model dipilih dari validation memakai MAE terendah, lalu RMSE. Seed 42; `n_jobs=-1`.

| Model | Validation MAE | Validation RMSE | Validation R² |
|---|---:|---:|---:|
| DummyRegressor mean | 6,0492 kg | 13,7210 kg | -0,0069 |
| Random Forest depth unlimited, leaf 1 | 0,1834 kg | 2,0635 kg | 0,9772 |
| Random Forest depth 10, leaf 1 (terpilih) | 0,1796 kg | 1,9538 kg | 0,9796 |
| Random Forest depth unlimited, leaf 2 | 0,3536 kg | 2,9870 kg | 0,9523 |

| Held-out test metric | Nilai | Makna |
|---|---:|---|
| MAE | 0,2779 kg CO₂e | Besar error absolut rata-rata |
| RMSE | 2,4290 kg CO₂e | Lebih peka terhadap error besar |
| R² | 0,9467 | Variasi yang dijelaskan pada split itu, bukan akurasi persen |
| Residual mean | -0,2247 kg | Arah bias menurut definisi residual di artifact |
| Maximum absolute error | 27,5321 kg | Menunjukkan potensi kesalahan besar |

Artifact runtime adalah `ml-engine/artifacts/embodied_carbon_model.joblib`; metadata/evaluasi ada pada `ml-engine/artifacts/embodied_carbon_model.json`. Artifact dilabeli experimental dan “SCARIF-informed only”; ini bukan reproduksi SCARIF yang tervalidasi. Artifact dibuat dengan scikit-learn 1.9.1; environment test yang tersedia menggunakan 1.8.0 dan menampilkan `InconsistentVersionWarning`. Samakan versi atau retrain sebelum klaim reproducibility produksi.

### 6.3 Interpretasi model

MAE 0,2779 berarti error absolut rata-rata pada split test dalam kg CO₂e; bukan “akurasi 99%”. RMSE yang jauh di atas MAE dan error maksimum 27,53 kg memperlihatkan pengaruh error besar. R² tinggi tidak menjamin estimasi akurat untuk setiap produk atau untuk hardware di luar data. Label dasar pun merupakan output simulasi ECO-CHIP, jadi model ML meniru pola label tersebut, bukan mengukur emisi pabrik.

### 6.4 Alur training dan inferensi yang dapat direproduksi

1. `ml-engine/data_processing/prepare_dataset.py` memeriksa kontrak target/sumber, membersihkan data, dan menulis report serta split.
2. `clean_data.py` menangani duplikasi, missing/invalid target, dan missing fitur yang dibutuhkan. Report menyimpan jumlah baris awal/akhir dan alasan penghapusan.
3. `feature_engineering.py` mempertahankan fitur numerik terpilih tanpa scaling maupun imputasi. Prediksi menolak field hilang, nilai nonnumerik, atau nilai NaN.
4. `models/train.py` memvalidasi disjoint group split, melatih mean baseline dan tiga variasi Random Forest, lalu memilih MAE validation terendah dengan RMSE sebagai tie-break.
5. Evaluasi akhir dilaporkan pada test holdout, bukan dipakai untuk memilih hyperparameter. Artifact joblib dan metadata JSON disimpan terpisah.
6. Backend mengirim lima fitur untuk satu prediksi embodied atau seluruh katalog untuk perbandingan batch. Artifact wajib memiliki model, `feature_columns`, serta unit target.

Training tidak dijalankan setiap kali aplikasi dimulai. Perubahan data tidak mengubah model sampai pipeline training dijalankan kembali dan artifact diperbarui. Reproduksi penuh membutuhkan snapshot dataset, preprocessing report, seed, split, artifact, dan versi scikit-learn yang sesuai.

## 7. Metode karbon dan metrik

### 7.1 Embodied carbon

Untuk estimasi baseline, API meminta prediksi model dan mengembalikan metadata `valueKind`, unit, functional unit, dan boundary. Ini adalah prediksi atas label CarbonSet modeled. Pada mode existing, profil fitur berasal dari CarbonSet; pada custom, pengguna memasukkan lima fitur. Tidak ada interval prediksi individual yang tervalidasi pada endpoint baseline.

Perbandingan penggantian menggunakan `Emb_Carbon_Mean` CarbonSet untuk emisi embodied kandidat, terpisah dari prediksi Random Forest pada kartu hasil.

### 7.2 Operational energy

Form mengubah utilisasi persen menjadi pecahan 0–1. Persamaan kalkulator:

```text
electricity_kwh = TDP_W / 1000
                  × hours_per_day
                  × days_per_year
                  × usage_years
                  × utilization
```

TDP adalah thermal design power, bukan pengukuran konsumsi listrik. Nilai energi merupakan skenario sederhana berdasarkan proxy tersebut. Endpoint energi dapat menghasilkan kWh tanpa grid factor.

### 7.3 Operational carbon

```text
operational_carbon_kg_co2e =
    electricity_kwh × grid_intensity_kg_co2e_per_kwh
```

Grid factor dicari berdasarkan region/tahun persis. Data yang tidak ada menghasilkan error, tidak memakai nilai default. Faktor yang digunakan lifecycle location-based; tidak tersedia faktor kontraktual market-based.

Contoh hitung transparan memakai nilai ilustrasi: TDP 180 W, 8 jam/hari, 365 hari/tahun, utilisasi 70%, pemakaian 5 tahun, dan CI 0,68515 kg CO₂e/kWh.

```text
annual electricity = 180 / 1000 × 8 × 365 × 0.70
                   = 367.92 kWh/year
five-year electricity = 367.92 × 5 = 1,839.60 kWh
annual operational carbon = 367.92 × 0.68515
                          = 252.08 kg CO₂e/year
five-year operational carbon = 1,839.60 × 0.68515
                              = 1,260.40 kg CO₂e
```

Hasil sebenarnya mengikuti pasangan region/tahun yang dipilih. Angka contoh bukan hasil uji perangkat dan tidak menunjukkan bahwa TDP sama dengan daya rata-rata aktual.

### 7.4 Compute Carbon Intensity (CCI)

```text
CCI = total_carbon_kg_co2e / completed_compute_work
```

Endpoint mewajibkan karbon non-negatif, workload lebih besar dari nol, `workloadUnit`, `lifecycleBoundary`, dan `analysisPeriod`. UI menghitung numerator sebagai predicted embodied + operational carbon dan meminta workload secara manual. Default/angka input pengguna bukan measurement benchmark. CCI hanya dapat dibandingkan jika unit workload, boundary, periode, dan cakupan sistem sama.

Contoh: 100 kg CO₂e / 10.000.000 gambar = 0,00001 kg CO₂e/gambar = 0,01 g CO₂e/gambar = 10 kg CO₂e per satu juta gambar. Numerator dan jumlah gambar harus mencakup sistem/periode yang sama.

Pada halaman estimate, **standard CCI** menggunakan predicted embodied satu kali ditambah operational carbon selama periode yang dipilih. **STEC-based CCI** menggunakan STEC satu chip ditambah operational carbon pada periode yang sama, kemudian dibagi completed workload yang sama. Bila STEC berstatus range, total dan CCI STEC juga ditampilkan sebagai rentang. Karena boundary embodied model dan STEC berbeda, kedua CCI bukan perbandingan apples-to-apples. Aplikasi tidak memverifikasi bahwa jumlah workload selesai dilakukan pada hardware dan periode yang sama.

### 7.5 E-waste dan custom PC

Modul e-waste mengalokasikan massa hardware ke reuse, recycling, dan disposal; fraksi 0–1 harus berjumlah satu dengan toleransi numerik. Modul memeriksa konservasi massa, namun tidak mengubah massa menjadi karbon karena faktor emisi recycling/disposal yang disetujui belum tersedia. Custom PC menerima BOM dan faktor carbon dengan source/boundary; proxy hanya eksplisit dan harus dalam tipe yang sama. Bila faktor wajib unresolved, total final adalah `null`, bukan subtotal yang ditampilkan sebagai total penuh. Kedua modul Python belum menjadi alur utama API/UI.

## 8. STEC: metode dan evidence

### 8.1 Definisi dan persamaan

Implementasi STEC mengatribusikan emisi location-based ke manufaktur satu die, cradle-to-gate:

```text
intensity_g_per_cm2 = GPS + MPS + CI × EPS
STEC_kg = intensity_g_per_cm2 × die_area_mm2 / 100 / 1000
```

`GPS` dan `MPS` berunit gCO₂e/cm²; `CI` berunit gCO₂e/kWh; `EPS` berunit kWh/cm². Luas die dikonversi dari mm² ke cm², kemudian gram ke kilogram. Batch memperhitungkan struktur die/chiplet sesuai evidence produk.

### 8.2 Parameter process node

| Node | EPS (kWh/cm²) | GPS (g/cm²) | MPS (g/cm²) | Catatan |
|---|---:|---:|---:|---|
| 28 nm | 0,9 | 100 | 500 | Parameter metodologi |
| 20 nm | 1,2 | 110 | 500 | Proxy eksplisit juga untuk 22 nm |
| 14 nm | 1,2 | 125 | 500 | Parameter metodologi |
| 10 nm | 1,475 | 150 | 500 | Parameter metodologi |
| 7 nm | 1,52 | 200 | 500 | Parameter metodologi |
| 7 nm EUV/EUV-DP | 2,15 | 200 | 500 | Bucket EUV |
| 5 nm | 2,75 | 225 | 500 | Parameter metodologi |
| 3 nm | 2,75 | 275 | 500 | Parameter metodologi |
| 12 nm | — | — | — | Belum ada; chiplet terkait dapat incomplete |

Parameter dirujuk ke Zhang et al. Table 7 dan workbook metodologi penelitian (`docs/research/Analisis_STEC_CPU_GPU.xlsx`). Node tanpa parameter menghasilkan status incomplete/error sesuai alur. Penggunaan proxy 22 nm → 20 nm dinyatakan eksplisit, bukan tebakan tersembunyi.

### 8.3 Asumsi dan batas

- Boundary: cradle-to-gate die manufacturing; tidak termasuk packaging, board, memory, cooling, penggunaan, dan end-of-life.
- Batch tidak menerapkan yield correction. Fungsi kalkulator menerima yield factor, tetapi hasil batch yang didokumentasikan tidak menggunakannya.
- Lokasi fab ambigu menghasilkan rentang skenario min–max, bukan confidence interval statistik.
- Tahun rilis dapat menjadi proxy manufacturing year bila tahun produksi tidak tersedia dan harus tetap dilabeli proxy.
- Bukti lokasi tidak lengkap dapat menghasilkan confidence unresolved atau output incomplete.
- Atribusi market-based belum tersedia tanpa faktor kontraktual PPA/REC bersumber.

### 8.4 Cara lokasi, tahun, dan chiplet memengaruhi output

Urutan resolver lokasi batch adalah: evidence produk spesifik; rule vendor+tipe+node; lalu rule vendor+tipe dengan node wildcard. Evidence produk diperiksa agar vendor dan tipe cocok; bila node pada evidence berbeda dari CarbonSet, sumber node dicatat dalam warning dan dipakai sesuai aturan batch. Rule dapat memuat beberapa kandidat region; setiap kandidat dihitung dengan CI tahun yang sama, lalu minimum/maksimum menjadi `range`.

Tahun manufaktur dari `manufacturing-years.csv` akan dipakai bila ada override bersumber. Jika tidak ada, tahun pada `Release Date` menjadi `release_year_proxy`; ini menandai tahun rilis sebagai proxy, bukan bukti tahun produksi chip. Jika tahun, fab region, CI, luas die, atau parameter node yang wajib tidak tersedia, hasil produk berstatus `incomplete`.

Untuk produk yang punya layout chiplet, batch dapat menggunakan jumlah/luas komponen yang didukung evidence chiplet alih-alih memperlakukan satu angka luas sebagai semua die. `chiplet_applied` dan `chiplet_die_area_mm2` menjelaskan kapan adjustment ini dipakai. Detail tersebut tetap bergantung pada cakupan evidence yang hanya tersedia untuk sebagian produk.

Nilai `global_baseline_stec_kg_co2e` adalah skenario baseline lokasi World yang dihitung terpisah; bukan nilai pengganti kandidat fab dan bukan bagian yang ditambahkan ke STEC produk. Kolom `carbonset_emb_*` hanya referensi untuk side-by-side, sedangkan `market_based_status` menyatakan bahwa faktor market-based belum tersedia.

### 8.5 Skenario STEC pada halaman estimate

Untuk prosesor CarbonSet, estimate mengambil record STEC yang sama dengan inventori batch: `point` menghasilkan satu nilai, `range` menghasilkan minimum–maksimum berdasarkan kandidat lokasi, dan `incomplete` tidak menghasilkan total STEC. UI menambahkan operational carbon ke satu nilai atau kedua batas rentang tersebut. Metadata fab, tahun, release-year proxy, dan warning ditampilkan di kartu skenario.

Untuk prosesor custom, UI memanggil `POST /api/estimates/stec` dengan `dieSizeMm2`, node STEC, manufacturing region, dan manufacturing year terpisah dari wilayah/tahun penggunaan. Input die size diperlakukan sebagai luas untuk satu chip; UI tidak merekonstruksi layout chiplet atau node campuran. Pengguna harus memilih node eksplisit dari parameter yang didukung. Jika lookup region-tahun atau node gagal, kartu standard tetap bisa tersedia dan kartu STEC menampilkan error/ketersediaan secara terpisah.

Skenario STEC-based dihitung sebagai:

```text
stec_scenario_carbon =
    STEC_die_manufacturing + operational_carbon_for_selected_period

stec_scenario_CCI =
    stec_scenario_carbon / completed_compute_work
```

Ini adalah **alternatif dengan boundary partial**, bukan `standard estimate + STEC`. Menambahkan STEC ke angka embodied model akan berisiko double-counting manufaktur die.

## 9. Perbandingan karbon penggantian

Untuk prosesor existing, aplikasi dapat membandingkan kelanjutan penggunaan dengan kandidat CarbonSet bertipe sama. Kandidat dipilih berdasarkan tahun rilis dan rentang TDP sebagai penyaring awal; aturan ini tidak membuktikan bahwa workload atau kemampuan kandidat setara.

```text
annual_savings = current_annual_operational_carbon
                 - candidate_annual_operational_carbon
carbon_payback_years = candidate_embodied_carbon / annual_savings
```

Waktu carbon payback menunjukkan berapa lama penghematan emisi operasional skenario penggantian perlu berlangsung untuk mengimbangi embodied carbon kandidat. Emisi pembuatan prosesor lama dianggap sunk, emisi akhir masa pakai tidak dihitung, dan TDP menjadi proxy daya. Hasilnya merupakan estimasi skenario, bukan tanggal penggantian yang tervalidasi atau jaminan kecocokan hardware.

### 9.1 Algoritma pemilihan kandidat secara berurutan

1. Tipe input harus `CPU` atau `GPU`; hanya produk CarbonSet dengan tipe yang sama dipertimbangkan.
2. Prosesor yang sedang dipilih dikeluarkan. Kandidat harus memiliki tanggal rilis setelah tanggal rilis prosesor saat ini.
3. Sistem mencari tahun rilis paling baru dari seluruh katalog, lalu membatasi ke lima tahun kalender terbaru katalog. Kandidat tetap harus lebih baru daripada prosesor aktif.
4. TDP kandidat harus finite dan berada pada rentang **50% sampai kurang dari 100%** dari TDP prosesor aktif. Kandidat dengan TDP sama/lebih tinggi, atau di bawah separuh TDP, tersisih.
5. Kandidat perlu memiliki `Emb_Carbon_Mean` non-negatif dan skenario harus menghasilkan penghematan operational carbon tahunan positif.
6. Kandidat diurutkan dengan `yearsToCarbonPayback` terkecil, kemudian nama produk alfabetis untuk tie-break. Maksimal tiga kandidat dikembalikan.

Lima tahun di atas ditentukan dari tahun terbaru pada **seluruh katalog**, bukan dihitung dari tanggal prosesor yang dipilih dan bukan lima produk teratas. Jika dataset/analisis-year berubah, himpunan kandidat juga dapat berubah.

### 9.2 Persamaan kandidat

```text
annual_carbon_per_watt =
    hours_per_day × days_per_year × utilization / 1000
    × grid_intensity_kg_co2e_per_kwh

current_annual_operational_carbon =
    current_tdp_w × annual_carbon_per_watt

candidate_annual_operational_carbon =
    candidate_tdp_w × annual_carbon_per_watt

annual_savings =
    current_annual_operational_carbon
    - candidate_annual_operational_carbon

years_to_carbon_payback =
    candidate_embodied_carbon_kg_co2e / annual_savings
```

Karena pola pemakaian dan grid factor sama untuk kedua prosesor, penghematan berasal dari selisih TDP pada rumus, bukan pengukuran daya aktual. Kandidat embodied memakai `CarbonSet Emb_Carbon_Mean`, bukan hasil prediksi baseline dari Random Forest.

### 9.3 Contoh angka ilustrasi

Misalkan prosesor sekarang bertipe GPU dengan TDP 180 W, kandidat sejenis 120 W, pola 8 jam/hari selama 365 hari/tahun pada utilisasi 70%, faktor grid 0,68515 kg CO₂e/kWh, dan embodied carbon kandidat 40 kg CO₂e. Angka ini hanya demonstrasi rumus, bukan klaim tentang produk tertentu.

```text
annual savings = (180 - 120) / 1000 × 8 × 365 × 0.70 × 0.68515
               ≈ 84.03 kg CO₂e/year
payback = 40 / 84.03
        ≈ 0.476 years ≈ 5.7 months
```

Interpretasi: jika pengguna sudah mengganti ke kandidat tersebut, dan workload/operasi tetap setara dengan asumsi, kira-kira 5,7 bulan penghematan operasional diperlukan agar embodied carbon kandidat tertutup oleh emisi operasional yang dihindari. Ini **bukan** “ganti prosesor dalam 5,7 bulan dari sekarang”; aplikasi tidak mengetahui umur, kondisi, atau sisa masa pakai perangkat.

### 9.4 Status hasil dan kasus tanpa rekomendasi

| Status API | Makna |
|---|---|
| `estimated` | Kandidat memenuhi filter dan punya penghematan positif; respons memuat maksimum tiga kandidat. |
| `current_release_date_unavailable` | Tanggal rilis prosesor saat ini kosong/tidak valid sehingga urutan “lebih baru” tidak dapat dibentuk. |
| `no_same_type_candidate` | Tidak ada prosesor katalog bertipe sama selain item saat ini. |
| `no_newer_candidate` | Tidak ada produk bertipe sama yang lebih baru. |
| `no_recent_candidate` | Ada kandidat lebih baru, tetapi tidak dalam jendela lima tahun rilis katalog terbaru. |
| `no_similar_tdp_candidate` | Tidak ada kandidat yang lolos jendela TDP 50%–kurang dari 100%. |
| `no_operational_carbon_savings` | Kandidat TDP ditemukan, tetapi pola penggunaan/CI tidak menghasilkan savings positif atau embodied candidate tidak valid. |

Untuk setiap objek kandidat, API mengembalikan nama/tipe/tanggal rilis, TDP, embodied mean/min/max, operational carbon tahunan kandidat, penghematan tahunan, dan `yearsToCarbonPayback`. Kartu UI menyoroti penghematan tahunan dan payback; min/max embodied tersedia sebagai data katalog tetapi tidak menjadi interval ketidakpastian payback.

Kartu rekomendasi tampil setelah estimate selesai. Pada input custom, tanggal rilis katalog umumnya tidak tersedia sehingga hasil wajar berupa `current_release_date_unavailable`. Jika request rekomendasi gagal, angka estimate utama tetap dapat ditampilkan dengan error rekomendasi terpisah.

### 9.5 Keterbatasan kategorisasi hardware

Katalog dan filter runtime hanya memiliki `Type` berupa CPU/GPU. Tidak ada field kelas perangkat yang teruji untuk desktop, laptop, workstation, atau server; tidak ada socket, motherboard, form factor, cooling, atau kompatibilitas sistem. Karena itu, filter “same type” hanya mencegah CPU dibandingkan dengan GPU—**belum mencegah GPU laptop dibandingkan dengan GPU desktop**, misalnya. TDP range adalah heuristik karbon, bukan bukti performa atau kecocokan.

### 9.6 Endpoint carbon budget yang terpisah

`POST /api/estimates/upgrade-timeline` memakai budget emisi yang ditentukan pengguna. Sistem menghitung:

```text
current_cumulative_carbon =
    embodied_carbon + annual_operational_carbon × years_already_used

years_to_budget =
    max(0, (carbon_budget - current_cumulative_carbon)
           / annual_operational_carbon)
```

Jika budget sudah terlampaui, status `budget_already_reached` dan waktunya nol. Jika emisi operasional tahunan nol sedangkan budget belum tercapai, status `no_annual_operational_carbon` dan `yearsToBudget` null. Endpoint ini memproyeksikan waktu sampai ambang karbon terpilih tercapai; ia tidak memilih kandidat hardware dan saat ini tidak dipanggil UI estimate.

## 10. Evaluasi, tes, dan reproducibility

### 10.1 Hasil validasi saat dokumen diperbarui

| Validasi | Hasil |
|---|---|
| Backend `npm test` dari `backend/` | 10 tes lulus |
| Frontend `npm run build` dari `frontend/` | Build produksi berhasil |
| Python `unittest discover -s ml-engine/tests -v` | 22 tes lulus; 1 test class model diskip karena environment test variables belum diset |
| scikit-learn artifact | Warning versi: artifact 1.9.1 dibaca dengan runtime 1.8.0 |

Tes backend mencakup validasi API dan perhitungan karbon. Tes Python mencakup preprocessing/group split, embodied artifact contract (diskip bila env khusus tidak tersedia), energy/carbon equation, CCI, custom PC, konservasi massa e-waste, kalkulator STEC, dan batch point/range/incomplete. Tes bukan verifikasi power meter.

### 10.2 Menyiapkan dan menjalankan aplikasi lokal

Prasyarat: Node.js/npm, Python, dan dependency Python di `ml-engine/requirements.txt`. Backend memakai `PYTHON_COMMAND` (default `python`). Untuk menghindari masalah path relatif, jalankan backend dari folder `backend/`. Untuk environment Python lokal di Windows:

```powershell
cd ml-engine
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..\backend
$env:PYTHON_COMMAND = (Resolve-Path "..\ml-engine\.venv\Scripts\python.exe").Path
```

Variabel `PYTHON_COMMAND` di terminal backend harus menunjuk executable Python yang memiliki dependency engine. Jika environment Python sudah dikonfigurasi global, langkah venv dapat dilewati.

Terminal pertama:

```powershell
cd backend
npm install
npm start
```

Terminal kedua:

```powershell
cd frontend
npm install
npm run dev
```

Frontend default menghubungi `http://localhost:3000`; untuk origin lain set `VITE_API_URL`. Backend default memakai port 3000 dan mendukung `PORT`, `CARBONSET_PATH`, `GRID_INTENSITY_PATH`, serta `PYTHON_COMMAND`. Path data default dihitung relatif dari current working directory backend. Endpoint health adalah `GET /health`; root `/` mengembalikan JSON daftar endpoint.

Perintah training bukan bagian dari startup runtime. Jangan menjalankan ulang training atau menimpa artifact semata-mata untuk membuka aplikasi, kecuali memang sedang membuat versi model baru dengan split/evaluasi terdokumentasi.

### 10.3 Batas arti hasil tes

Backend tests memvalidasi kontrak endpoint dan rumus pada fixture yang dipakai test; Python tests memvalidasi preprocessing/model/accounting/STEC sesuai fixture. Build frontend memeriksa kompilasi produksi. Tes ini tidak membuktikan bahwa nilai CarbonSet adalah nilai pengukuran, bahwa grid factor mewakili lokasi marginal, bahwa fab evidence benar untuk setiap unit, atau bahwa kandidat penggantian mampu menjalankan workload pengguna. Itu memerlukan validasi sumber dan studi eksternal.

Perintah:

```text
cd backend
npm test

cd frontend
npm run build

cd ml-engine
python -m unittest discover -s tests -v
```

Backend perlu Node.js dan Python engine sesuai konfigurasi; frontend memakai Vite. Model/hasil yang bisa direproduksi juga memerlukan snapshot data, artifact, seed, split, dan versi dependencies yang sama.

## 11. Batasan dan interpretasi yang aman

| Topik | Batasan | Dampak |
|---|---|---|
| Embodied model | Label CarbonSet modeled; artifact eksperimental; mismatch versi sklearn | Bukan hasil ukur atau prediksi universal; samakan versi dan validasi luar |
| Operational power | TDP proxy dan input skenario | Bukan pembacaan konsumsi aktual |
| CCI | Workload diinput pengguna, bukan diukur | Angka input tidak otomatis membuktikan pekerjaan yang benar-benar selesai |
| STEC | Evidence fab/node/year tidak lengkap untuk sebagian produk | Hasil dapat berupa range, memakai proxy, atau incomplete |
| Dua skenario hasil | Embodied model dan STEC memakai cakupan embodied yang berbeda | Tampilkan sebagai hasil alternatif; jangan menjumlahkan keduanya atau menyamakan CCI-nya |
| Perbandingan penggantian | TDP dan tahun rilis hanya penyaring; workload-equivalence, performa, compatibility, dan form factor tidak diuji | Carbon payback adalah skenario setelah penggantian, bukan tanggal ganti tervalidasi |
| Custom PC/e-waste | Modul Python belum terhubung ke UI/API utama | Jangan menyatakan sebagai fitur UI end-to-end |
| Persistensi | Tidak ada DB runtime yang terverifikasi | Jangan mengklaim hasil tersimpan permanen oleh aplikasi |

Klaim aman untuk presentasi: **“CarbonHardware mengestimasi embodied carbon prosesor memakai model eksperimental yang dilatih pada label CarbonSet; menghitung emisi listrik penggunaan dari skenario TDP dan faktor grid lifecycle; menampilkan STEC location-based dengan status evidence; menghitung CCI untuk workload yang didefinisikan pengguna; dan membandingkan skenario penggantian berdasarkan estimasi carbon payback.”**

## 12. Rekomendasi pengembangan

Prioritas berikut menjaga batasan dan mengembangkan evidence secara bertahap:

1. **Validasi carbon payback.** Uji asumsi penyaringan kandidat, skenario pemakaian, dan dampak variasi grid intensity; jangan menyajikan hasil sebagai tanggal penggantian pasti.
2. **Perjelas kesetaraan workload.** Jika perbandingan penggantian akan dipakai untuk keputusan nyata, tentukan cara membuktikan kandidat mampu menjalankan workload yang sama.
3. **Perjelas uncertainty.** Sajikan ketidakpastian input embodied dan faktor daya/grid, bukan hanya satu nilai estimasi.
4. **Samakan boundary.** Pastikan embodied, operational carbon, STEC, dan CCI dibandingkan hanya bila functional unit serta boundary-nya sepadan.
5. **Sediakan provenance reproduktif.** Simpan sumber, versi dataset, aturan transformasi, dan laporan pembersihan untuk input yang digunakan.
6. **Konsolidasikan dokumentasi dan dependencies.** Samakan README, metadata model, sklearn runtime/artifact version, dan instruksi tes.
7. **Integrasi custom PC/e-waste.** Hanya bila masuk scope produk; sediakan API/UI, katalog faktor berbukti, dan perilaku eksplisit untuk komponen unresolved.

## 13. Glosarium

| Istilah | Arti |
|---|---|
| Embodied carbon | Emisi siklus hidup produk sesuai boundary sumber; baseline CarbonSet adalah output modeled |
| CFP | Carbon footprint of product; jejak karbon produk sesuai boundary dan metode sumber |
| Operational energy | Listrik saat hardware digunakan, dalam kWh |
| Operational carbon | Energi listrik dikali intensitas emisi grid lokasi/waktu |
| STEC | Spatial-Temporal Embodied Carbon; di sini location-based die manufacturing |
| CCI | Compute Carbon Intensity: karbon per unit kerja komputasi selesai |
| TDP | Thermal Design Power; proxy daya dalam skenario, bukan konsumsi terukur |
| Carbon payback | Durasi operasi kandidat yang diperkirakan perlu agar penghematan operational carbon menutup embodied carbon kandidat |
| Release-year proxy | Tahun rilis yang dipakai sebagai pendekatan tahun manufaktur ketika override bersumber tidak tersedia |
| Point/range/incomplete | Nilai tunggal / rentang skenario lokasi / terblokir karena bukti atau parameter kurang |
| Boundary | Komponen dan tahap siklus hidup yang masuk ke suatu angka |
| Location-based | Atribusi menggunakan intensitas listrik wilayah fisik dan tahun |
| Market-based | Atribusi faktor kontraktual seperti PPA/REC; belum tersedia |
| MAE/RMSE/R² | Metrik regresi: error absolut / error kuadrat / variasi yang dijelaskan; bukan accuracy klasifikasi |

## 14. Peta file utama

| Area | Path | Peran |
|---|---|---|
| Frontend | `frontend/src/App.jsx`, `frontend/src/pages/` | Navigasi dan halaman UI |
| Form dan hasil | `frontend/src/components/HardwareForm.jsx`, `frontend/src/pages/EstimateCarbon.jsx` | Input existing/custom, kalkulasi, hasil |
| Perbandingan penggantian karbon | `frontend/src/components/CarbonReplacementComparison.jsx`, `backend/src/services/carbon-replacement.service.js` | Membandingkan penggunaan berlanjut dengan kandidat CarbonSet bertipe sama memakai waktu impas karbon |
| Backend routes | `backend/src/app.js`, `backend/src/routes/` | Pendaftaran endpoint |
| Perhitungan karbon | `backend/src/controllers/estimate.controller.js`, `backend/src/services/carbon.service.js`, `backend/src/services/metrics.service.js` | Estimasi operational dan CCI |
| Dataset utama | `data/raw/carbonset/`, `data/raw/environmental/`, `data/raw/stec/evidence/` | Input CarbonSet, grid, evidence |
| Dataset STEC | `data/processed/stec-per-chip.csv` | Inventori point/range/incomplete |
| Model | `ml-engine/models/`, `ml-engine/carbon/`, `ml-engine/artifacts/` | Training, inferensi, accounting, artifact |
| Tes backend | `backend/test/api.test.js`, `backend/test/carbon-replacement.test.js` | API dan perbandingan karbon |
| Tes Python | `ml-engine/tests/` | Preprocessing, model contract, accounting, STEC |
| Dokumentasi terkait | `backend/README.md`, `docs/carbon-methodology.md`, `docs/dataset-documentation.md` | Petunjuk implementasi dan metode |
| Sumber PDF ini | `docs/CarbonHardware_Project_Documentation_ID.md` | Naskah yang dapat diedit untuk PDF |
| Generator PDF | `scripts/generate_project_documentation_pdf.py` | Menghasilkan PDF dari naskah Markdown |

## Kesimpulan

CarbonHardware memiliki alur end-to-end untuk estimasi embodied baseline, operational carbon, STEC, CCI, serta perbandingan karbon penggantian. Perbandingan penggantian menggunakan CarbonSet dan skenario operasional berbasis TDP; hasilnya adalah carbon payback bersyarat, bukan rekomendasi universal atau tanggal penggantian tervalidasi.
