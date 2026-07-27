# [Task] Implementation: Yahoo Finance Ticker Chart Visualizer (Static PNG & Animated MP4)

## 📌 Deskripsi Brief
Proyek ini bertujuan untuk membuat modul layanan visualisasi data ticker dari Yahoo Finance menggunakan Python. Output dari modul ini adalah:
1. **Gambar Statis (`.png`)**: Format Landscape `1920x1080` (untuk Feed / Social Media Post).
2. **Video Animasi (`.mp4`)**: Format Vertical `1080x1920` (fit to size untuk TikTok, Instagram Reels, dan YouTube Shorts).

Tugas ini ditujukan sebagai fondasi awal visualisasi (*layout, theme, & rendering engine*). Logika bisnis aplikasi tingkat lanjut belum diperlukan, fokus utama adalah estetika chart, akurasi visualisasi theme, dan modularitas struktur kode.

---

## 🗂️ Struktur Direktori Target

Program harus mengikut pola struktur folder berikut:

```text
root/
└── src/
    └── service/
        └── chart.py
```

---

## 🎨 Spesifikasi Visual & Styling Chart

Setiap chart yang dihasilkan (statis & animasi) wajib memenuhi standar desain berikut:

| Parameter Visual | Spesifikasi / Aturan |
| :--- | :--- |
| **Theme / Background** | Dark Theme `#0f172a` |
| **Warna Teks & Font** | Semua teks berwarna Putih (`#FFFFFF`), Font Size = `11` |
| **Header / Judul Center** | Berada di bagian atas/tengah dengan format 3 baris:<br>`$ticker, $ticker, $ticker`<br>`<Tanggal dinamis sesuai range chart>`<br>`<Nama $ticker yang memimpin/lead>` |
| **Sumbu Y (Kiri)** | Harga yang **sudah dikonversi ke IDR secara realtime** (ambil kurs USD/IDR terbaru saat script berjalan). Format mata uang rapi (contoh: `Rp 15.000` / `Rp 2,5 Juta`). |
| **Sumbu X (Bawah)** | Format Tanggal/Periode:<br>• Jika dalam rentang periode tahunnya sama: Tampilkan hanya **`Bulan`** (contoh: `Juni`).<br>• Jika rentang periode melewati tahun berbeda: Tampilkan **`Bulan Tahun`** (contoh: `Juni 2026`). |
| **Line & Glow Effect** | Efek menyala (*Glow Effect*) dibuat dengan cara **Double Plotting** (garis utama + garis kedua dengan `alpha` transparan & `linewidth` lebih tebal di bawahnya). |
| **Area Fill** | Transparan di bawah garis menggunakan `fill_between` (alpha ~`0.15` - `0.25`). |
| **Marker & Last Value** | Marker poin data diperbesar. Nilai/titik data terakhir (*last value*) diberi penanda warna yang selaras dengan warna garis ticker. |
| **Grid & Spine** | Grid terlihat jelas tetapi halus/tidak bold (`alpha` rendah). Line Spine (bingkai chart) dibuat tipis. |
| **Legend** | Style *Dark Glass* (background gelap semi-transparan dengan border tipis). |

---

## 📝 Tahapan Langkah Implementasi (Step-by-Step)

Petunjuk bagi Junior Programmer / AI Agent untuk mengimplementasikan modul ini:

### **Langkah 1: Environment & Dependency Setup**
1. Buat virtual environment Python (opsional tapi disarankan).
2. Install library yang dibutuhkan:
   ```bash
   pip install yfinance matplotlib pandas numpy requests moviepy
   ```
   *(Catatan: `moviepy` atau `matplotlib.animation` dengan `ffmpeg` dibutuhkan untuk merender file `.mp4`)*.

---

### **Langkah 2: Pembuatan Struktur File**
1. Buat folder `src/service/`.
2. Buat file `src/service/chart.py`.

---

