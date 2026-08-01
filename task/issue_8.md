# Issue #8: Fitur Baru — IHSP (Indeks Harga Saham Pearl) vs IHSG dengan Argument `-x`

## 📌 Ringkasan Tugas
Dokumen perencanaan ini dibuat sebagai panduan langkah-demi-langkah (*step-by-step implementation guide*) untuk **Junior Programmer** atau **AI Model** dalam mengimplementasikan fitur visualisasi **IHSP (Indeks Harga Saham Pearl) vs IHSG (IDX Composite / ^JKSE)**.

**Tujuan Utama:**
1. Menambahkan argument CLI `-x` (tanpa value) yang berfungsi sebagai pengganti `-t`.
2. Jika `-x` digunakan, maka **`-t` tidak boleh digunakan** (mutually exclusive).
3. `-x` mengambil **semua simbol** dari tabel `stock_data` **kecuali `^JKSE`**, menggabungkannya menjadi satu indeks gabungan per hari (**IHSP / `^PEARL`**).
4. Memvisualisasikan perbandingan **IHSP vs IHSG (^JKSE)** dalam bentuk:
   - **Static Chart (`.png`)** — Landscape 1920×1080
   - **Animation Chart (`.mp4`)** — Vertical 1080×1920
5. Menyimpan data IHSP ke tabel baru `stock_simulate_data` dengan simbol `^PEARL`.

**Contoh penggunaan:**
```bash
# Benar
python main.py -x -d 14/07/2026 30/07/2026

# Salah (karena -x dan -t tidak bisa bersama)
python main.py -x -t BMRI.JK 14/07/2026 30/07/2026
```

---

## 🗂️ File yang Akan Dimodifikasi / Dibuat

| File | Tindakan | Perubahan |
| :--- | :--- | :--- |
| `src/main.py` | **Modifikasi** | Tambah argumen `-x`, buat mutually exclusive dengan `-t` |
| `src/service/controller.py` | **Modifikasi** | Tambah logika pipeline untuk mode `-x` |
| `src/service/db.py` | **Modifikasi** | Tambah tabel `stock_simulate_data`, fungsi CRUD untuk `^PEARL` |
| `src/service/chart.py` | **Modifikasi** | Tambah fungsi visualisasi IHSP vs IHSG (2 line chart) |

---

## 📋 Spesifikasi & Aturan Detail

### 1. Argument `-x` di CLI

| Aturan | Deskripsi |
| :--- | :--- |
| **Nama flag** | `-x` / `--ihsp` (gunakan `store_true`) |
| **Type** | `store_true` (boolean flag, tanpa value) |
| **Mutually exclusive dengan** | `-t` / `--tickers` |
| **Kombinasi dengan argumen lain** | Tetap bisa dikombinasikan dengan `-d`, `-i`, `-p` seperti biasa |
| **Validasi** | Jika `-x` dan `-t` digunakan bersamaan → tampilkan error dan exit |

### 2. Konsep IHSP (Indeks Harga Saham Pearl)

IHSP adalah indeks gabungan dari seluruh saham yang terdaftar di tabel `stock_data` (kecuali `^JKSE`). Cara menghitungnya:

1. Ambil semua data dari tabel `stock_data` untuk **setiap simbol** selain `^JKSE` dalam rentang tanggal yang diminta.
2. Untuk setiap tanggal, jumlahkan **harga `close`** dari semua simbol yang memiliki data pada tanggal tersebut.
3. Hasil penjumlahan per tanggal inilah yang menjadi **nilai IHSP**.
4. Data IHSP disimpan ke tabel `stock_simulate_data` dengan simbol `^PEARL`.

> **Catatan:** Jika suatu simbol tidak memiliki data pada tanggal tertentu, abaikan (jangan dianggap 0, jangan diisi).

### 3. Tabel `stock_simulate_data`

Buat tabel baru di MySQL dengan struktur berikut:

```sql
CREATE TABLE IF NOT EXISTS stock_simulate_data (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    symbol          VARCHAR(50)  NOT NULL,
    date            DATE         NOT NULL,
    open            DECIMAL(20,4),
    previous_close  DECIMAL(20,4),
    high            DECIMAL(20,4),
    low             DECIMAL(20,4),
    close           DECIMAL(20,4),
    volume          DECIMAL(20,4),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by      VARCHAR(100) DEFAULT 'system',
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by      VARCHAR(100) DEFAULT 'system',
    UNIQUE(symbol, date)
);
```

