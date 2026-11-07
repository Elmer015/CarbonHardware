# Dokumentasi Proyek CarbonHardware

## Status dokumen

Dokumentasi teknis dan metodologi ini diselaraskan dengan source code, dataset, model, dan tes yang tersedia pada **7 November 2026**. Dokumen ini menjelaskan perilaku implementasi saat ini, bukan rancangan masa depan. Nilai karbon adalah estimasi/model output sesuai batas masing-masing sumber, bukan pengukuran universal atau LCA lengkap.

> **Ringkasan rekomendasi hardware:** setelah kalkulasi karbon berhasil untuk prosesor CarbonSet, aplikasi dapat menampilkan sistem MLPerf ResNet-50 yang dalam cohort yang sama memiliki embodied carbon perangkat inference setara/lebih rendah dan throughput sistem lebih tinggi. Perhitungan rekomendasi ini memakai nilai embodied CarbonSet, bukan prediksi embodied di kartu hasil dan bukan total karbon operasional.

## Daftar isi

1. Ringkasan eksekutif
2. Tujuan, ruang lingkup, dan batas klaim
3. Arsitektur aplikasi
4. Alur pengguna dan API
5. Dataset dan provenance
6. Pemrosesan data dan model embodied
7. Metode karbon dan metrik
8. STEC: metode dan evidence
9. MLPerf ResNet-50 dan rekomendasi hardware
10. Evaluasi, tes, dan reproducibility
11. Batasan dan interpretasi yang aman
12. Rekomendasi pengembangan
13. Glosarium
14. Peta file utama

## 1. Ringkasan eksekutif

CarbonHardware adalah aplikasi riset yang menggabungkan estimasi embodied carbon prosesor, estimasi listrik dan emisi fase penggunaan, lookup intensitas karbon grid, perhitungan STEC die manufacturing, serta Compute Carbon Intensity (CCI). Aplikasi terdiri dari frontend React/Vite, backend REST Node.js/Express, dan engine Python untuk prediksi embodied serta perhitungan STEC. CSV dan artifact model adalah sumber runtime; backend tidak menggunakan database untuk penyimpanan runtime.

Frontend memiliki tiga halaman navigasi: estimasi embodied/operational carbon, STEC per prosesor, dan perbandingan baseline embodied dengan STEC. Fitur rekomendasi benchmark tidak menjadi menu atau halaman tersendiri. Rekomendasi ResNet-50 tampil di bawah hasil kalkulasi karbon yang berhasil, hanya pada mode prosesor existing yang dipilih dari CarbonSet.

| Area | Kondisi implementasi | Interpretasi |
|---|---|---|
| Embodied baseline | Random Forest terintegrasi melalui artifact joblib; eksperimental | Prediksi atas label modeled CarbonSet, bukan LCA terukur untuk unit tertentu |
| Operational energy/carbon | Endpoint dan form tersedia; daya diproksikan dengan TDP | Skenario, bukan pengukuran daya aktual |
| STEC | Dataset batch per chip dan kalkulator tersedia | Location-based cradle-to-gate die manufacturing; hasil berstatus point, range, atau incomplete |
| CCI | Endpoint dan input workload tersedia | Valid hanya bila definisi kerja, periode, dan boundary konsisten |
| ResNet-50 | 38 baris benchmark termapping ke enam produk CarbonSet | Perbandingan terbatas pada cohort tertentu; tidak semua baris bisa dibandingkan |
| Rekomendasi | API dan UI terintegrasi pada hasil kalkulasi | Trade-off berdasarkan embodied CarbonSet dan throughput MLPerf; bukan skor karbon total atau rekomendasi universal |
| Database | Tidak digunakan pada alur runtime yang diperiksa | CSV lokal adalah sumber runtime |

## 2. Tujuan, ruang lingkup, dan batas klaim

### 2.1 Tujuan

Produk membantu membandingkan besaran jejak karbon hardware komputasi dengan menampilkan sumber, unit, boundary, status evidence, serta asumsi. Embodied carbon, operational carbon, STEC, CCI, throughput, dan massa e-waste adalah besaran berbeda; angka-angka itu tidak boleh dijumlahkan atau dibandingkan tanpa memeriksa functional unit dan boundary.

### 2.2 Yang dihitung

