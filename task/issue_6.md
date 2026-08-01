# Issue #6: Database Caching Enhancement — Check DB First, Fallback to Yahoo Finance

## 📌 Ringkasan Tugas
Dokumen perencanaan ini dibuat sebagai panduan langkah-demi-langkah (*step-by-step implementation guide*) untuk **Junior Programmer** atau **AI Model** dalam mengimplementasikan peningkatan (*enhancement*) pada logika pengambilan data dan penyimpanan ke database.

**Tujuan Utama:**
1. Jika data sudah tersedia di database `stock_data`, gunakan data tersebut (tanpa fetch ulang).
2. Jika data belum tersedia di database, lakukan fetch dari Yahoo Finance (`yfinance`), lalu simpan ke database.
3. Lakukan pengujian menggunakan data lama (tahun 2024 / 2025) untuk memvalidasi fitur.

---

## 🎯 Analisis Kode Saat Ini (*Current Implementation Review*)

Saat ini, logika database caching sudah ada di `controller.py` pada **Step 3**:

```python
# 3a. Check if data already exists in DB
if db.check_data_completeness(ticker, start_date, end_date):
    print(f"  >> Using cached data from database")
    continue

# 3b. Fetch from Yahoo Finance
yf_df = yahoo_service.fetch_yfinance_data(ticker, start_date, end_date)

# 3c. Save to database
db.save_stock_data(yf_df, ticker)
```

Namun, masih ada beberapa kelemahan yang perlu diperbaiki:
- **Ketergantungan pada `check_data_completeness`** yang belum sempurna (masih ada *tolerance* yang longgar).
- **Tidak ada mekanisme *partial fetch*** — jika data hanya kurang beberapa hari, tetap fetch seluruh rentang.
- **Tidak ada validasi** apakah data yang di-fetch benar-benar mencakup rentang tanggal yang diminta.
- **Belum ada penanganan** jika data di DB lebih lengkap dari rentang yang diminta.

---

## 🗂️ File yang Akan Dimodifikasi

| File | Perubahan |
| :--- | :--- |
| `src/service/controller.py` | Enhance logika *cache-first* pipeline |
| `src/service/db.py` | Perbaiki `check_data_completeness` agar lebih presisi |
| `src/service/yahoo_service.py` | (Opsional) Tambahkan fungsi *partial fetch* jika diperlukan |

---

## 🛠️ Tahapan Implementasi (Step-by-Step Guide)

### Tahap 1: Perbaiki `check_data_completeness` di `db.py`

**Tujuan:** Membuat pengecekan ketersediaan data lebih ketat dan presisi.

**Langkah-langkah:**

1. Buka file `src/service/db.py`.
2. Temukan fungsi `check_data_completeness()`.
3. Ubah logika pengecekan menjadi sebagai berikut:
   - Hitung jumlah **hari kerja (business days)** antara `start_date` dan `end_date` (gunakan `pd.bdate_range` atau `np.busday_count`).
   - Bandingkan jumlah tersebut dengan jumlah baris data yang ada di DB.
   - Jika **selisih jumlah baris ≤ threshold** (misal: selisih 2-3 hari karena hari libur pasar), anggap data lengkap.
   - Jika **selisih > threshold**, kembalikan `False` agar dilakukan fetch ulang.

```python
# Pseudocode — contoh implementasi
import numpy as np

def check_data_completeness(ticker: str, start_date: str, end_date: str) -> bool:
    df = get_stock_data(ticker, start_date, end_date)
    if df.empty:
        return False

    # Hitung jumlah hari kerja dalam rentang
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    expected_days = np.busday_count(start_dt.date(), end_dt.date() + timedelta(days=1))

    # Ambil tanggal unik dari DB
    db_dates = pd.to_datetime(df['date']).dt.date
    unique_dates = set(db_dates)
    actual_days = len(unique_dates)

    # Toleransi: selisih maksimal 3 hari (karena hari libur tak terduga)
    tolerance = 3
    is_complete = (expected_days - actual_days) <= tolerance

    if is_complete:
        print(f"  DB check [{ticker}]: data found ({actual_days}/{expected_days} days)")
    else:
        print(f"  DB check [{ticker}]: incomplete ({actual_days}/{expected_days} days, missing {expected_days - actual_days})")

    return is_complete
```

4. **Catatan Penting:** Hapus atau ganti logika *tolerance* berbasis `timedelta(days=3)` yang lama dengan logika berbasis **jumlah hari kerja** di atas.

---

### Tahap 2: Enhance Logika Cache-First Pipeline di `controller.py`