### **Langkah 3: Helper Konversi Mata Uang IDR (Realtime)**
Di dalam `chart.py`:
1. Buat fungsi helper `get_usd_to_idr_rate()` menggunakan `yfinance` (`USDIDR=X`) atau API exchange rate publik gratis.
2. Ambil kurs realtime saat fungsi dipanggil untuk mengonversi data harga dari USD ke IDR.

---

### **Langkah 4: Fetch Data Ticker dari Yahoo Finance**
1. Gunakan library `yfinance` untuk mengambil histori harga beberapa ticker (contoh: `AAPL`, `NVDA`, `MSFT` atau saham lokal).
2. Bersihkan dan selaraskan dataframe pandas (handling missing value / null).
3. Kalikan nilai kolom `Close` / `Adj Close` dengan kurs IDR yang didapatkan.

---

### **Langkah 5: Penanganan Format Sumbu X (Smart Month/Year Formatting)**
1. Buat fungsi formatter tanggal untuk Sumbu X:
   - Cek `min_year` dan `max_year` dari rentang data chart.
   - Jika `min_year == max_year`: Format label sumbu X menjadi `%B` (contoh: `Juni`).
   - Jika `min_year != max_year`: Format label sumbu X menjadi `%B %Y` (contoh: `Juni 2026`).

---

### **Langkah 6: Implementasi Visualisasi Statis (`.png`)**
1. Set kanvas Matplotlib: `fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)`.
2. Set background figure & axes ke `#0f172a`.
3. Implementasikan styling:
   - Plot garis dengan **Glow Effect** (plot 1: linewidth tebal alpha 0.3; plot 2: linewidth normal solid).
   - `ax.fill_between` transparan di bawah garis.
   - Set warna spine ke abu-abu tipis / transparan.
   - Set grid `color='white'`, `alpha=0.15`, `linestyle='--'`.
   - Set legend dengan frame dark glass: `facecolor='#1e293b'`, `edgecolor='#334155'`, `alpha=0.8`.
   - Sorot nilai terakhir (*last data point*) dengan marker khusus & anotasi angka harga IDR selaras warna garis.
4. Set Title/Header di tengah (*center aligned*):
   - Line 1: `$AAPL, $NVDA, $MSFT`
   - Line 2: Rentang Tanggal (contoh: `01 Jan 2026 - 30 Jun 2026`)
   - Line 3: Ticker dengan performa tertinggi/leading (contoh: `NVDA Leading (+25.4%)`)
5. Simpan gambar dengan resolusi tepat: `plt.savefig("output.png", dpi=100, facecolor=fig.get_facecolor())`.

---

### **Langkah 7: Implementasi Visualisasi Animasi (`.mp4`)**
1. Ubah dimensi kanvas ke rasio vertikal: `figsize=(10.8, 19.2)` (1080x1920 px).
2. Gunakan `matplotlib.animation.FuncAnimation`:
   - Animasikan data dari frame pertama hingga frame terakhir secara sekuensial (efek garis bertambah panjang seiring waktu).
   - Pastikan header/title dan angka harga pada nilai terakhir di-update secara dinamis pada setiap frame animasi.
3. Render dan simpan ke format MP4:
   ```python
   writer = FFCustomWriter / FFMpegWriter(fps=30)
   anim.save("output.mp4", writer=writer)
   ```

---

## ✅ Kriteria Selesai (Definition of Done)
- [ ] File `src/service/chart.py` dapat dijalankan tanpa error.
- [ ] Menghasilkan file `.png` (1920x1080) dengan background `#0f172a`, font size 11, glow effect, dan format IDR.
- [ ] Menghasilkan file `.mp4` (1080x1920) animasi gerakan garis chart yang smooth.
- [ ] Header teks sesuai format 3 baris dan *center aligned*.
- [ ] Sumbu X menampilkan `Bulan` jika tahun sama, atau `Bulan Tahun` jika tahun berbeda.
- [ ] Penanda nilai terakhir (*last value*) berwarna sama dengan garis ticker.