- **Embodied baseline:** prediksi model atas `Emb_Carbon_Mean` CarbonSet dari lima fitur prosesor.
- **Operational energy/carbon:** listrik dan emisi penggunaan dari TDP sebagai proxy daya, skenario pemakaian, dan intensitas grid location-based lifecycle.
- **STEC:** estimasi location-based untuk manufaktur die berdasarkan node, luas die, parameter manufaktur, dan intensitas listrik lokasi-tahun.
- **CCI:** total karbon yang dikirim ke endpoint dibagi jumlah pekerjaan komputasi selesai yang didefinisikan pengguna.
- **Rekomendasi benchmark:** perbandingan embodied carbon perangkat inference dan throughput sistem pada benchmark ResNet-50 yang termapping ke CarbonSet.
- **E-waste dan custom PC:** modul Python tersedia untuk alokasi massa dan kalkulasi BOM, tetapi belum menjadi alur API/frontend utama.

### 2.3 Yang tidak boleh diklaim

Aplikasi bukan LCA lengkap untuk server; bukan pengukur konsumsi daya aktual; tidak menghitung otomatis workload selesai dari FLOPS/runtime; tidak menghitung emisi market-based kontrak listrik; dan tidak menjamin prediksi berlaku untuk semua vendor, generasi, node, atau produk di luar distribusi data. Tes yang lulus membuktikan kontrak teknis tertentu, bukan kebenaran seluruh input sumber atau validitas ilmiah universal.

## 3. Arsitektur aplikasi

### 3.1 Komponen

| Komponen | Tanggung jawab |
|---|---|
| Frontend React 18 + Vite | Form existing/custom, hasil kalkulasi, STEC, perbandingan, dan kartu rekomendasi |
| Backend Node.js + Express | REST API, validasi input, load CSV, pencocokan data, serta perhitungan ringan |
| Python engine | Prediksi embodied dengan artifact model dan kalkulator STEC |
| CarbonSet CSV | Profil hardware serta embodied Min/Mean/Max |
| Grid-intensity CSV | Data intensitas listrik per entitas/wilayah dan tahun |
| STEC CSV/evidence | Hasil batch dan evidence fab, node, manufacturing year, serta chiplet |
| Benchmark CSV terkurasi | 38 baris MLPerf ResNet-50 yang sudah dipetakan ke CarbonSet |

Alur umumnya adalah **UI → REST API → layanan domain → CSV dan/atau subprocess Python**. Backend memuat CarbonSet, intensitas grid, inventori STEC, dan benchmark saat startup. Prediksi embodied dan STEC custom dijalankan backend dengan Python sebagai subprocess; payload JSON dikirim lewat stdin dan hasil JSON dibaca dari stdout. Kegagalan load data atau proses kalkulasi harus terlihat sebagai error, bukan angka sukses pengganti.

### 3.2 Runtime dan konfigurasi

Backend berjalan pada port `3000` secara default. `PORT`, `CARBONSET_PATH`, `GRID_INTENSITY_PATH`, dan `PYTHON_COMMAND` dapat dioverride lewat environment. Jalankan backend dari direktori `backend/`, karena default path dataset relatif terhadap direktori kerja tersebut. Benchmark saat ini menunjuk ke `../data/processed/resnet50-carbonset-benchmark.csv`. Frontend memakai `VITE_API_URL` atau default `http://localhost:3000`.

Tidak ditemukan koneksi database aktif pada jalur runtime yang diperiksa. Adanya folder/schema database bukan bukti bahwa aplikasi menyimpan data ke database.

## 4. Alur pengguna dan API

### 4.1 Alur estimasi karbon

1. Pengguna memilih prosesor CarbonSet **existing** atau memasukkan lima fitur prosesor **custom**.
2. Pengguna memasukkan skenario operasional: jam/hari, tahun pemakaian, utilisasi, hari/tahun, wilayah grid, dan tahun analisis.
3. Pengguna memasukkan jumlah workload selesai dan unitnya untuk CCI.
4. Frontend meminta embodied prediction, operational carbon (yang menyertakan energy dan grid factor), lalu CCI.
5. Hasil baru ditampilkan setelah seluruh request berhasil. CCI UI menjumlahkan predicted embodied dan operational carbon untuk numerator.
6. Jika mode **existing**, komponen rekomendasi meminta kandidat ResNet-50 dengan nama prosesor pilihan. Mode custom tidak menampilkan rekomendasi.

Rekomendasi adalah analisis terpisah dari kartu karbon: ia tidak menggunakan total embodied + operational carbon yang baru dihitung, dan tidak mengubah angka CCI. Detail logikanya ada pada Bagian 9.

### 4.2 Halaman frontend