**Tujuan:** Membuat pipeline yang lebih cerdas dengan fallback bertahap.

**Langkah-langkah:**

1. Buka file `src/service/controller.py`.
2. Temukan bagian **Step 3** (sekitar baris 90-110).
3. Ubah logikanya menjadi sebagai berikut:

```python
# ── Step 3: For each ticker, check DB → fetch (partial if needed) → save ──
for ticker in tickers:
    print(f"\n[{ticker}]")

    # 3a. Cek apakah data di DB sudah lengkap
    if db.check_data_completeness(ticker, start_date, end_date):
        print(f"  ✓ Data lengkap di database — menggunakan cache")
        continue

    # 3b. Cek apakah ada data parsial di DB
    existing_df = db.get_stock_data(ticker, start_date, end_date)
    if not existing_df.empty:
        # Data parsial tersedia — cari rentang tanggal yang hilang
        print(f"  ⚠ Data parsial ditemukan ({len(existing_df)} rows), mencari tanggal yang kurang...")
        missing_ranges = _find_missing_date_ranges(existing_df, start_date, end_date)

        if missing_ranges:
            # Fetch hanya untuk rentang tanggal yang hilang
            for miss_start, miss_end in missing_ranges:
                print(f"  >> Fetch missing range: {miss_start} to {miss_end}")
                partial_df = yahoo_service.fetch_yfinance_data(ticker, miss_start, miss_end)
                if not partial_df.empty:
                    db.save_stock_data(partial_df, ticker)
                    print(f"  ✓ Saved {len(partial_df)} rows for missing range")
    else:
        # 3c. Tidak ada data sama sekali — fetch full range
        print(f"  >> Tidak ada data di DB — fetch dari Yahoo Finance...")
        yf_df = yahoo_service.fetch_yfinance_data(ticker, start_date, end_date)

        if yf_df.empty:
            print(f"  ✗ WARNING: Tidak ada data untuk {ticker}")
            continue

        # Validasi: pastikan data mencakup rentang tanggal yang diminta
        fetched_start = yf_df['Date'].min().strftime('%Y-%m-%d')
        fetched_end = yf_df['Date'].max().strftime('%Y-%m-%d')
        print(f"  >> Rentang data: {fetched_start} → {fetched_end}")

        # 3d. Simpan ke database
        db.save_stock_data(yf_df, ticker)
        print(f"  ✓ Data disimpan ({len(yf_df)} rows)")
```

4. Tambahkan fungsi helper `_find_missing_date_ranges()` di `controller.py` untuk mendeteksi rentang tanggal yang kosong:

```python
def _find_missing_date_ranges(
    existing_df: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> List[Tuple[str, str]]:
    """
    Mendeteksi rentang tanggal yang hilang dari data yang sudah ada di DB.

    Args:
        existing_df: DataFrame yang berisi data dari DB (kolom 'date')
        start_date: Start date 'YYYY-MM-DD'
        end_date: End date 'YYYY-MM-DD'

    Returns:
        List of (missing_start, missing_end) tuples
    """
    from datetime import datetime, timedelta

    # Buat set tanggal yang sudah ada di DB
    existing_dates = set(pd.to_datetime(existing_df['date']).dt.date)

    # Buat daftar semua tanggal (setiap hari, bukan hanya hari kerja)
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    all_dates = []
    current = start_dt
    while current <= end_dt:
        all_dates.append(current)
        current += timedelta(days=1)

    # Cari rentang yang hilang
    missing_ranges = []
    in_gap = False
    gap_start = None

    for d in all_dates:
        if d not in existing_dates:
            if not in_gap:
                gap_start = d
                in_gap = True
        else:
            if in_gap:
                missing_ranges.append((
                    gap_start.strftime('%Y-%m-%d'),
                    (d - timedelta(days=1)).strftime('%Y-%m-%d'),
                ))
                in_gap = False

    # Jika masih ada gap di akhir
    if in_gap:
        missing_ranges.append((
            gap_start.strftime('%Y-%m-%d'),
            end_dt.strftime('%Y-%m-%d'),
        ))

    return missing_ranges
```

---

### Tahap 3: Tambahkan Validasi Data Sebelum Disimpan

**Tujuan:** Memastikan data yang akan disimpan ke DB tidak korup atau kosong.

**Langkah-langkah:**

1. Di `db.py`, sebelum menyimpan data di fungsi `save_stock_data()`, tambahkan validasi:
   - Pastikan kolom `Date` (atau `date`) tidak null.
   - Pastikan kolom `Close` (atau `close`) tidak null.
   - Pastikan jumlah baris > 0.

