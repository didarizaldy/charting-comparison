# Issue #4: Peningkatan Visualisasi Animation Chart (.mp4)

## 📌 Ringkasan Tugas
Dokumen perencanaan ini dibuat sebagai panduan teknis (*step-by-step implementation guide*) untuk **Junior Programmer** atau **AI Model** dalam mengimplementasikan peningkatan (*enhancement*) pada modul pembuat video animasi grafik (`.mp4`).

Tujuan utama dari task ini adalah menyempurnakan tampilan visual chart agar lebih bersih, berfokus pada data esensial, serta memiliki penanganan sumbu waktu (X-axis) yang lebih intuitif dan rapi.

---

## 🎯 Detail Kebutuhan Feature & Spesifikasi

### 1. Format Nama Ticker (Pembersihan Simbol `$`)
* **Masalah:** Saat ini nama ticker saham/kripto diawali dengan karakter `$` (misal: `$BBCA`, `$BMRI`, `$BTC`).
* **Solusi:** Hapus simbol `$` pada seluruh label visualisasi chart, legend, maupun tooltip video.
* **Spesifikasi:**
  * Input: `"$BBCA"` $ightarrow$ Output Visual: `"BBCA"`
  * Gunakan sanitasi string yang aman (misal `.lstrip('$')` atau `.replace('$', '')`).

---

### 2. Limitasi Visual Ticker ke Top 3 Dinamis
* **Masalah:** Ketika grafik memuat lebih dari 3 ticker, visualisasi menjadi terlalu ramai/menumpuk.
* **Solusi:** 
  * Jika total ticker yang diproses **> 3**, batasi tampilan chart hanya untuk **Top 3 Ticker Utama (Leading Tickers)** pada setiap *frame* / interval waktu.
  * Tampilan harus **dinamis**: Jika ticker peringkat 4 menyalip peringkat 3 pada tanggal tertentu, animasi harus secara halus merefleksikan perubahan posisi tersebut.
* **Spesifikasi Logic:**
  1. Di setiap frame/step animasi:
     * Hitung nilai/performa dari semua ticker yang aktif.
     * Urutkan secara *descending* (nilai tertinggi ke terendah).
     * Ambil 3 ticker teratas pada frame tersebut.
  2. Sembunyikan (*hide/filter out*) ticker di luar Top 3 dari kanvas gambar pada frame tersebut.
  3. Jika total ticker yang diberikan $\le 3$, tampilkan seluruh ticker seperti biasa.

---

### 3. Reformating & Penyimulasian Sumbu X (X-Axis) Tanggal & Tahun
* **Masalah:** Sumbu X (*time axis*) saat ini menampilkan tanggal lengkap beserta bulan (misal `15 Jan`, `20 Feb`), yang menyebabkan teks menumpuk (*overlapping*) ketika rentang waktu panjang.
* **Solusi:** Ubah format X-axis hanya menampilkan **Bulan** saja (tanpa tanggal), serta lakukan penyesuaian otomatis jika rentang waktu mencakup **multi-bulan** dan **multi-tahun**.
* **Spesifikasi Format & Simulasi:**
  * **Kasus 1: Dalam 1 Tahun yang Sama (contoh: Jan - Des 2026)**
    * Tampilkan nama bulan saja.
    * Contoh label Ticks: `Jan`, `Feb`, `Mar`, `Apr`, `Mei`, dst.
  * **Kasus 2: Lintas Tahun / Multi-Year (contoh: Nov 2025 - Mar 2026)**
    * Tampilkan bulan dan penanda tahun secara proporsional agar audiens tidak bingung pergantian tahun.
    * Contoh label Ticks: `Nov 25`, `Des 25`, `Jan 26`, `Feb 26`, `Mar 26` **atau** tampilkan label tahun (`2026`) khusus pada pergantian tahun.
  * **Aturan Tick Spacing (Interval):**
    * Jangan tampilkan tick untuk *setiap hari*. Kelompokkan tick berdasarkan interval bulanan (misal tanggal 1 setiap bulan, atau pertengahan bulan).
    * Pastikan *tick locator* pada library grafik (Matplotlib `MonthLocator`, Plotly, dll) diset ke level bulanan.

---

## 🛠️ Tahapan Implementasi (Step-by-Step Guide)