> **Struktur tabel ini identik dengan `stock_data`.** Bedanya hanya di konten: tabel ini menyimpan **data simulasi/sintetis** (seperti IHSP), bukan data asli dari Yahoo Finance.

### 4. Visualisasi IHSP vs IHSG

Hanya **2 garis (line)** yang akan ditampilkan pada chart:

| Line | Simbol | Sumber Data |
| :--- | :--- | :--- |
| **IHSP (Indeks Harga Saham Pearl)** | `^PEARL` | `stock_simulate_data` (hasil gabungan seluruh simbol kecuali `^JKSE`) |
| **IHSG (IDX Composite)** | `^JKSE` | `stock_data` (data asli dari Yahoo Finance) |

Detail visualisasi:
- **Static (`.png`)** — Landscape `1920x1080`, menggunakan template chart yang sudah ada di `chart.py`
- **Animated (`.mp4`)** — Vertical `1080x1920`, menggunakan template animasi yang sudah ada di `chart.py`
- Kedua line menggunakan **normalisasi persentase** (percentage change dari harga pertama) agar perbandingan lebih fair
- Judul chart: `IHSP (Indeks Harga Saham Pearl) vs IHSG (IDX Composite)`

---

## 🛠️ Tahapan Implementasi (Step-by-Step Guide)

### Tahap 1: Modifikasi `src/main.py` — Tambah Argumen `-x`

#### 1a. Buat grup mutually exclusive antara `-t` dan `-x`

Di fungsi `build_parser()`:

1. Hapus `required=True` dari `parser.add_argument('-t', '--tickers', ...)` karena sekarang `-x` bisa menjadi alternatif.
2. Buat grup mutually exclusive baru untuk `-t` dan `-x`:

```python
# ── Tickers OR IHSP mode (mutually exclusive) ────────────────────
ticker_group = parser.add_mutually_exclusive_group(required=True)

ticker_group.add_argument(
    '-t', '--tickers',
    nargs='+',
    metavar='TICKER',
    help='One or more ticker symbols (e.g., BTC-USD BBCA.JK ^JKSE)',
)

ticker_group.add_argument(
    '-x', '--ihsp',
    action='store_true',
    help='Mode IHSP: visualisasi IHSP (^PEARL) vs IHSG (^JKSE) menggunakan seluruh data di database',
)
```

#### 1b. Ubah logika parsing di fungsi `main()`

Sekarang `args.tickers` bisa `None` (jika `-x` digunakan). Tambahkan penanganan:

```python
# Di dalam main(), setelah args = parser.parse_args()
# Tentukan mode IHSP
is_ihsp_mode = args.ihsp if hasattr(args, 'ihsp') else False

# Jika mode IHSP, tickers akan ditentukan oleh controller
if is_ihsp_mode:
    # panggil controller dengan tickers=None atau flag khusus
    controller.run(
        tickers=None,
        is_ihsp_mode=True,
        date_mode=date_mode,
        date_start=date_start,
        date_end=date_end,
        interval_days=interval_days,
        period=period,
    )
else:
    # panggil controller seperti biasa dengan tickers dari args
    controller.run(
        tickers=args.tickers,
        is_ihsp_mode=False,
        date_mode=date_mode,
        date_start=date_start,
        date_end=date_end,
        interval_days=interval_days,
        period=period,
    )
```

---

### Tahap 2: Modifikasi `src/service/db.py` — Tambah Tabel `stock_simulate_data` & Fungsi Baru

#### 2a. Buat tabel `stock_simulate_data` di `init_db()`

Di fungsi `init_db()`, tambahkan `CREATE TABLE IF NOT EXISTS` untuk `stock_simulate_data` setelah `stock_data`:

```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_simulate_data (
        id              INT PRIMARY KEY AUTO_INCREMENT,
        symbol          VARCHAR(50)  NOT NULL,
        date            DATE         NOT NULL,
        open            DECIMAL(20,4),
        previous_close  DECIMAL(20,4),
        high            DECIMAL(20,4),
        low             DECIMAL(20,4),
        close           DECIMAL(20,4),
        volume          DECIMAL(20,4),
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by      VARCHAR(100) DEFAULT 'system',
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        updated_by      VARCHAR(100) DEFAULT 'system',
        UNIQUE(symbol, date)
    )
""")
```

#### 2b. Buat fungsi `get_all_symbols_except_jkse()`

Fungsi untuk mengambil daftar semua simbol unik dari `stock_data` kecuali `^JKSE`:

```python
def get_all_symbols_except_jkse() -> List[str]:
    """
    Ambil semua simbol unik dari tabel stock_data, kecuali '^JKSE'.

    Returns:
        List of ticker symbols (strings)
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT symbol FROM stock_data WHERE symbol != '^JKSE' ORDER BY symbol"
    )
    symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    return symbols
```

#### 2c. Buat fungsi `get_all_stock_data_except_jkse()`

Fungsi untuk mengambil semua data `close` per tanggal dari semua simbol kecuali `^JKSE`:

```python
def get_all_stock_data_except_jkse(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Ambil data close price dari semua simbol kecuali ^JKSE dalam rentang tanggal.

    Returns:
        DataFrame dengan kolom: symbol, date, close (diurutkan berdasarkan date, symbol)
    """
    conn = _get_connection()
    query = """
        SELECT symbol, date, close
        FROM stock_data
        WHERE symbol != '^JKSE'
          AND date >= %s AND date <= %s
        ORDER BY date ASC, symbol ASC
    """
    df = pd.read_sql_query(query, conn, params=(start_date, end_date))
    conn.close()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])

    return df
```

#### 2d. Buat fungsi untuk menghitung dan menyimpan IHSP

Fungsi ini akan:
1. Ambil semua data dari `get_all_stock_data_except_jkse()`
2. Group by date, jumlahkan `close` per tanggal
3. Simpan hasilnya ke `stock_simulate_data` dengan simbol `^PEARL`

```python
def calculate_and_save_ihsp(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Hitung IHSP dengan menjumlahkan close price seluruh simbol (kecuali ^JKSE)
    per tanggal, lalu simpan ke tabel stock_simulate_data.

    Args:
        start_date: Start date 'YYYY-MM-DD'
        end_date:   End date 'YYYY-MM-DD'

    Returns:
        DataFrame dengan kolom: date, close (hasil IHSP)
    """
    # Ambil semua data
    df = get_all_stock_data_except_jkse(start_date, end_date)

    if df.empty:
        print("  WARNING: Tidak ada data untuk menghitung IHSP")
        return pd.DataFrame()

    # Group by date, sum close price
    ihsp_df = df.groupby('date', as_index=False)['close'].sum()
    ihsp_df = ihsp_df.rename(columns={'close': 'close'})
    ihsp_df = ihsp_df.sort_values('date')

    # Simpan ke stock_simulate_data
    save_simulate_data(ihsp_df, '^PEARL')

    print(f"  IHSP (^PEARL) calculated and saved: {len(ihsp_df)} rows")
    return ihsp_df
```

#### 2e. Buat fungsi `save_simulate_data()` dan `get_simulate_data()`

Fungsi untuk menyimpan dan membaca data dari `stock_simulate_data`:

```python
def save_simulate_data(df: pd.DataFrame, symbol: str) -> int:
    """
    Simpan data simulasi ke tabel stock_simulate_data (upsert).

    Args:
        df: DataFrame dengan kolom minimal 'date' dan 'close'
        symbol: Simbol custom (misal '^PEARL')

    Returns:
        Jumlah baris yang tersimpan
    """
    if df.empty:
        return 0

    conn = _get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    rows_affected = 0

    for idx in range(len(df)):
        row = df.iloc[idx]

        date_val = row['date']
        if hasattr(date_val, 'strftime'):
            date_str = date_val.strftime('%Y-%m-%d')
        else:
            date_str = str(pd.to_datetime(date_val).strftime('%Y-%m-%d'))

        close_val = float(row['close']) if pd.notna(row['close']) else None

        try:
            cursor.execute("""
                INSERT INTO stock_simulate_data
                    (symbol, date, close, created_at, created_by, updated_at, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    close = VALUES(close),
                    updated_at = VALUES(updated_at),
                    updated_by = VALUES(updated_by)
            """, (
                symbol, date_str, close_val,
                now, 'system', now, 'system',
            ))
            rows_affected += 1
        except Exception as e:
            print(f"  Error saving simulate data for {symbol} on {date_str}: {e}")

    conn.commit()
    conn.close()

    if rows_affected > 0:
        print(f"  Saved {rows_affected} rows for {symbol} in stock_simulate_data")
    return rows_affected


def get_simulate_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Ambil data simulasi dari stock_simulate_data.

    Args:
        symbol: Simbol custom (misal '^PEARL')
        start_date: Start date 'YYYY-MM-DD'
        end_date:   End date 'YYYY-MM-DD'

    Returns:
        DataFrame dengan kolom: symbol, date, close
    """
    conn = _get_connection()
    query = """
        SELECT symbol, date, open, high, low, close, volume
        FROM stock_simulate_data
        WHERE symbol = %s AND date >= %s AND date <= %s
        ORDER BY date ASC
    """
    df = pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))
    conn.close()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])

    return df
```

#### 2f. Perbarui `inspect_table()` (Opsional)

Jika fungsi `inspect_table()` ada, tambahkan informasi tentang tabel `stock_simulate_data`.

---

### Tahap 3: Modifikasi `src/service/controller.py` — Pipeline Mode IHSP

#### 3a. Tambahkan parameter `is_ihsp_mode` ke fungsi `run()`

Ubah signature fungsi `run()`:

```python
def run(
    tickers: List[str] = None,
    is_ihsp_mode: bool = False,
    date_mode: str = None,
    date_start: str = None,
    date_end: str = None,
    interval_days: int = None,
    period: str = None,
) -> None:
```

#### 3b. Tambahkan cabang logika untuk mode IHSP

Di dalam `run()`, setelah Step 1 (resolve dates), tambahkan:

```python
# ── Mode IHSP (khusus) ──────────────────────────────────────────────
if is_ihsp_mode:
    print("\n-- IHSP Mode: IHSP (^PEARL) vs IHSG (^JKSE) --")

    # Step 2: Init DB
    print("\n-- Initialising database --")
    db.init_db()

    # Step 3: Hitung/simpan IHSP
    print("\n-- Calculating IHSP from all symbols (except ^JKSE) --")
    ihsp_df = db.calculate_and_save_ihsp(start_date, end_date)

    if ihsp_df.empty:
        print("\nERROR: Gagal menghitung IHSP. Pastikan data stock_data tersedia. Exiting.")
        return

    # Step 4: Ambil data IHSG (^JKSE) dari stock_data
    print("\n-- Loading IHSG (^JKSE) data --")
    jkse_df = db.get_stock_data('^JKSE', start_date, end_date)

    if jkse_df.empty():
        print("\nERROR: Tidak ada data IHSG (^JKSE) di database. Exiting.")
        return

    # Step 5: Siapkan data untuk chart
    print("\n-- Preparing data for IHSP vs IHSG chart --")
    
    # Rename columns for chart compatibility
    ihsp_chart = ihsp_df.copy()
    ihsp_chart = ihsp_chart.rename(columns={'date': 'Date', 'close': 'Close_IDR'})
    
    jkse_chart = jkse_df.copy()
    if 'date' in jkse_chart.columns and 'Date' not in jkse_chart.columns:
        jkse_chart = jkse_chart.rename(columns={'date': 'Date'})
    if 'close' in jkse_chart.columns and 'Close_IDR' not in jkse_chart.columns:
        jkse_chart = jkse_chart.rename(columns={'close': 'Close_IDR'})

    chart_data = {
        '^PEARL': ihsp_chart,
        '^JKSE': jkse_chart,
    }

    # Step 6: Generate output
    output_dir = os.path.join(...)  # (sama seperti pipeline normal)
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    png_path = os.path.join(output_dir, f"chart_ihsp_vs_ihsg_{timestamp}.png")
    mp4_path = os.path.join(output_dir, f"chart_ihsp_vs_ihsg_{timestamp}.mp4")

    # 6a. Static PNG
    print("\n-- Generating IHSP vs IHSG static PNG chart --")
    try:
        chart.generate_png_chart(chart_data, png_path)
    except Exception as e:
        print(f"  ERROR generating PNG: {e}")

    # 6b. Animated MP4
    print("\n-- Generating IHSP vs IHSG animated MP4 chart --")
    try:
        chart.generate_mp4_animation(chart_data, mp4_path)
    except Exception as e:
        print(f"  ERROR generating MP4: {e}")

    print("\n" + "=" * 60)
    print("  IHSP vs IHSG — Done!")
    print("=" * 60)
    return
```

