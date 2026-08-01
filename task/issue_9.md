# Issue #9: Database Enhancement — Menambahkan Field `changes` (Persentase Perubahan Harian)

## 📌 Ringkasan Tugas
Dokumen perencanaan ini dibuat sebagai panduan langkah-demi-langkah (*step-by-step implementation guide*) untuk **Junior Programmer** atau **AI Model** dalam mengimplementasikan penambahan kolom baru pada database.

**Tujuan Utama:**
1. Menambahkan field `changes` pada tabel `stock_data` dan `stock_simulate_data`, ditempatkan di antara kolom `volume` dan `created_at`.
2. Mengisi field `changes` dengan nilai persentase perubahan harga (`%change`) berdasarkan harga penutupan (`close`) tanggal sebelumnya.
3. Melakukan pengujian pada rentang tanggal **14/07/2026 – 30/07/2026**.

---

## 🗂️ File yang Akan Dimodifikasi

| File | Perubahan |
| :--- | :--- |
| `src/service/db.py` | Tambah kolom `changes` di `init_db()` dan `init_simulate_table()`; update `save_stock_data()`, `save_simulate_data()`, `calculate_and_save_ihsp()`; opsional update `get_stock_data()` dan `get_simulate_data()` |

> **Catatan:** Tidak ada file baru yang perlu dibuat. Semua perubahan dilakukan pada file yang sudah ada.

---

## 📋 Spesifikasi & Aturan Detail

### 1. Posisi Kolom `changes` di Database

Kolom `changes` harus ditempatkan **setelah kolom `volume`** dan **sebelum kolom `created_at`** pada kedua tabel.

**Tabel `stock_data`** — urutan kolom setelah perubahan:

```sql
id, symbol, date, open, previous_close, high, low, close, volume,
changes,          -- ← KOLOM BARU (DECIMAL(10,4), DEFAULT NULL)
created_at, created_by, updated_at, updated_by
```

**Tabel `stock_simulate_data`** — urutan kolom setelah perubahan:

```sql
id, symbol, date, open, previous_close, high, low, close, volume,
changes,          -- ← KOLOM BARU (DECIMAL(10,4), DEFAULT NULL)
pct_change,
created_at, created_by, updated_at, updated_by
```