### **Tahap 1: Analisis Kode & Setup Lingkungan**
1. Lokasikan file utama yang bertanggung jawab meng-generate grafik dan video `.mp4` (contoh: `chart_generator.py`, `animator.py`, atau skrip terkait).
2. Identifikasi library rendering animasi yang digunakan (contoh: `matplotlib.animation`, `bar_chart_race`, `moviepy`, `plotly`, atau `manim`).

---

### **Tahap 2: Implementasi Sanitasi Nama Ticker (Task 1)**
1. Temukan bagian kode yang membaca daftar ticker atau menembagakan teks label pada chart.
2. Buat helper function sederhana:
   ```python
   def clean_ticker_symbol(symbol: str) -> str:
       if not symbol:
           return ""
       return str(symbol).replace('$', '').strip()
   ```
3. Terapkan fungsi ini pada:
   * Label garis/batang grafik.
   * Legend chart (jika ada).
   * Judul/Subtitle (jika memuat nama ticker).

---

### **Tahap 3: Implementasi Logic Top 3 Dinamis (Task 2)**
1. Temukan loop utama pembuatan frame animation (*update function* / *frame generator*).
2. Sebelum merender data pada frame `t`:
   ```python
   # Contoh Pseudocode Filtering Top 3
   current_frame_data = get_data_at_frame(t) # dict/dataframe berisi nilai ticker pada waktu t
   
   # Sort berdasarkan nilai terbanyak/tertinggi
   sorted_tickers = sorted(current_frame_data.items(), key=lambda x: x[1], reverse=True)
   
   # Ambil top 3
   top_3_tickers = dict(sorted_tickers[:3])
   
   # Render hanya data top_3_tickers ke chart
   render_chart_frame(top_3_tickers)
   ```
3. Pastikan transisi warna tetap konsisten per ticker (misal: BBCA selalu warna biru, BMRI selalu warna mandiri kuning, dst) meskipun posisi peringkatnya berubah-ubah agar tidak membingungkan penonton.

---

### **Tahap 4: Formatting & Simulasi Sumbu X / X-Axis (Task 3)**
1. Ubah konfigurasi *Date Formatter* dan *Date Locator* pada sumbu X.
2. Jika menggunakan **Matplotlib**:
   ```python
   import matplotlib.dates as mdates

   # Atur agar tick muncul setiap bulan
   ax.xaxis.set_major_locator(mdates.MonthLocator())

   # Buat kondisi format berdasarkan rentang tahun
   start_year = df['date'].min().year
   end_year = df['date'].max().year

   if start_year == end_year:
       # Dalam tahun yang sama: Tampilkan hanya bulan (misal: 'Jan', 'Feb')
       ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
   else:
       # Lintas tahun: Tampilkan Bulan + Tahun singkat (misal: 'Jan 25', 'Feb 26')
       ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
   ```
3. Lakukan pengujian simulasi data pada 3 skenario:
   * **Skenario A:** Data 3 bulan dalam 1 tahun (misal: Jan 2026 - Mar 2026).
   * **Skenario B:** Data 12 bulan penuh (Jan 2026 - Des 2026).
   * **Skenario C:** Data lintas tahun (Okt 2025 - Mei 2026).

---

### **Tahap 5: Rendering Video & Quality Check**
1. Jalankan proses *export* / *rendering* video `.mp4`.
2. Periksa hasil video output secara visual.

---

## ✅ Checklist Pengujian (Acceptance Criteria)

Sebelum PR (*Pull Request*) disetujui, pastikan kriteria berikut terpenuhi:

- [ ] **Tidak ada simbol `$`** pada seluruh teks ticker di dalam video `.mp4`.
- [ ] **Maksimal 3 ticker** yang tampil secara bersamaan di layar saat grafik bergerak.
- [ ] Ticker yang tampil secara dinamis berganti sesuai dengan peringkat 3 teratas pada rentang waktu tersebut.
- [ ] Warna masing-masing ticker tetap konsisten meskipun urutan/posisinya berubah.
- [ ] **Sumbu X hanya menampilkan Nama Bulan** (tanpa tanggal seperti `01`, `15`, dst).
- [ ] Jika data mencakup lebih dari 1 tahun, Sumbu X dengan jelas menampilkan penanda tahun (misal `Jan 25`, `Jan 26`).
- [ ] Video `.mp4` berhasil di-render tanpa crash / error memori.

---

## 📄 Tanggapan & Output Yang Diharapkan
- **Output:** File video animasi `.mp4` dengan visualisasi yang sudah diperbaiki sesuai kriteria di atas.
- **Status Response:** `-` (Akan diverifikasi oleh reviewer setelah submission).