| Halaman | Fungsi |
|---|---|
| `/` dan `/estimate` | Estimasi embodied/operational carbon, CCI, serta rekomendasi ResNet-50 di bawah hasil untuk prosesor existing |
| `/stec` | Pencarian/detail STEC dan kalkulator custom |
| `/comparison` | Perbandingan baseline embodied prediction dan STEC; keduanya ditampilkan terpisah |

Navigasi menggunakan History API di frontend. Halaman benchmark terpisah tidak ada pada navigasi. Kartu rekomendasi berada pada halaman estimasi karbon.

### 4.3 Endpoint utama

| Endpoint | Fungsi | Batas penting |
|---|---|---|
| `GET /` | Metadata service dan daftar endpoint | Bukan halaman dokumentasi interaktif |
| `GET /health` | Health check | Status service |
| `GET /api/hardware/processors` | Daftar/pencarian prosesor CarbonSet | Sumber data lokal |
| `GET /api/hardware/processors/:name` | Detail prosesor | Tidak ditemukan menghasilkan 404 |
| `POST /api/estimates/embodied` | Prediksi embodied | Existing atau custom; Python + artifact model |
| `POST /api/estimates/operational-energy` | Energi listrik | Menghasilkan kWh dari TDP proxy dan skenario |
| `POST /api/estimates/operational-carbon` | Operational emissions | Energi dikali grid factor region/tahun persis |
| `POST /api/estimates/stec` | Estimasi STEC | Existing/custom; memerlukan grid factor dan node tersedia |
| `POST /api/estimates/cci` | Karbon per workload | `completedComputeWork` wajib lebih dari nol |
| `GET /api/grid-intensity?region=...&year=...` | Lookup intensitas grid | Region dan tahun dicari; tidak ada fallback |
| `GET /api/grid-intensity/regions` | Daftar region | Dari snapshot lokal |
| `GET /api/stec/processors` | Daftar/filter STEC | Filter search/type/status; page size maksimum 200 |
| `GET /api/stec/processors/options` | Opsi dropdown STEC | Label ringkas produk/type/vendor/status |
| `GET /api/stec/processors/:name` | Detail STEC | Tidak ditemukan menghasilkan 404 |
| `GET /api/comparison` | Batch baseline + STEC | Dua hasil tidak additive |
| `GET /api/benchmarks/resnet50` | Benchmark yang termapping | 38 baris, metadata keterbandingan |
| `GET /api/benchmarks/resnet50/recommendations?processorName=...` | Kandidat lebih rendah/setara karbon dan throughput lebih tinggi | Nama prosesor wajib; hasil bisa kosong bila tidak ada cohort/kandidat |

### 4.4 Validasi input yang tampak pada UI

Form custom meminta process size (nm), TDP (W), die size (mm²), jumlah die, dan average die area (mm²). Skenario operasional meminta jam/hari (maksimum 24), umur pemakaian, utilisasi 0–100%, hari/tahun (maksimum 366), region, dan tahun analisis (UI membatasi 1990–2025 sesuai snapshot yang tersedia). CCI meminta workload positif dan unit berupa teks. Nilai operasional adalah asumsi pengguna, bukan telemetry.

Endpoint lookup grid memerlukan kecocokan region/tahun persis pada snapshot; data yang hilang memberi 404. Endpoint API menolak input invalid dengan error 4xx dan error handler menyampaikan kegagalan.

## 5. Dataset dan provenance

### 5.1 CarbonSet

`data/raw/carbonset/CarbonSet.csv` memiliki 1.320 baris dan 19 kolom. Kolom meliputi nama produk, tipe, tanggal rilis, process size, TDP, die size, vendor, jumlah die, average die area, serta nilai embodied/operational/total carbon Min/Mean/Max. Komposisi raw: 741 CPU dan 579 GPU. Ada 17 duplikasi baris identik; setelah penghapusan tersisa 1.303 observasi untuk pipeline model. Nama produk unik: 1.272.

Target `Emb_Carbon_Mean` adalah rata-rata output modeled ECO-CHIP dari 10.000 simulasi, bukan pengukuran langsung atau EPD untuk semua chip. Unit target adalah kg CO₂e. Nilai pada snapshot berkisar sekitar 0,504–117,937 kg CO₂e; distribusinya skew, sehingga metrik error ekstrem juga perlu dilihat.

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