> **⚠️  Catatan Penting:** Tabel `stock_simulate_data` **sudah memiliki** kolom `pct_change` (ditambahkan pada Issue #8 untuk fitur IHSP). Kolom `changes` adalah kolom **baru yang terpisah** — kedua kolom akan *coexist*.

### 2. Tipe Data Kolom `changes`

| Parameter | Nilai |
| :--- | :--- |
| **Nama Kolom** | `changes` |
| **Tipe Data** | `DECIMAL(10,4)` |
| **Nullable** | `DEFAULT NULL` (boleh NULL) |
| **Posisi** | `AFTER volume` |

### 3. Logic Perhitungan `changes`

Rumus perhitungan perubahan persentase berdasarkan hari sebelumnya:

```
changes = ((close_today - close_yesterday) / close_yesterday) * 100
```

**Aturan:**

| Kondisi | Nilai `changes` |
| :--- | :--- |
| Data hari ini dan hari kemarin tersedia | `((close_today - close_yesterday) / close_yesterday) * 100` |
| Baris pertama (tidak ada data hari sebelumnya) | `NULL` |
| `close_yesterday` bernilai 0 | `NULL` (hindari division by zero) |

**Contoh Perhitungan:**

| Tanggal | Symbol | close | close_kemarin | changes |
| :--- | :--- | :--- | :--- | :--- |
| 2026-07-14 | BBCA.JK | 10.000 | — | `NULL` |
| 2026-07-15 | BBCA.JK | 10.250 | 10.000 | `((10250-10000)/10000)*100 = +2.5000%` |
| 2026-07-16 | BBCA.JK | 10.100 | 10.250 | `((10100-10250)/10250)*100 = -1.4634%` |

---

## 🛠️ Tahapan Implementasi (Step-by-Step Guide)

### Tahap 1: Tambah Kolom `changes` ke Tabel `stock_data`

**Lokasi:** Fungsi `init_db()` di `src/service/db.py`

**Langkah-langkah:**

1. Buka file `src/service/db.py`.
2. Cari fungsi `init_db()`.
3. Di dalam fungsi `init_db()`, **setelah** `CREATE TABLE IF NOT EXISTS` dan `conn.commit()`, tambahkan kode ALTER TABLE untuk menambah kolom `changes`:

```python
# Tambah kolom changes jika belum ada
try:
    cursor.execute("""
        ALTER TABLE stock_data
        ADD COLUMN changes DECIMAL(10,4) DEFAULT NULL
        AFTER volume
    """)
    conn.commit()
except Exception:
    pass  # Kolom sudah ada — skip
```

4. **Penjelasan:** Penggunaan `try-except` diperlukan karena jika tabel sudah pernah di-migrasi, kolom `changes` sudah ada dan ALTER TABLE akan gagal. Dengan `try-except`, error tersebut diabaikan.

---

### Tahap 2: Tambah Kolom `changes` ke Tabel `stock_simulate_data`

**Lokasi:** Fungsi `init_simulate_table()` di `src/service/db.py`

**Langkah-langkah:**

1. Masih di file `src/service/db.py`.
2. Cari fungsi `init_simulate_table()`.
3. Di dalam fungsi `init_simulate_table()`, **setelah** blok `try-except` untuk kolom `pct_change` (yang sudah ada), tambahkan blok serupa untuk kolom `changes`:

```python
# Tambah kolom changes jika belum ada
try:
    cursor.execute("""
        ALTER TABLE stock_simulate_data
        ADD COLUMN changes DECIMAL(10,4) DEFAULT NULL
        AFTER volume
    """)
    conn.commit()
except Exception:
    pass  # Kolom sudah ada — skip
```

4. **Penting:** Pastikan blok ini ditambahkan **setelah** blok `pct_change` agar urutan kolom sesuai: `volume → changes → pct_change → created_at`.

---

### Tahap 3: Update `save_stock_data()` — Hitung & Simpan `changes`

**Lokasi:** Fungsi `save_stock_data()` di `src/service/db.py`

**Langkah-langkah:**

1. Cari fungsi `save_stock_data()`.
2. Di dalam loop `for idx in range(len(df))`:
   - Ambil nilai `close` baris saat ini (`close_val`).
   - Ambil nilai `close` baris **sebelumnya** (`close_series[idx - 1]`) sebagai `close_yesterday`.
   - Hitung `changes`:
     ```python
     if idx > 0 and prev_close is not None and prev_close != 0 and close_val is not None:
         changes_val = ((close_val - prev_close) / prev_close) * 100
     else:
         changes_val = None
     ```
3. Update query **INSERT** — tambahkan `changes` ke daftar kolom dan VALUES:

   **Kolom INSERT bertambah menjadi:**
   ```sql
   INSERT INTO stock_data
       (symbol, date, open, previous_close, high, low, close, volume, changes,
        created_at, created_by, updated_at, updated_by)
   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
   ```

   **VALUES tuple bertambah menjadi:**
   ```python
   (ticker, date_str, open_val, prev_close,
    high_val, low_val, close_val, volume_val, changes_val,
    now, SYSTEM_USER, now, SYSTEM_USER)
   ```

4. Update query **ON DUPLICATE KEY UPDATE** — tambahkan baris untuk `changes`:
   ```sql
   ON DUPLICATE KEY UPDATE
       open = VALUES(open),
       previous_close = VALUES(previous_close),
       high = VALUES(high),
       low = VALUES(low),
       close = VALUES(close),
       volume = VALUES(volume),
       changes = VALUES(changes),
       updated_at = VALUES(updated_at),
       updated_by = VALUES(updated_by)
   ```

---

### Tahap 4: Update `save_simulate_data()` — Hitung & Simpan `changes`

**Lokasi:** Fungsi `save_simulate_data()` di `src/service/db.py`

**Langkah-langkah:**

1. Cari fungsi `save_simulate_data()`.
2. Tambahkan perhitungan `changes_val` di dalam loop (sama seperti Tahap 3), menggunakan `close_series` atau data dari DataFrame.
3. Update query **INSERT** untuk menyertakan kolom `changes`:

   ```sql
   INSERT INTO stock_simulate_data
       (symbol, date, open, previous_close, high, low, close, volume, changes, pct_change,
        created_at, created_by, updated_at, updated_by)
   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
   ```

4. Update query **ON DUPLICATE KEY UPDATE**:
   ```sql
   ON DUPLICATE KEY UPDATE
       open = VALUES(open),
       previous_close = VALUES(previous_close),
       high = VALUES(high),
       low = VALUES(low),
       close = VALUES(close),
       volume = VALUES(volume),
       changes = VALUES(changes),
       pct_change = VALUES(pct_change),
       updated_at = VALUES(updated_at),
       updated_by = VALUES(updated_by)
   ```

5. Update VALUES tuple untuk menyertakan `changes_val` dan `pct_change_val`.

---

### Tahap 5: Update `calculate_and_save_ihsp()` (Opsional tapi Disarankan)

**Lokasi:** Fungsi `calculate_and_save_ihsp()` di `src/service/db.py`

**Langkah-langkah:**

1. Fungsi ini sudah menghitung `pct_change` untuk IHSP (`^PEARL`).
2. Jika ingin konsisten, pastikan kolom `changes` juga terisi. Ada **2 opsi**:

   **Opsi A — Biarkan `save_simulate_data()` yang menghitung:**
   - Cukup pastikan DataFrame yang dikirim ke `save_simulate_data()` memiliki kolom `close` berurutan (sudah diurutkan berdasarkan `date`).
   - `save_simulate_data()` akan menghitung `changes` secara otomatis berdasarkan perbandingan `close` dengan baris sebelumnya.

   **Opsi B — Hitung manual di fungsi ini:**
   ```python
   ihsp_df['changes'] = ihsp_df['pct_change']  # Nilainya sama persis
   ```

   > **Rekomendasi:** Gunakan **Opsi A** karena lebih sederhana — `save_simulate_data()` sudah menangani perhitungan `changes` secara otomatis.

---

### Tahap 6: Update Fungsi `get_stock_data()` dan `get_simulate_data()` (Opsional)

**Lokasi:** Fungsi `get_stock_data()` dan `get_simulate_data()` di `src/service/db.py`

**Langkah-langkah:**

1. Jika data `changes` perlu diakses oleh consumer (misal untuk ditampilkan di chart atau diekspor), tambahkan kolom `changes` ke SELECT query.

   **`get_stock_data()`:**
   ```python
   query = """
       SELECT symbol, date, open, previous_close, high, low, close, volume, changes
       FROM stock_data
       WHERE symbol = %s AND date >= %s AND date <= %s
       ORDER BY date ASC
   """
   ```

   **`get_simulate_data()`:**
   ```python
   query = """
       SELECT symbol, date, open, previous_close, high, low, close, volume, changes, pct_change
       FROM stock_simulate_data
       WHERE symbol = %s AND date >= %s AND date <= %s
       ORDER BY date ASC
   """
   ```

---

### Tahap 7: Backfill Data Lama (Data Sebelum Migrasi)

**Tujuan:** Mengisi kolom `changes` untuk data yang **sudah ada** di database sebelum migrasi ini dilakukan.

**Langkah-langkah:**

1. Buat script SQL atau Python untuk backfill.

   **Cara 1 — Update via Python (Direkomendasikan):**
   ```python
   def backfill_changes():
       """Backfill changes column for existing data in both tables."""
       conn = _get_connection()
       cursor = conn.cursor()
       
       for table in ['stock_data', 'stock_simulate_data']:
           # Ambil semua simbol unik
           cursor.execute(f"SELECT DISTINCT symbol FROM {table}")
           symbols = [row[0] for row in cursor.fetchall()]
           
           for symbol in symbols:
               # Ambil data per simbol, urut berdasarkan date
               cursor.execute(f"""
                   SELECT id, close, previous_close
                   FROM {table}
                   WHERE symbol = %s
                   ORDER BY date ASC
               """, (symbol,))
               rows = cursor.fetchall()
               
               for i, (row_id, close_val, prev_close) in enumerate(rows):
                   if i > 0 and prev_close is not None and prev_close != 0 and close_val is not None:
                       changes = ((close_val - prev_close) / prev_close) * 100
                       cursor.execute(
                           f"UPDATE {table} SET changes = %s WHERE id = %s",
                           (round(changes, 4), row_id)
                       )
               print(f"  Backfill {table}/{symbol}: {len(rows)} rows processed")
       
       conn.commit()
       conn.close()
       print("Backfill completed!")
   ```

   **Cara 2 — Update via SQL (Lebih Cepat untuk Data Besar):**
   ```sql
   -- Contoh untuk satu simbol (tidak praktis untuk banyak simbol)
   -- Lebih baik gunakan Python approach di atas
   ```

2. Jalankan script backfill **setelah** Tahap 1-5 selesai dan aplikasi sudah berjalan.

---

### Tahap 8: Pengujian (Testing) — Rentang 14/07/2026 – 30/07/2026

**Tujuan:** Memvalidasi bahwa kolom `changes` terisi dengan benar.

**Langkah-langkah:**

1. **Jalankan aplikasi** dengan perintah:
   ```bash
   python src/main.py -t ^JKSE BBCA.JK BMRI.JK -d 14/07/2026 30/07/2026
   ```

2. **Verifikasi di database** — Query manual untuk memeriksa data:
   ```sql
   SELECT symbol, date, close, previous_close, changes
   FROM stock_data
   WHERE date >= '2026-07-14' AND date <= '2026-07-30'
     AND symbol IN ('^JKSE', 'BBCA.JK', 'BMRI.JK')
   ORDER BY symbol, date;
   ```

3. **Validasi perhitungan** — Pilih 2-3 baris data dan hitung manual:
   ```
   Contoh: BBCA.JK tanggal 15/07/2026
   close = 10.250, previous_close = 10.000
   changes = ((10.250 - 10.000) / 10.000) * 100 = +2.5000%
   ```

4. **Cek baris pertama** — Pastikan baris pertama setiap simbol memiliki `changes = NULL`:
   ```sql
   SELECT symbol, MIN(date) as first_date, changes
   FROM stock_data
   WHERE date >= '2026-07-14' AND date <= '2026-07-30'
   GROUP BY symbol;
   ```

5. **Cek data simulasi** (jika ada):
   ```sql
   SELECT symbol, date, close, changes, pct_change
   FROM stock_simulate_data
   WHERE date >= '2026-07-14' AND date <= '2026-07-30'
   ORDER BY symbol, date;
   ```

---

## 🔍 Ringkasan Perubahan Kode di `db.py`

| Fungsi | Perubahan |
| :--- | :--- |
| `init_db()` | Tambah blok `try-except` untuk ALTER TABLE `stock_data` ADD COLUMN `changes` AFTER `volume` |
| `init_simulate_table()` | Tambah blok `try-except` untuk ALTER TABLE `stock_simulate_data` ADD COLUMN `changes` AFTER `volume` |
| `save_stock_data()` | Hitung `changes_val` di loop; tambahkan ke INSERT, VALUES, dan ON DUPLICATE KEY UPDATE |
| `save_simulate_data()` | Hitung `changes_val` di loop; tambahkan ke INSERT, VALUES, dan ON DUPLICATE KEY UPDATE |
| `calculate_and_save_ihsp()` | (Opsional) Pastikan kolom `changes` terisi — cukup andalkan `save_simulate_data()` |
| `get_stock_data()` | (Opsional) Tambahkan `changes` ke SELECT query |
| `get_simulate_data()` | (Opsional) Tambahkan `changes` ke SELECT query |

---

## ✅ Checklist Pengujian (Definition of Done)

- [ ] Kolom `changes` dengan tipe `DECIMAL(10,4) DEFAULT NULL` berhasil ditambahkan ke tabel `stock_data` (posisi setelah `volume`).
- [ ] Kolom `changes` dengan tipe `DECIMAL(10,4) DEFAULT NULL` berhasil ditambahkan ke tabel `stock_simulate_data` (posisi setelah `volume`).
- [ ] Fungsi `save_stock_data()` menyimpan nilai `changes` dengan benar.
- [ ] Fungsi `save_simulate_data()` menyimpan nilai `changes` dengan benar.
- [ ] Baris pertama setiap simbol memiliki nilai `changes = NULL`.
- [ ] Data lama (sebelum migrasi) berhasil di-backfill.
- [ ] Pengujian dengan rentang **14/07/2026 – 30/07/2026** menunjukkan hasil perhitungan yang akurat.
- [ ] Tidak ada error saat migrasi di lingkungan produksi (ALTER TABLE idempotent dengan try-except).

---

## 📝 Contoh Pengujian Manual

```bash
# Step 1: Jalankan aplikasi dengan data baru
python src/main.py -t ^JKSE BBCA.JK BMRI.JK -d 14/07/2026 30/07/2026

# Step 2: Verifikasi via MySQL
mysql -u root -p -e "
USE stock_data;
SELECT symbol, date, close, previous_close, changes
FROM stock_data
WHERE symbol = 'BBCA.JK' AND date BETWEEN '2026-07-14' AND '2026-07-16'
ORDER BY date;
"
```

**Expected Output:**
```
+---------+------------+---------+----------------+----------+
| symbol  | date       | close   | previous_close | changes  |
+---------+------------+---------+----------------+----------+
| BBCA.JK | 2026-07-14 | 10000.0 | NULL           | NULL     |
| BBCA.JK | 2026-07-15 | 10250.0 | 10000.0        | 2.5000   |
| BBCA.JK | 2026-07-16 | 10100.0 | 10250.0        | -1.4634  |
+---------+------------+---------+----------------+----------+
```
