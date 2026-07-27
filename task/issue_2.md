# Issue #2: Enhance Visual Chart & Video Visualization

## 📌 Ringkasan Tugas
Dokumen perencanaan ini dibuat sebagai panduan langkah demi langkah (*step-by-step implementation plan*) untuk pengembang (*junior programmer*) maupun model AI (*LLM agent*). Tujuan utama dari issue ini adalah meningkatkan visualisasi grafis baik pada chart statis maupun animasi chart format `.mp4`.

---

## 🎯 Spesifikasi & Detail Kebutuhan Feature

### 1. Zero-Baseline & Inisialisasi Tanggal H-1
* **Aturan:**
  * Semua chart wajib dimulai dari koordinat angka **0** baik pada **Sumbu X** maupun **Sumbu Y**.
  * Apabila rentang data utama yang ingin ditampilkan dimulai pada tanggal `13/07/2026`, maka titik data pertama pada chart harus ditarik mundur ke tanggal `12/07/2026` dengan nilai awal `0`.
* **Tujuan:** Menghindari manipulasi visual (*misleading scaling*) dan memberikan titik awal pergerakan (*baseline*) yang konsisten dari nilai nol.

### 2. Format Angka Pasti (Tanpa Singkatan)
* **Aturan:**
  * Seluruh label visualisasi harga wajib menampilkan nominal pasti/lengkap.
  * **Contoh Benar:** `Rp 2.304.299`
  * **Contoh Salah:** `Rp 2,3Jt`, `Rp 2.3M`, `2.3M`

### 3. Presisi Format Angka Sumbu Y
* **Aturan:**
  * Label pada Sumbu Y yang menggunakan pembulatan unit nominal harus ditampilkan tanpa desimal nol jika nilainya bulat (1 digit integer tanpa `.0`).
  * **Contoh Benar:** `Rp 2 juta`
  * **Contoh Salah:** `Rp 2.0 juta`, `Rp 2.00 juta`

### 4. Layout & Zoom Out Viewport (Khusus Render Video `.mp4`)
* **Aturan:**
  * Elemen chart pada format video `.mp4` tidak boleh terpotong (*clipped*) oleh *bounding box* atau *frame* video.
  * Lakukan penyesuaian skala (*zoom out*) atau penambahan *padding/margin* pada canvas area agar:
    * Label pada Sumbu X (tanggal/waktu) terlihat utuh.
    * Label pada Sumbu Y (skala harga) terlihat utuh.
    * Text/badge *final price* pada ujung garis chart tidak terpotong tepi kanan/atas frame.

### 5. Display Pergerakan Harga + %Change Badge (Khusus `.mp4`)
* **Aturan:**
  * Menampilkan informasi pergerakan `harga` beserta persentase perubahan (`%change`) secara *real-time* mengikuti pergerakan animasi garis.
  * Ditampilkan dalam bentuk kotak bersudut tumpul (*rounded box / pill badge*).
  * Warna background/border kotak menyesuaikan dengan warna identitas masing-masing $ticker (atau hijau/merah berdasarkan kondisi *profit/loss*).

### 6. Dynamic Overlay Text Center (Khusus `.mp4`)
* **Aturan:**
  * Menampilkan teks informasi terpusat (*center alignment*) di bagian atas/tengah video chart dengan struktur 3 baris:
    * **Baris 1:** Daftar ticker yang disajikan, contoh: `$BBCA $BMRI $TLKM`
    * **Baris 2:** Tanggal/waktu pergerakan chart saat animasi berjalan (contoh: `13 Juli 2026`)
    * **Baris 3:** Ringkasan performa ticker unggulan dan terendah:
      * `{{ nama $ticker yang unggul }}` -> Ditampilkan dalam *rounded box* berwarna **Hijau**.
      * `{{ nama $ticker yang low }}` -> Ditampilkan dalam *rounded box* berwarna **Merah**.

---

## 🛠️ Tahapan Implementasi (Implementation Steps)

### Tahap 1: Data Preprocessing & Date Handling
1. **Fungsi Inject Baseline Data:**
   * Buat *helper function* `prepare_chart_data(raw_data)`.
   * Deteksi tanggal paling awal dalam dataset (misal: `min_date = '2026-07-13'`).
   * Hitung tanggal `H-1` (misal: `'2026-07-12'`).
   * Sisipkan entry baru pada indeks 0: `{ date: '2026-07-12', value: 0 }`.
2. **Sumbu X & Y Limit Configuration:**
   * Set batas minimum Sumbu Y (`y_min`) secara eksplisit ke angka `0`.
   * Set titik origin Sumbu X bertepatan dengan data awal `H-1`.

### Tahap 2: Standardisasi Formatter Angka
1. **Fungsi Format Nominal Lengkap (`formatCurrencyFull`):**
   * Gunakan format mata uang Rupiah dengan pemisah ribuan titik.
   * Contoh kode Python: `f"Rp {value:,.0f}".replace(",", ".")`
2. **Fungsi Format Label Sumbu Y (`formatYAxisLabel`):**
   * Buat logika pembulatan untuk unit juta/miliar jika Sumbu Y diringkas secara konseptual.
   * Pastikan tidak ada desimal trailing nol (gunakan pembulatan integer / `round()`).
   * Contoh: jika `2.0` maka format menjadi `"Rp 2 juta"`, bukan `"Rp 2.0 juta"`.

### Tahap 3: Penyesuaian Canvas & Viewport Video (`.mp4`)
1. **Margin & Padding Adjustment:**
   * Tambahkan *outer padding* pada konfigurasi chart/canvas (minimal `top: 60px`, `bottom: 50px`, `left: 80px`, `right: 100px`).
   * Atur skala auto-fit / zoom out (misal: `0.85x` - `0.9x`) agar elemen *tooltip* dan *final price tag* di batas paling kanan/atas tidak terpotong tepi layar video.

### Tahap 4: Pembentukan Element Overlay Badge & Real-Time Price Callout
1. **Badge Pergerakan Harga per Ticker:**
   * Buat fungsi *render function* untuk *floating badge* di dekat ujung garis animasi (*head point*).
   * Format isi badge: `{current_price} ({change_percent}%)`.
   * Gambar latar belakang *rounded rectangle* (border radius 8–12px) dengan *fill color* / *border color* sesuai variabel warna ticker.

2. **Overlay Header Text Center:**
   * Layout container teks di posisi atas tengah (*top-center*).
   * **Baris 1:** Text render daftar ticker (contoh: `$BBCA $BMRI`).
   * **Baris 2:** Dynamic date binding sesuai frame animasi saat ini.
   * **Baris 3:** Logika pencarian ticker terbaik & terendah pada frame aktif:
     * Hitung `max_ticker` dan `min_ticker`.
     * Render badge hijau untuk `max_ticker` dan badge merah untuk `min_ticker`.

---

## 📋 Checklist Pengujian (Definition of Done)

- [ ] Chart dimulai dari tanggal H-1 dengan nilai 0 pada Sumbu X dan Y.
- [ ] Angka pada chart berbentuk nominal penuh tanpa singkatan (e.g. `Rp 2.304.299`).
- [ ] Label Sumbu Y menggunakan format 1 digit bulat tanpa desimal nol (e.g. `Rp 2 juta`).
- [ ] Hasil render `.mp4` tidak memiliki teks/label/garis yang terpotong di tepi frame.
- [ ] Video `.mp4` secara dinamis menampilkan harga & `%change` dalam *rounded box*.
- [ ] Teks center di video `.mp4` menampilkan 3 baris lengkap beserta badge hijau (unggul) & merah (low).
