# Task Issue #3: Implementation Planning for `main.py` & Multi-Ticker Stock Visualizer

## 1. Overview & Objective
Dokumen ini berisi spesifikasi teknis dan panduan langkah-demi-langkah (step-by-step) untuk mengimplementasikan *logic app* pada `main.py`. Program ini bertugas mengambil data harga saham/aset dari Yahoo Finance (atau Database lokal jika sudah tersedia), menyimpan/sinkronisasi data ke database SQLite/MySQL/PostgreSQL, serta memvisualisasikan perbandingan antar *ticker* dalam bentuk grafik gambar (`.png`) dan animasi (`.mp4`).

Panduan ini disusun secara eksplisit agar dapat dengan mudah diikuti oleh **Junior Programmer** atau disajikan sebagai instruksi kontekstual untuk **AI Model**.

---

## 2. Directory & File Structure
Seluruh source code aplikasi berada di dalam direktori `src/`. Pastikan struktur folder dan file diatur sebagai berikut:

```text
project-root/
│
├── src/
│   ├── main.py                    # Entry point aplikasi & CLI Argument Parser
│   └── service/                   # Layer modul & bisnis logika
│       ├── __init__.py
│       ├── db.py                  # Module penanganan database (query, insert, check)
│       ├── yahoo_service.py       # Module fetching data dari yfinance
│       ├── controller.py          # Orchestrator / Pengendali alur logika utama
│       └── chart.py               # Module visualisasi (.png statis & .mp4 animasi)
│
├── output/                        # Folder penyimpanan hasil ekspor .png dan .mp4
├── requirements.txt               # Daftar dependencies
└── issue_2.md                     # File perencanaan ini
```

---

## 3. Database Specification & Inspection
Sebelum mengimplementasikan logika penarikan data, lakukan verifikasi struktur tabel terlebih dahulu.
* **Table access** :
* `user` : root
* `pass` : root

### 3.1 Identifikasi Database & Tabel
* **Database Name**: `stock_data`
* **Table Name**: `stock_data` (Catatan: Jika terdapat referensi nama tabel `stock_list` abaikan saja karna itu bagian dari logic apps lainnya, pastikan untuk melakukan normalisasi atau mengecek keberadaan tabel `stock_data` terlebih dahulu).

### 3.2 Struktur Kolom yang Diharapkan
Lakukan inspeksi struktur tabel menggunakan script simulasi sederhana / query:
* `symbol` (VARCHAR/TEXT) — Kode ticker (contoh: `^JKSE`, `BTC-USD`, `BBCA.JK`).
* `date` (DATE/DATETIME) — Tanggal data harga.
* `open` (FLOAT/DOUBLE) — Harga pembukaan.
* `previous_close` (FLOAT/DOUBLE/DECIMAL) — Harga penutupan.
* `high` (FLOAT/DOUBLE) — Harga tertinggi.
* `low` (FLOAT/DOUBLE) — Harga terendah.
* `close` (FLOAT/DOUBLE/DECIMAL) — Harga penutupan.
* `volume` (BIGINT/FLOAT) — Volume perdagangan.
* `created_at` (TIMESTAMP) — Timestamp.
* `created_by` (VARCHAR/TEXT) — User yang input (contoh : "yahoo_api").
* `updated_at` (TIMESTAMP) — Timestamp.
* `updated_by` (VARCHAR/TEXT) — User yang input (contoh : "yahoo_api").

---

## 4. Spesifikasi Argument Parser (CLI Options)

Aplikasi dijalankan via terminal melalui `main.py` dengan mendukung 3 opsi mode input parameter rentang waktu. Semua opsi wajib menerima minimal 1 atau lebih ticker setelah parameter `-t`.

### Mode 1: Rentang Tanggal Spesifik (`-d`)
* **Format Command**:
  ```bash
  python src/main.py -t ^JKSE GF=F BTC-USD -d 01/07/2026 23/07/2026
  ```
* **Deskripsi**:
  * `-t`: Menerima daftar ticker (array/list of strings).
  * `-d`: Menerima 2 string tanggal dengan format `DD/MM/YYYY` (`start_date` dan `end_date`).
* **Handling Tanggal**: Konversi format `DD/MM/YYYY` menjadi `YYYY-MM-DD` untuk query ke Yahoo Finance (`yfinance`) dan Database.

### Mode 2: Interval Hari Kebelakang (`-i`)
* **Format Command**:
  ```bash
  python src/main.py -t BTC-USD BBCA GOTO -i 5
  ```
* **Deskripsi**:
  * `-i`: Integer `X` hari kebelakang dari tanggal hari ini (`today - X days` s/d `today`).

### Mode 3: Periode Kustom (`-p`)
* **Format Command**:
  ```bash
  python src/main.py -t ETH-USD SILVER TLKM -p 1mo
  ```
* **Deskripsi**:
  * `-p`: String periode standar `yfinance` (contoh: `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`).

*Catatan Penting*: Opsi `-d`, `-i`, dan `-p` bersifat *mutually exclusive* (hanya satu mode yang boleh dipakai dalam satu kali eksekusi).