> **PENTING:** Pastikan logika mode IHSP ini **dieksekusi sebelum** pipeline normal. Jika `is_ihsp_mode=True`, fungsi `run()` harus langsung return setelah selesai memproses mode IHSP, tanpa menjalankan pipeline normal.

---

### Tahap 4: Modifikasi `src/service/chart.py` — Penyesuaian Visualisasi untuk IHSP

#### 4a. Pastikan chart bisa menangani 2 ticker dengan baik

Fungsi `create_static_chart()` dan `generate_png_chart()` yang sudah ada sudah mendukung multi-ticker. Mode IHSP hanya mengirimkan 2 ticker (`^PEARL` dan `^JKSE`), jadi tidak perlu perubahan besar.

Namun, pastikan:

1. **Warna garis konsisten:**
   - `^PEARL` (IHSP) → Gunakan warna biru (`#3b82f6`)
   - `^JKSE` (IHSG) → Gunakan warna merah (`#ef4444`)

2. **Judul chart khusus untuk IHSP vs IHSG:**
   Baris 1: `IHSP (^PEARL) vs IHSG (^JKSE)`
   Baris 2: Rentang tanggal
   Baris 3: Mana yang leading

3. Jika ingin membuat fungsi khusus untuk mode IHSP, buat fungsi baru:

```python
def generate_ihsp_comparison_chart(
    ihsp_df: pd.DataFrame,
    jkse_df: pd.DataFrame,
    output_png: str,
    output_mp4: str,
) -> None:
    """
    Generate IHSP vs IHSG comparison chart (static PNG + animated MP4).

    Args:
        ihsp_df: DataFrame IHSP (^PEARL) dengan kolom 'Date' dan 'Close_IDR'
        jkse_df: DataFrame IHSG (^JKSE) dengan kolom 'Date' dan 'Close_IDR'
        output_png: Path output untuk PNG
        output_mp4: Path output untuk MP4
    """
    chart_data = {
        '^PEARL': ihsp_df,
        '^JKSE': jkse_df,
    }

    # Custom title
    ticker_label = "IHSP (^PEARL) vs IHSG (^JKSE)"

    # Generate PNG
    create_static_chart(chart_data, output_png, title_lines=[
        ticker_label,
        f"{ihsp_df['Date'].iloc[0].strftime('%d %b %Y')} - {ihsp_df['Date'].iloc[-1].strftime('%d %b %Y')}",
        None,  # Auto-calculate best performer
    ])

    # Generate MP4 (gunakan fungsi yang sudah ada)
    create_animated_chart(chart_data, output_mp4)
```

> **Catatan:** Fungsi `create_static_chart()` sudah menerima parameter opsional `title_lines`. Jika tidak ada custom title, fungsi akan membuat title otomatis.

---

### Tahap 5: Testing

Setelah implementasi selesai, lakukan pengujian dengan langkah berikut:

#### 5a. Persiapan Data

Pastikan tabel `stock_data` sudah berisi data untuk periode pengujian. Jika belum, fetch dulu menggunakan mode normal:

```bash
# Fetch data untuk semua simbol (contoh)
python main.py -t ^JKSE BBCA.JK BBRI.JK BMRI.JK -d 14/07/2026 21/07/2026
```

#### 5b. Uji Coba Mode IHSP

```bash
# Test 1: Mode IHSP dengan date range
python main.py -x -d 14/07/2026 21/07/2026
```