2. Contoh validasi:

```python
def save_stock_data(df: pd.DataFrame, ticker: str) -> int:
    if df.empty:
        print(f"  No data to save for {ticker}")
        return 0

    # Validasi: pastikan ada kolom Date
    date_col = None
    for col in df.columns:
        if col.lower() == 'date':
            date_col = col
            break

    if date_col is None:
        print(f"  ERROR: DataFrame untuk {ticker} tidak memiliki kolom Date")
        return 0

    # Validasi: pastikan ada kolom Close
    close_col = None
    for col in df.columns:
        if col.lower() == 'close':
            close_col = col
            break

    if close_col is None:
        print(f"  ERROR: DataFrame untuk {ticker} tidak memiliki kolom Close")
        return 0

    # ... (lanjut dengan logika penyimpanan yang sudah ada)
```

---

### Tahap 4: Implementasi Logika Upsert (Update or Insert)

**Tujuan:** Jika data sudah ada di DB untuk tanggal tertentu tetapi nilainya berbeda (misal: *adjusted close* diperbarui), data tersebut diperbarui (*update*) bukan diabaikan (*ignore*).

**Langkah-langkah:**

1. Di `db.py`, ubah query `INSERT OR IGNORE` menjadi `INSERT OR REPLACE` atau gunakan `UPDATE` terlebih dahulu.

2. Contoh implementasi dengan logika *upsert*:

```python
def save_stock_data(df: pd.DataFrame, ticker: str) -> int:
    # ... (validasi seperti di Tahap 3)

    conn = _get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    rows_affected = 0

    for idx in range(len(df)):
        row = df.iloc[idx]
        date_val = row[date_col]

        # Parse date
        if hasattr(date_val, 'strftime'):
            date_str = date_val.strftime('%Y-%m-%d')
        else:
            date_str = str(pd.to_datetime(date_val).strftime('%Y-%m-%d'))

        # Cek apakah data sudah ada untuk tanggal ini
        cursor.execute(
            "SELECT id FROM stock_data WHERE symbol = ? AND date = ?",
            (ticker, date_str)
        )
        existing = cursor.fetchone()

        if existing:
            # Update data yang sudah ada
            cursor.execute("""
                UPDATE stock_data
                SET open = ?, previous_close = ?, high = ?, low = ?,
                    close = ?, volume = ?, updated_at = ?, updated_by = ?
                WHERE symbol = ? AND date = ?
            """, (
                float(row[open_col]) if hasattr(row, open_col) and not pd.isna(row[open_col]) else None,
                float(row[prev_close_col]) if hasattr(row, prev_close_col) and not pd.isna(row[prev_close_col]) else None,
                float(row[high_col]) if hasattr(row, high_col) and not pd.isna(row[high_col]) else None,
                float(row[low_col]) if hasattr(row, low_col) and not pd.isna(row[low_col]) else None,
                float(row[close_col]) if hasattr(row, close_col) and not pd.isna(row[close_col]) else None,
                float(row[vol_col]) if hasattr(row, vol_col) and not pd.isna(row[vol_col]) else None,
                now,
                SYSTEM_USER,
                ticker,
                date_str,
            ))
        else:
            # Insert data baru
            cursor.execute("""
                INSERT INTO stock_data
                    (symbol, date, open, previous_close, high, low, close, volume,
                     created_at, created_by, updated_at, updated_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                date_str,
                # ... (nilai-nilai kolom)
                now,
                SYSTEM_USER,
                now,
                SYSTEM_USER,
            ))

        rows_affected += 1

    conn.commit()
    conn.close()
    print(f"  Saved {rows_affected} rows for {ticker} (upsert)")
    return rows_affected
```

> **Catatan:** Jika implementasi *upsert* terlalu kompleks, alternatif yang lebih sederhana adalah tetap menggunakan `INSERT OR IGNORE` seperti saat ini (karena data historis jarang berubah).

---

### Tahap 5: Pengujian dengan Data Lama (Tahun 2024 / 2025)

**Tujuan:** Memvalidasi bahwa fitur *cache-first* bekerja dengan benar menggunakan data historis.

**Langkah-langkah Pengujian:**

#### Test Case 1: Fresh Fetch (Belum Ada Data di DB)

```bash
# Hapus database terlebih dahulu agar bersih
# Jalankan dengan data tahun 2024
python src/main.py -t ^JKSE BBCA.JK BMRI.JK -d 01/01/2024 31/01/2024
```