`data/raw/environmental/owid-lifecycle-carbon-intensity.csv` memuat 6.332 baris, 238 entitas, tahun 1990–2025. Metadata snapshot menyebut Ember (2026) melalui Our World in Data, lifecycle carbon intensity of electricity, update 2026-06-30, diunduh 2026-10-25. Sumber berunit gCO₂e/kWh; backend membagi angka dengan 1.000 menjadi kgCO₂e/kWh. Basisnya lifecycle location-based, bukan faktor market-based PPA/REC.

### 5.4 ResNet-50 dan cakupan CarbonSet

Runtime API memakai subset terkurasi `data/processed/resnet50-carbonset-benchmark.csv`: 38 baris MLPerf Inference ResNet-50 Offline pada versi suite v1.0–v4.1, terpetakan ke enam produk CarbonSet:

- AMD Ryzen Threadripper 1920X
- Intel Xeon Platinum 8592+
- NVIDIA A100 PCIe 40 GB
- NVIDIA A100 PCIe 80 GB
- NVIDIA A100 SXM4 80 GB
- NVIDIA A30 PCIe

Subset memiliki benchmark ID, versi suite, submitter, nama/tipe sistem, konfigurasi, precision/input type, device inference dan jumlahnya, nama produk CarbonSet, host processor bila tersedia, top-1 accuracy, throughput, serta URL sumber hasil MLPerf. Sumber URL benchmark dicatat per baris.

Di antara 38 baris, 20 berada di delapan cohort yang masing-masing punya lebih dari satu produk CarbonSet; 18 baris lain tidak memenuhi syarat perbandingan lintas produk pada cohort-nya. Ini tidak berarti benchmark tersebut salah atau performanya buruk: artinya cohort yang sama tidak memiliki produk berbeda untuk dibandingkan.

CarbonSet memiliki 1.275 kombinasi produk–tipe pada daftar coverage rekomendasi. Enam pasangan terpetakan pada subset ini; 1.269 belum terpetakan pada subset benchmark ResNet-50 yang dipakai. File daftar: `data/processed/carbonset-products-missing-resnet50-throughput.csv`. **Missing berarti tidak ada kecocokan pada subset ini**, bukan bukti bahwa data performa produk tidak tersedia di sumber lain.

Data sumber lengkap MLPerf/CCI yang pernah diperiksa merupakan bahan riset eksternal; file mentah lengkap tersebut tidak dibaca sebagai sumber runtime dan tidak seluruhnya disimpan di repository. CSV terkurasi beserta URL sumber tiap baris adalah input API saat ini. Dataset CCI/daya tidak digunakan oleh rekomendasi saat ini.

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

## 7. Metode karbon dan metrik

### 7.1 Embodied carbon

Untuk estimasi baseline, API meminta prediksi model dan mengembalikan metadata `valueKind`, unit, functional unit, dan boundary. Ini adalah prediksi atas label CarbonSet modeled. Pada mode existing, profil fitur berasal dari CarbonSet; pada custom, pengguna memasukkan lima fitur. Tidak ada interval prediksi individual yang tervalidasi pada endpoint baseline.

Rekomendasi benchmark menggunakan **sumber embodied yang berbeda dari prediksi kartu hasil**: `Emb_Carbon_Mean` CarbonSet, bukan output Random Forest. Pemisahan ini disengaja dan dijelaskan lagi pada Bagian 9.

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

### 7.4 Compute Carbon Intensity (CCI)

```text
CCI = total_carbon_kg_co2e / completed_compute_work
```

Endpoint mewajibkan karbon non-negatif, workload lebih besar dari nol, `workloadUnit`, `lifecycleBoundary`, dan `analysisPeriod`. UI menghitung numerator sebagai predicted embodied + operational carbon dan meminta workload secara manual. Default/angka input pengguna bukan measurement benchmark. CCI hanya dapat dibandingkan jika unit workload, boundary, periode, dan cakupan sistem sama.

Contoh: 100 kg CO₂e / 10.000.000 gambar = 0,00001 kg CO₂e/gambar = 10 g CO₂e per juta gambar. Numerator dan jumlah gambar harus mencakup sistem/periode yang sama.

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

## 9. MLPerf ResNet-50 dan rekomendasi hardware

### 9.1 Sumber dan satuan performa

Subset runtime berasal dari hasil MLPerf Inference ResNet-50 Offline. `throughput_samples_per_s` ditampilkan sebagai completed inference images per second (gambar/detik). Throughput adalah untuk **seluruh sistem benchmark**, bukan otomatis satu akselerator. Bila sistem berisi delapan perangkat, angka throughput tidak dibagi delapan tanpa bukti scaling.