---

## 5. Flow Logika Aplikasi (Controller Logic)

Proses dieksekusi melalui urutan langkah berikut:

```text
[ Input Parameter CLI ]
         │
         ▼
[ Parse Parameter (-t, -d/-i/-p) ]
         │
         ▼
[ Cek Ketersediaan Data di Database (stock_data) ]
    ├── Data Sudah Ada & Lengkap? ────► [ Ambil Data dari Database ]
    └── Data Belum Ada / Kurang? ────► [ Fetch Data dari Yahoo Finance (yfinance) ]
                                                │
                                                ▼
                                    [ Simpan Data Baru ke Database ]
                                                │
                                                ▼
                                    [ Ambil Data Lengkap dari Database ]
         │
         ▼
[ Visualisasi Data via chart.py ]
    ├── Generasi Gambar Line Chart (.png)
    └── Generasi Video Animasi Chart (.mp4)
         │
         ▼
[ Simpan File Output ke Folder output/ ]
```

### Logika Caching & Fetching Data
1. Untuk setiap `ticker` dalam list:
   * Query database `stock_data` untuk memeriksa apakah range tanggal yang diminta sudah tersimpan.
   * **Jika data sudah lengkap di DB**: Langsung ambil dataset dari DB (mencegah redundant API call).
   * **Jika data belum ada / parsial**:
     1. Unduh data dari `yfinance` menggunakan metode `yf.download(ticker, start=..., end=...)` atau `yf.Ticker(ticker).history(period=...)`.
     2. Lakukan data cleansing (handling null values, formatting kolom).
     3. Insert record data ke dalam tabel `stock_data` (gunakan `ON CONFLICT IGNORE` atau `INSERT IGNORE` agar tidak duplicate entry).
2. Tentukan dataset final gabungan seluruh ticker untuk siap divisualisasikan.

---

## 6. Spesifikasi Visualisasi (`chart.py`)

Output grafik perbandingan (*comparison chart*) harus memenuhi standar berikut:

### 6.1 Line Chart (.png)
* Membandingkan pergerakan harga (misal: normalized price / % growth / closing price) antar ticker.
* Setiap ticker wajib menggunakan **warna yang berbeda** (gunakan colormap distinct seperti `tab10` atau palet warna terpisah).
* Lengkapi dengan: Title, X-axis (Tanggal), Y-axis (Harga / % Perubahan), Grid, Legend, dan Watermark/Label.
* Resolusi minimal 300 DPI, disimpan di `output/chart_comparison_<timestamp>.png`.

### 6.2 Animation Chart (.mp4)
* Menggunakan `matplotlib.animation.FuncAnimation` atau `ffmpeg`.
* Menampilkan garis chart bergerak maju secara kumulatif sesuai urutan tanggal.
* Menyimpan file video di `output/chart_animation_<timestamp>.mp4`.

---

## 7. Panduan Implementasi Step-by-Step (Untuk Junior Dev / AI Model)

### Langkah 1: Pengecekan Database
Buat script kecil untuk membaca schema tabel:
```python
# Check table structure
import sqlite3 # Atau mysql.connector / psycopg2 sesuai DB driver
# jalankan "PRAGMA table_info(stock_data);" atau "DESCRIBE stock_data;"
```

### Langkah 2: Buat Helper Database (`src/service/db.py`)
Implementasikan fungsi:
* `get_stock_data(ticker, start_date, end_date)`
* `save_stock_data(df, ticker)`

### Langkah 3: Buat Fetcher Yahoo Finance (`src/service/yahoo_service.py`)
Implementasikan fungsi:
* `fetch_yfinance_data(ticker, start_date, end_date)`
* `parse_period_to_dates(period_str)` / `parse_interval_to_dates(days)`

### Langkah 4: Buat Modul Visualisasi (`src/service/chart.py`)
Implementasikan fungsi:
* `generate_png_chart(df_dict, output_path)`
* `generate_mp4_animation(df_dict, output_path)`

### Langkah 5: Buat Controller Orchestrator (`src/service/controller.py`)
Hubungkan logika `db.py`, `yahoo_service.py`, dan `chart.py`.

### Langkah 6: Implementasi CLI Parser di `src/main.py`
Gunakan library `argparse` untuk menerima argumen CLI `-t`, `-d`, `-i`, dan `-p`.

---

## 8. Kriteria Penerimaan (Acceptance Criteria)

1. Command `-d` berjalan lancar:
   `python src/main.py -t ^JKSE GF=F BTC-USD -d 01/07/2026 23/07/2026`
2. Command `-i` berjalan lancar:
   `python src/main.py -t BTC-USD BBCA GOTO -i 5`
3. Command `-p` berjalan lancar:
   `python src/main.py -t ETH-USD SILVER TLKM -p 1mo`
4. Data baru tersimpan otomatis di database `stock_data`.
5. Data yang sudah ada diambil dari database tanpa memanggil API Yahoo Finance kembali.
6. File `.png` dan `.mp4` berhasil dibuat di folder output dengan garis berwarna beda untuk setiap ticker.
