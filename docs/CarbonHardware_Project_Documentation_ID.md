# Dokumentasi Proyek CarbonHardware

## Status dokumen

Dokumentasi teknis dan metodologi ini diselaraskan dengan source code, dataset, model, dan tes yang tersedia pada **18 November 2026**. Dokumen ini menjelaskan perilaku implementasi saat ini, bukan rancangan masa depan. Nilai karbon adalah estimasi/model output sesuai batas masing-masing sumber, bukan pengukuran universal atau LCA lengkap.

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

CarbonHardware adalah aplikasi riset yang menggabungkan estimasi embodied carbon prosesor, estimasi listrik dan emisi fase penggunaan, lookup intensitas karbon grid, perhitungan STEC die manufacturing, serta Compute Carbon Intensity (CCI). Aplikasi terdiri dari frontend React/Vite, backend REST Node.js/Express, dan engine Python untuk prediksi embodied serta perhitungan STEC. CSV dan artifact model adalah sumber runtime; backend tidak menggunakan database untuk penyimpanan runtime.

Frontend memiliki tiga halaman navigasi: estimasi embodied/operational carbon, STEC per prosesor, dan perbandingan baseline embodied dengan STEC. Halaman estimasi juga dapat menampilkan perbandingan carbon payback untuk kandidat CarbonSet sejenis.

| Area | Kondisi implementasi | Interpretasi |
|---|---|---|
| Embodied baseline | Random Forest terintegrasi melalui artifact joblib; eksperimental | Prediksi atas label modeled CarbonSet, bukan LCA terukur untuk unit tertentu |
| Operational energy/carbon | Endpoint dan form tersedia; daya diproksikan dengan TDP | Skenario, bukan pengukuran daya aktual |
| STEC | Dataset batch per chip dan kalkulator tersedia | Location-based cradle-to-gate die manufacturing; hasil berstatus point, range, atau incomplete |
| CCI | Endpoint dan input workload tersedia | Valid hanya bila definisi kerja, periode, dan boundary konsisten |
| Perbandingan penggantian | Kandidat CarbonSet sejenis dibandingkan berdasarkan carbon payback | Skenario karbon; kesetaraan workload dan kecocokan hardware tidak divalidasi |
| Database | Tidak digunakan pada alur runtime yang diperiksa | CSV lokal adalah sumber runtime |

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

## 4. Alur pengguna dan API

### 4.1 Alur estimasi karbon

1. Pengguna memilih prosesor CarbonSet **existing** atau memasukkan lima fitur prosesor **custom**.
2. Pengguna memasukkan skenario operasional: jam/hari, tahun pemakaian, utilisasi, hari/tahun, wilayah grid, dan tahun analisis.
3. Pengguna memasukkan jumlah workload selesai dan unitnya untuk CCI.
4. Frontend meminta embodied prediction, operational carbon (yang menyertakan energy dan grid factor), lalu CCI.
5. Hasil baru ditampilkan setelah seluruh request berhasil. CCI UI menjumlahkan predicted embodied dan operational carbon untuk numerator.
6. Jika mode **existing**, aplikasi dapat menampilkan perbandingan carbon payback dengan kandidat CarbonSet bertipe sama.

Perbandingan penggantian adalah analisis skenario terpisah dari CCI dan bukan rekomendasi tanggal penggantian yang tervalidasi. Detail logikanya ada pada Bagian 9.

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

### 5.4 Perbandingan karbon penggantian

Perbandingan penggantian menggunakan metadata prosesor dan embodied carbon dari CarbonSet, tanpa dataset benchmark terpisah. Backend memilih kandidat bertipe sama yang lebih baru, berada dalam rentang tahun rilis katalog, dan memiliki TDP 50% hingga kurang dari TDP prosesor saat ini. Kandidat diurutkan berdasarkan estimasi carbon payback. Aturan ini adalah penyaringan awal dan tidak membuktikan kesetaraan workload atau kecocokan perangkat.

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

## 9. Perbandingan karbon penggantian

Untuk prosesor existing, aplikasi dapat membandingkan kelanjutan penggunaan dengan kandidat CarbonSet bertipe sama. Kandidat dipilih berdasarkan tahun rilis dan rentang TDP sebagai penyaring awal; aturan ini tidak membuktikan bahwa workload atau kemampuan kandidat setara.

```text
annual_savings = current_annual_operational_carbon
                 - candidate_annual_operational_carbon
carbon_payback_years = candidate_embodied_carbon / annual_savings
```

Waktu carbon payback menunjukkan berapa lama penghematan emisi operasional skenario penggantian perlu berlangsung untuk mengimbangi embodied carbon kandidat. Emisi pembuatan prosesor lama dianggap sunk, emisi akhir masa pakai tidak dihitung, dan TDP menjadi proxy daya. Hasilnya merupakan estimasi skenario, bukan tanggal penggantian yang tervalidasi atau jaminan kecocokan hardware.

## 10. Evaluasi, tes, dan reproducibility

### 10.1 Hasil validasi saat dokumen diperbarui

| Validasi | Hasil |
|---|---|
| Backend `npm test` dari `backend/` | 10 tes lulus |
| Frontend `npm run build` dari `frontend/` | Build produksi berhasil |
| Python `unittest discover -s ml-engine/tests -v` | 22 tes lulus; 1 test class model diskip karena environment test variables belum diset |
| scikit-learn artifact | Warning versi: artifact 1.9.1 dibaca dengan runtime 1.8.0 |

Tes backend mencakup validasi API dan perhitungan karbon. Tes Python mencakup preprocessing/group split, embodied artifact contract (diskip bila env khusus tidak tersedia), energy/carbon equation, CCI, custom PC, konservasi massa e-waste, kalkulator STEC, dan batch point/range/incomplete. Tes bukan verifikasi power meter.

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
| Perbandingan penggantian | TDP dan tahun rilis hanya penyaring; workload-equivalence tidak diuji | Carbon payback adalah skenario, bukan tanggal ganti tervalidasi |
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
| Operational energy | Listrik saat hardware digunakan, dalam kWh |
| Operational carbon | Energi listrik dikali intensitas emisi grid lokasi/waktu |
| STEC | Spatial-Temporal Embodied Carbon; di sini location-based die manufacturing |
| CCI | Compute Carbon Intensity: karbon per unit kerja komputasi selesai |
| TDP | Thermal Design Power; proxy daya dalam skenario, bukan konsumsi terukur |
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