### 9.2 Kapan rekomendasi muncul

1. Pengguna memilih prosesor **existing** dari CarbonSet.
2. Pengguna mengirim kalkulasi karbon. Kartu rekomendasi baru dirender bila request embodied, operational-carbon, dan CCI semuanya berhasil.
3. Komponen UI memanggil `GET /api/benchmarks/resnet50/recommendations?processorName=<nama>`.
4. Prosesor custom tidak dikirim ke endpoint rekomendasi dan tidak mendapat kartu rekomendasi.

Dengan demikian, kalkulasi operational carbon yang berhasil adalah pemicu UI, bukan input karbon yang dipakai aturan rekomendasi.

### 9.3 Data dan pemetaan

API memuat 38 baris CSV terkurasi saat startup dan melakukan join persis pada nama `carbonset_product` terhadap kolom `Product` CarbonSet. Dataset benchmark harus memuat ID unik, cohort, produk terpetakan, throughput, jumlah inference device, dan URL sumber. ID kosong/duplikat, mapping CarbonSet hilang, device count invalid, throughput invalid, atau skema rusak membuat load gagal terang-terangan.

Baris benchmark hanya bisa ikut rekomendasi jika produk punya CarbonSet embodied mean/min/max yang valid dan cohort-nya berisi setidaknya dua produk CarbonSet berbeda. Hasil API mencakup field benchmark, mapping produk, jumlah device, throughput sistem, top-1 accuracy, CarbonSet mean/min/max per perangkat, dan karbon embodied sistem.

### 9.4 Rumus embodied sistem

Untuk setiap baris benchmark:

```text
system_embodied_mean_kg =
    CarbonSet.Emb_Carbon_Mean × inference_device_count

system_embodied_min_kg =
    CarbonSet.Emb_Carbon_Min × inference_device_count

system_embodied_max_kg =
    CarbonSet.Emb_Carbon_Max × inference_device_count
```

Contoh nyata: NVIDIA A100 PCIe 40 GB memiliki `Emb_Carbon_Mean` sekitar **68,076 kg CO₂e per chip** pada CarbonSet. Sistem benchmark tiga perangkat menjadi sekitar **204,228 kg CO₂e mean embodied** untuk ketiga inference device tersebut. Range Min/Max juga dikalikan tiga dan ditampilkan. Host CPU, memory, motherboard, PSU, chassis, network, cooling, operational electricity/carbon, dan komponen server lain tidak dihitung.

### 9.5 Cohort pembanding

Perbandingan dibatasi pada grup identik menurut empat kolom:

- versi suite MLPerf;
- tipe sistem (misalnya datacenter atau edge);
- kelas konfigurasi (MaxQ/non-MaxQ);
- input data type/precision.

Dataset memiliki delapan cohort dengan lebih dari satu produk CarbonSet, berjumlah 20 baris eligible. Delapan belas baris di cohort satu-produk tidak dipakai untuk rekomendasi lintas produk. Sistem dan versi berbeda tidak digabung begitu saja.

**Batas pembanding:** host model, framework/software stack, jumlah node, dan detail hardware lain tidak menjadi kunci cohort. `accuracy_top1_pct` tersedia dan dapat ditampilkan/dilacak, tetapi bukan syarat filter dalam kode rekomendasi saat ini. Karena itu “cohort sama” bukan jaminan semua aspek benchmark identik; hasil sebaiknya dianggap screening kandidat, bukan uji terkontrol penuh.

### 9.6 Aturan kandidat dan urutan

Suatu sistem kandidat lolos hanya jika:

1. kandidat dan baseline berada pada cohort yang sama dan eligible;
2. produk CarbonSet kandidat berbeda dari prosesor baseline;
3. `candidate.systemEmbodiedCarbonMeanKg <= baseline.systemEmbodiedCarbonMeanKg`; dan
4. `candidate.throughputSamplesPerS > baseline.throughputSamplesPerS`.

Carbon yang dibandingkan adalah **mean point estimate**, bukan syarat bahwa rentang Min/Max saling mendominasi. Ketidakpastian rentang tidak dipakai sebagai filter statistik. API menghapus duplikasi kandidat benchmark ID dengan menyimpan pasangan baseline paling cepat yang memenuhi syarat. Hasil diurutkan menurut peningkatan throughput tertinggi, lalu mean embodied carbon kandidat terendah. UI menampilkan semua hasil yang dikembalikan API; tidak membatasi jumlah rekomendasi tetap.