**Ekspektasi:**
- Semua ticker di-fetch dari Yahoo Finance.
- Data disimpan ke database `stock_data`.
- Chart PNG dan MP4 berhasil digenerate.

---

#### Test Case 2: Cache Hit (Data Sudah Ada di DB)

```bash
# Jalankan ulang dengan rentang tanggal yang sama
python src/main.py -t ^JKSE BBCA.JK BMRI.JK -d 01/01/2024 31/01/2024
```

**Ekspektasi:**
- Muncul pesan: `Data lengkap di database — menggunakan cache`.
- Tidak ada fetch dari Yahoo Finance.
- Chart tetap berhasil digenerate.

---

#### Test Case 3: Partial Cache (Data Sebagian Ada)

```bash
# Jalankan dengan rentang yang lebih lebar (sebagian sudah ada, sebagian belum)
python src/main.py -t BBCA.JK -d 01/01/2024 29/02/2024
```

**Ekspektasi:**
- Data untuk Januari 2024 di-skip (cache hit).
- Data untuk Februari 2024 di-fetch dari Yahoo Finance.
- Data baru disimpan ke database.

---

#### Test Case 4: Cache dengan Rentang Tahun Penuh (2024)

```bash
# Test dengan tahun penuh
python src/main.py -t ^JKSE BBCA.JK BMRI.JK TLKM.JK -d 01/01/2024 31/12/2024
```

**Ekspektasi:**
- Butuh waktu lebih lama untuk fetch pertama kali.
- Pada eksekusi kedua, semua data menggunakan cache.
- Chart menampilkan data setahun penuh.

---

#### Test Case 5: Cache dengan Rentang 2025

```bash
python src/main.py -t BTC-USD ETH-USD ^JKSE -d 01/06/2025 30/06/2025
```

**Ekspektasi:**
- Data di-fetch dan disimpan ke database.
- Eksekusi ulang menggunakan cache.
- Tidak ada error atau data ganda.

---

### Tahap 6: Verifikasi Data di Database

**Tujuan:** Memastikan data tersimpan dengan benar di database SQLite.

**Langkah-langkah:**

1. Setelah menjalankan test case, verifikasi data di database:
   ```bash
   sqlite3 data/stock_data.db
   ```

2. Jalankan query untuk memeriksa jumlah data per ticker:
   ```sql
   SELECT symbol, COUNT(*) as row_count,
          MIN(date) as first_date, MAX(date) as last_date
   FROM stock_data
   GROUP BY symbol
   ORDER BY symbol;
   ```

3. Jalankan query untuk memeriksa duplikasi:
   ```sql
   SELECT symbol, date, COUNT(*)
   FROM stock_data
   GROUP BY symbol, date
   HAVING COUNT(*) > 1;
   ```

**Ekspektasi:**
- Tidak ada duplikasi data (UNIQUE constraint berfungsi).
- Jumlah baris sesuai dengan rentang tanggal.
- Data lama (2024/2025) tersimpan dengan benar.

---

## 📋 Checklist Pengujian (Definition of Done)

- [x] `check_data_completeness()` menggunakan perhitungan hari kerja (*business days*), bukan *timedelta* sederhana.
- [x] Logika *cache-first* bekerja: jika data lengkap di DB, tidak melakukan fetch.
- [x] Logika *partial fetch* bekerja: jika data parsial, hanya fetch tanggal yang hilang.
- [x] Data baru disimpan ke database setelah fetch dari Yahoo Finance.
- [x] Tidak ada data duplikat di database (UNIQUE constraint berfungsi).
- [x] Test Case 1-5 berhasil dijalankan tanpa error.
- [x] Database `stock_data` berisi data yang valid untuk tahun 2024 dan/atau 2025.
- [x] Chart tetap digenerate dengan benar setelah data di-load dari database.

---

## ⚠️ Catatan Penting untuk Developer

1. **Jangan ubah logika chart** (`chart.py`) — fokus hanya pada *data layer* (controller, db, yahoo_service).
2. **Pastikan database path** sudah benar: `data/stock_data.db` (relative dari project root).
3. **Hapus database lama** sebelum pengujian pertama jika ingin memastikan clean slate:
   ```bash
   rm -f data/stock_data.db
   ```
4. **Perhatikan error handling** — jika Yahoo Finance sedang down, aplikasi harus tetap memberi pesan error yang jelas, bukan crash.
5. **UTC vs Local Time** — pastikan semua timestamp menggunakan UTC untuk konsistensi.