**Yang divalidasi:**
1. ✅ Program berjalan tanpa error
2. ✅ Data IHSP (`^PEARL`) berhasil dihitung dan disimpan ke `stock_simulate_data`
3. ✅ File `.png` dan `.mp4` tergenerate di folder `output/`
4. ✅ Chart menampilkan 2 garis: IHSP (`^PEARL`) dan IHSG (`^JKSE`)
5. ✅ Judul chart menampilkan "IHSP (^PEARL) vs IHSG (^JKSE)"

#### 5c. Uji Kombinasi dengan Mode Lain

```bash
# Test 2: Mode IHSP dengan interval
python main.py -x -i 7

# Test 3: Mode IHSP dengan period
python main.py -x -p 1mo
```

#### 5d. Uji Validasi Error

```bash
# Test 4: -x dan -t bersama → harus error
python main.py -x -t BBCA.JK -d 14/07/2026 21/07/2026
# Expected: argparse error karena mutually exclusive
```

#### 5e. Verifikasi Data di Database

Jalankan query berikut di MySQL untuk memverifikasi data IHSP:

```sql
SELECT * FROM stock_simulate_data WHERE symbol = '^PEARL' ORDER BY date;
```

Pastikan:
- Ada data per tanggal (14/07/2026 - 21/07/2026)
- Nilai `close` adalah penjumlahan dari `close` semua simbol (kecuali `^JKSE`) pada tanggal yang sama

---

## ⚠️ Hal-Hal yang Perlu Diperhatikan

1. **Mutually Exclusive:** Argumen `-x` dan `-t` harus **saling eksklusif**. Gunakan `add_mutually_exclusive_group()` dari argparse. Jangan lupa set `required=True` pada grup tersebut.

2. **Data kosong:** Jika data di `stock_data` kosong untuk rentang yang diminta, program harus menampilkan pesan error yang jelas dan berhenti (bukan crash).

3. **IHSG (^JKSE) wajib ada:** Mode IHSP sangat bergantung pada data `^JKSE` sebagai pembanding. Jika tidak ada data `^JKSE`, tampilkan error.

4. **Performa:** Jika ada banyak simbol di `stock_data`, proses grouping dan sum bisa lambat. Ini tidak masalah untuk tahap awal.

5. **IDR Conversion:** Data dari `stock_data` (saham .JK) sudah dalam IDR. `^JKSE` juga sudah dalam IDR. Jadi **tidak perlu** konversi IDR untuk mode IHSP.

6. **Normalisasi Chart:** Kedua line (IHSP dan IHSG) harus dinormalisasi ke persentase perubahan dari harga pertama agar perbandingan visualnya fair.

7. **Nama file output:** Gunakan prefix `chart_ihsp_vs_ihsg_` untuk membedakan output mode IHSP dengan mode normal.

---

## ✅ Checklist Implementasi

| No | Checklist | Status |
| :--- | :--- | :--- |
| 1 | Tambah argumen `-x` di `main.py` (mutually exclusive dengan `-t`) | ☐ |
| 2 | Hapus `required=True` dari argumen `-t` lama | ☐ |
| 3 | Kirim parameter `is_ihsp_mode` ke `controller.run()` | ☐ |
| 4 | Tambah tabel `stock_simulate_data` di `db.py` | ☐ |
| 5 | Buat fungsi `get_all_symbols_except_jkse()` di `db.py` | ☐ |
| 6 | Buat fungsi `get_all_stock_data_except_jkse()` di `db.py` | ☐ |
| 7 | Buat fungsi `calculate_and_save_ihsp()` di `db.py` | ☐ |
| 8 | Buat fungsi `save_simulate_data()` di `db.py` | ☐ |
| 9 | Buat fungsi `get_simulate_data()` di `db.py` | ☐ |
| 10 | Tambah pipeline mode IHSP di `controller.py` | ☐ |
| 11 | Pastikan chart bisa menampilkan judul khusus IHSP vs IHSG | ☐ |
| 12 | Uji coba: `-x -d 14/07/2026 21/07/2026` | ☐ |
| 13 | Uji coba: `-x -i 7` | ☐ |
| 14 | Uji coba: `-x -p 1mo` | ☐ |
| 15 | Uji coba: `-x -t BBCA.JK` → harus error | ☐ |
| 16 | Verifikasi data `^PEARL` di database | ☐ |