Aturan ini menghasilkan kandidat trade-off “carbon tidak lebih tinggi dan throughput lebih tinggi”; tidak menghasilkan satu skor gabungan, tidak memilih pemenang universal, dan tidak menyatakan penghematan CCI atau operational emissions.

### 9.7 Mengapa tidak selalu ada hasil

Hasil kosong adalah kondisi yang diharapkan ketika:

- prosesor tidak memiliki benchmark ResNet-50 termapping;
- baseline hanya berada di cohort dengan satu produk CarbonSet;
- tidak ada kandidat dalam cohort sama yang memenuhi kedua syarat carbon dan throughput; atau
- prosesor yang dihitung adalah custom.

Contoh saat ini: Threadripper 1920X memiliki benchmark, tetapi cohort yang tersedia tidak memiliki produk CarbonSet pembanding. Xeon Platinum 8592+ juga tidak memiliki kandidat lintas produk di cohort sebanding. Karena itu pesan “no comparable benchmark cohort” atau “no candidate” tidak berarti API rusak atau kalkulasi karbon gagal.

### 9.8 Perbedaan dari hasil kalkulasi karbon

| Kartu kalkulasi karbon | Rekomendasi benchmark |
|---|---|
| Embodied memakai prediksi Random Forest (existing/custom) | Embodied memakai `Emb_Carbon_Mean` CarbonSet yang dipetakan |
| Operational memakai TDP proxy × waktu × utilisasi × faktor grid | Operational carbon tidak dipakai |
| CCI memakai embodied prediction + operational carbon dibagi workload input pengguna | Tidak menghitung CCI |
| Boundary mengikuti output model dan skenario listrik yang dikirim | CarbonSet inference processor saja, dikalikan jumlah perangkat |
| Berjalan untuk existing dan custom | Hanya prosesor existing dengan benchmark baseline eligible |

### 9.9 Cara membaca hasil dan sumber energi

Komponen menampilkan produk kandidat, system name, jumlah inference device, carbon mean/range kandidat dan baseline, throughput sistem, persentase peningkatan throughput, serta tautan URL hasil MLPerf. Jika mean carbon identik, labelnya “Equal embodied carbon”; jika berbeda, UI menunjukkan selisih mean dan throughput gain.

Data daya dan energi/image yang pernah disusun dari sumber lain tidak menjadi bagian aturan rekomendasi ini. Energi per gambar hanya dapat dihitung dengan rumus `average_power_watt / throughput_images_per_second` bila daya dan throughput berasal dari run yang sama serta boundary daya diketahui. TDP tidak boleh menggantikan measured power untuk perhitungan tersebut.

## 10. Evaluasi, tes, dan reproducibility

### 10.1 Hasil validasi saat dokumen diperbarui

| Validasi | Hasil |
|---|---|
| Backend `npm test` dari `backend/` | 6 tes lulus |
| Frontend `npm run build` dari `frontend/` | Build produksi berhasil |
| Python `unittest discover -s ml-engine/tests -v` | 22 tes lulus; 1 test class model diskip karena environment test variables belum diset |
| scikit-learn artifact | Warning versi: artifact 1.9.1 dibaca dengan runtime 1.8.0 |

Tes backend mencakup API validation/perhitungan, pemetaan CarbonSet ke 38 baris benchmark, jumlah produk dan eligible rows, endpoint benchmark, aturan kandidat, dan kondisi tanpa cohort. Tes Python mencakup preprocessing/group split, embodied artifact contract (diskip bila env khusus tidak tersedia), energy/carbon equation, CCI, custom PC, konservasi massa e-waste, kalkulator STEC, dan batch point/range/incomplete. Tes bukan benchmark performa hardware dan bukan verifikasi power meter.

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

### 10.2 Pemecahan masalah rute benchmark

Jika rute baru memberi `Route not found`, pastikan backend yang berjalan telah dimulai ulang setelah route ditambahkan, request mengarah ke port/base URL backend yang benar, dan `GET /` mencantumkan endpoint benchmark. Route aktif didaftarkan pada `backend/src/app.js`; file dataset benchmark wajib tersedia pada path konfigurasi. Rute yang tidak aktif adalah error deployment/runtime, berbeda dari respons sukses dengan `results: []` yang berarti tidak ada kandidat pembanding.

## 11. Batasan dan interpretasi yang aman

| Topik | Batasan | Dampak |
|---|---|---|
| Embodied model | Label CarbonSet modeled; artifact eksperimental; mismatch versi sklearn | Bukan hasil ukur atau prediksi universal; samakan versi dan validasi luar |
| Operational power | TDP proxy dan input skenario | Bukan pembacaan konsumsi aktual |
| CCI | Workload diinput pengguna, bukan diukur | Placeholder/angka input tidak otomatis mewakili beban benchmark |
| STEC | Evidence fab/node/year tidak lengkap untuk sebagian produk | Hasil dapat berupa range, memakai proxy, atau incomplete |
| Recommendation carbon | Hanya inference device; mean CarbonSet × device count | Tidak setara dengan embodied seluruh server atau total carbon kartu kalkulasi |
| Recommendation performance | Throughput seluruh sistem; cohort hanya empat kunci; accuracy tidak difilter | Screening lintas hasil yang lebih sebanding, bukan uji identik sempurna |
| Recommendation uncertainty | Min/Max ditampilkan tetapi tidak menentukan kelayakan | Perbandingan mean bukan bukti bahwa rentang risiko kandidat lebih baik |
| Coverage | Enam produk dari 1.275 pasangan produk–tipe pada subset | Banyak hardware tidak punya benchmark yang dapat dibandingkan |
| Data tambahan | Dataset mentah riset eksternal tidak seluruhnya ada di repository | Curated CSV dan URL sumber menjadi provenance runtime; rebuild subset belum sepenuhnya otomatis |
| Custom PC/e-waste | Modul Python belum terhubung ke UI/API utama | Jangan menyatakan sebagai fitur UI end-to-end |
| Persistensi | Tidak ada DB runtime yang terverifikasi | Jangan mengklaim hasil tersimpan permanen oleh aplikasi |

Klaim aman untuk presentasi: **“CarbonHardware mengestimasi embodied carbon prosesor memakai model eksperimental yang dilatih pada label CarbonSet; menghitung emisi listrik penggunaan dari skenario TDP dan faktor grid lifecycle; menampilkan STEC location-based dengan status evidence; dan untuk sebagian prosesor existing menampilkan kandidat sistem MLPerf ResNet-50 yang pada cohort tertentu memiliki embodied carbon inference-device setara/lebih rendah serta throughput sistem lebih tinggi. Rekomendasi benchmark terpisah dari total karbon kalkulator, hanya mencakup inference device, dan tidak mencakup emisi operasional server.”**

## 12. Rekomendasi pengembangan

Prioritas berikut menjaga batasan dan mengembangkan evidence secara bertahap:

1. **Perluas coverage benchmark.** Tambahkan throughput ResNet-50 yang punya sumber, versi suite, system configuration, precision, validitas, dan nama produk CarbonSet yang dapat diverifikasi. Fokuskan pengumpulan pada 1.269 pasangan yang belum terpetakan; missing pada subset saat ini bukan berarti data tidak ada di tempat lain.
2. **Perkuat aturan comparable.** Putuskan secara eksplisit kebijakan accuracy tolerance, valid division, host model, software/framework, jumlah node, dan perangkat. Jika aturan berubah, update cohort generator, API, tes, dan dokumentasi sekaligus.
3. **Perjelas uncertainty.** Tentukan apakah Min/Max CarbonSet perlu memengaruhi kelayakan (misalnya robust dominance atau overlap label), bukan hanya mean point estimate.
4. **Samakan boundary.** Untuk rekomendasi server-level, kumpulkan embodied inventory CPU host, accelerator, memory, board, PSU, chassis, dan komponen relevan. Beri label parsial jika inventory belum lengkap.
5. **Sediakan provenance reproduktif.** Simpan input dataset legal/berlisensi, source URL/commit, ID, aturan mapping, schema, versi transformasi, dan laporan pembersihan.
6. **Konsolidasikan dokumentasi dan dependencies.** Samakan README, metadata model, sklearn runtime/artifact version, dan instruksi tes.
7. **Validasi operasional dan CCI.** Bila ingin CCI ResNet-50 yang berbasis energi, pasangkan measured power dan throughput dari run sama, dokumentasikan whole-system boundary, dan hindari mengganti missing power dengan TDP.
8. **Integrasi custom PC/e-waste.** Hanya bila masuk scope produk; sediakan API/UI, katalog faktor berbukti, dan perilaku eksplisit untuk komponen unresolved.

## 13. Glosarium

| Istilah | Arti |
|---|---|
| Embodied carbon | Emisi siklus hidup produk sesuai boundary sumber; baseline CarbonSet adalah output modeled |
| Operational energy | Listrik saat hardware digunakan, dalam kWh |
| Operational carbon | Energi listrik dikali intensitas emisi grid lokasi/waktu |
| STEC | Spatial-Temporal Embodied Carbon; di sini location-based die manufacturing |
| CCI | Compute Carbon Intensity: karbon per unit kerja komputasi selesai |
| TDP | Thermal Design Power; proxy daya dalam skenario, bukan konsumsi terukur |
| Throughput | Pekerjaan selesai per satuan waktu; ResNet-50 dilaporkan sebagai gambar/detik |
| Energy/image | Joule per inference image dari watt terukur dibagi throughput yang cocok |
| Cohort | Kelompok hasil benchmark yang sama pada kunci perbandingan yang ditentukan |
| Boundary | Komponen dan tahap siklus hidup yang masuk ke suatu angka |
| Location-based | Atribusi menggunakan intensitas listrik wilayah fisik dan tahun |
| Market-based | Atribusi faktor kontraktual seperti PPA/REC; belum tersedia |
| Point/range/incomplete | Nilai tunggal / rentang skenario / terblokir bukti atau parameter |
| MAE/RMSE/R² | Metrik regresi: error absolut / error kuadrat / variasi yang dijelaskan; bukan accuracy klasifikasi |

## 14. Peta file utama

| Area | Path | Peran |
|---|---|---|
| Frontend | `frontend/src/App.jsx`, `frontend/src/pages/` | Navigasi dan halaman UI |
| Form dan hasil | `frontend/src/components/HardwareForm.jsx`, `frontend/src/pages/EstimateCarbon.jsx` | Input existing/custom, kalkulasi, hasil |
| UI rekomendasi | `frontend/src/components/Resnet50Recommendations.jsx` | Kartu rekomendasi di bawah hasil kalkulasi |
| Backend routes | `backend/src/app.js`, `backend/src/routes/` | Pendaftaran endpoint |
| Benchmark API | `backend/src/controllers/resnet50-benchmark.controller.js`, `backend/src/services/resnet50-benchmark.service.js` | Kriteria eligibility, join, perhitungan carbon sistem, rekomendasi |
| Perhitungan karbon | `backend/src/controllers/estimate.controller.js`, `backend/src/services/carbon.service.js`, `backend/src/services/metrics.service.js` | Estimasi operational dan CCI |
| Dataset utama | `data/raw/carbonset/`, `data/raw/environmental/`, `data/raw/stec/evidence/` | Input CarbonSet, grid, evidence |
| Benchmark runtime | `data/processed/resnet50-carbonset-benchmark.csv` | Dataset benchmark terkurasi 38 baris |
| Daftar missing | `data/processed/carbonset-products-missing-resnet50-throughput.csv` | Produk–tipe tanpa mapping pada subset benchmark saat ini |
| Dataset STEC | `data/processed/stec-per-chip.csv` | Inventori point/range/incomplete |
| Model | `ml-engine/models/`, `ml-engine/carbon/`, `ml-engine/artifacts/` | Training, inferensi, accounting, artifact |
| Tes backend | `backend/test/api.test.js`, `backend/test/resnet50-benchmark.test.js` | API dan rekomendasi |
| Tes Python | `ml-engine/tests/` | Preprocessing, model contract, accounting, STEC |
| Dokumentasi terkait | `backend/README.md`, `docs/carbon-methodology.md`, `docs/dataset-documentation.md` | Petunjuk implementasi dan metode |
| Sumber PDF ini | `docs/CarbonHardware_Project_Documentation_ID.md` | Naskah yang dapat diedit untuk PDF |
| Generator PDF | `scripts/generate_project_documentation_pdf.py` | Menghasilkan PDF dari naskah Markdown |

## Kesimpulan

CarbonHardware memiliki alur end-to-end untuk estimasi embodied baseline, operational carbon, STEC, CCI, serta rekomendasi ResNet-50 bagi subset hardware CarbonSet yang cocok. Dokumentasi lama keliru menyatakan rekomendasi performa belum terintegrasi; sekarang benchmark terkurasi dipakai backend dan rekomendasi tampil di bawah hasil kalkulasi karbon untuk prosesor existing. Interpretasi yang benar tetap terbatas: rekomendasi membandingkan embodied carbon perangkat inference dari CarbonSet dan throughput MLPerf seluruh sistem pada cohort tertentu. Ia bukan rekomendasi total karbon server, bukan perhitungan CCI, dan tidak menjamin equivalence sempurna di luar kunci cohort yang digunakan.
