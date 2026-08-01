# Issue #7: Migrasi DBMS — SQLite ke MySQL

## 📌 Ringkasan Tugas
Dokumen perencanaan ini dibuat sebagai panduan langkah-demi-langkah (*step-by-step implementation guide*) untuk **Junior Programmer** atau **AI Model** dalam mengimplementasikan migrasi database dari **SQLite** ke **MySQL**.

**Tujuan Utama:**
1. Mengubah DBMS dari SQLite menjadi MySQL.
2. Koneksi ke MySQL dengan user `root`, password `root`, database `stock_data`.
3. Tidak ada perubahan struktur tabel — kolom, tipe data, constraint, dan index tetap sama persis seperti yang sudah ada.

---

## 🗂️ File yang Akan Dimodifikasi

| File | Perubahan |
| :--- | :--- |
| `requirements.txt` | Tambahkan dependensi MySQL (`mysql-connector-python`) |
| `src/service/db.py` | Ubah semua fungsi dari SQLite `sqlite3` ke MySQL `mysql.connector` |

> **Catatan:** Tidak ada file baru yang perlu dibuat. Semua perubahan dilakukan pada file yang sudah ada.

---

## 📋 Spesifikasi & Aturan

### 1. Kredensial MySQL
| Parameter | Nilai |
| :--- | :--- |
| **Host** | `localhost` (default) |
| **User** | `root` |
| **Password** | `root` |
| **Database** | `stock_data` |

### 2. Struktur Tabel (Tidak Berubah)
Tabel `stock_data` sudah ada di MySQL. Kolom, tipe data, constraint (PRIMARY KEY, UNIQUE, NOT NULL), dan index tetap sama persis seperti saat ini di SQLite:

```sql
CREATE TABLE stock_data (
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
    created_by      VARCHAR(100) DEFAULT 'yahoo_api',
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by      VARCHAR(100) DEFAULT 'yahoo_api',
    UNIQUE(symbol, date)
);
```

> **PENTING:** Tabel `stock_data` sudah tersedia di MySQL. **Jangan** menjalankan `CREATE TABLE` atau `ALTER TABLE` — hanya gunakan `CREATE TABLE IF NOT EXISTS` untuk jaga-jaga di fungsi `init_db()`.

---

## 🛠️ Tahapan Implementasi (Step-by-Step Guide)

### Tahap 1: Install Package MySQL Python Driver

1. Buka file `requirements.txt` di root project.
2. Tambahkan baris berikut:

```
mysql-connector-python>=8.0.0
```

3. Jalankan perintah installasi:

```bash
pip install -r requirements.txt
```

Atau install langsung:

```bash
pip install mysql-connector-python
```

---

### Tahap 2: Ubah Konfigurasi Koneksi Database di `db.py`

Buka file `src/service/db.py`. Lakukan perubahan sebagai berikut:

#### 2a. Hapus Import & Konstanta SQLite Lama

1. Hapus baris `import sqlite3`.
2. Hapus variabel `DB_DIR` dan `DB_PATH` karena MySQL tidak menggunakan file path.
3. Tambahkan `import mysql.connector` di bagian atas file.

#### 2b. Ganti Fungsi `_get_connection()`

Ubah dari koneksi SQLite (file-based) menjadi koneksi MySQL (TCP/IP):

```python
def _get_connection() -> mysql.connector.MySQLConnection:
    """Get a connection to the MySQL database."""
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='stock_data',
    )
    return conn
```

> **Tips:** Untuk debugging, tambahkan `print(f"Connected to MySQL: stock_data")` setelah koneksi berhasil.

#### 2c. Ubah Fungsi `init_db()`

SQLite menggunakan `INTEGER PRIMARY KEY AUTOINCREMENT` sedangkan MySQL menggunakan `INT AUTO_INCREMENT`.
SQLite menggunakan `TEXT` untuk string, MySQL menggunakan `VARCHAR`.
SQLite menggunakan `REAL` untuk float, MySQL menggunakan `DECIMAL(20,4)`.
SQLite menggunakan `DATE` → tetap `DATE` di MySQL.
SQLite menggunakan `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` → MySQL menggunakan `DATETIME DEFAULT CURRENT_TIMESTAMP`.

Ganti statement `CREATE TABLE` di `init_db()` dengan versi MySQL:

```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_data (
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
        created_by      VARCHAR(100) DEFAULT 'yahoo_api',
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        updated_by      VARCHAR(100) DEFAULT 'yahoo_api',
        UNIQUE(symbol, date)
    )
""")
```

Ubah juga statement `CREATE INDEX`:

```python
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_stock_data_symbol_date
    ON stock_data(symbol, date)
""")
```

#### 2d. Ubah Fungsi `inspect_table()`

MySQL menggunakan `DESCRIBE stock_data` atau `SHOW COLUMNS FROM stock_data` sebagai pengganti `PRAGMA table_info(stock_data)`:

```python
cursor.execute("DESCRIBE stock_data")
columns = cursor.fetchall()
```

Atau jika ingin konsisten:

```python
cursor.execute("SHOW COLUMNS FROM stock_data")
columns = cursor.fetchall()
```

Sesuaikan format print-nya karena struktur hasil query `SHOW COLUMNS` berbeda dengan `PRAGMA table_info`.

#### 2e. Ubah Fungsi `get_stock_data()`

Tidak ada perubahan signifikan selain dari koneksi. Query `SELECT` tetap sama:

```python
query = """
    SELECT symbol, date, open, previous_close, high, low, close, volume
    FROM stock_data
    WHERE symbol = %s AND date >= %s AND date <= %s
    ORDER BY date ASC
"""
df = pd.read_sql_query(query, conn, params=(ticker, start_date, end_date))
```

> **PENTING:** MySQL menggunakan `%s` sebagai placeholder parameter, **bukan** `?` seperti SQLite. Pastikan semua placeholder diubah.

#### 2f. Ubah Fungsi `check_data_completeness()`

Tidak ada perubahan signifikan — fungsi ini hanya membaca data. Pastikan query SELECT di dalamnya sudah menggunakan placeholder `%s`.

#### 2g. Ubah Fungsi `save_stock_data()`

Ini adalah fungsi yang paling banyak berubah karena perbedaan sintaks UPSERT.

**SQLite** menggunakan:
```sql
SELECT id FROM stock_data WHERE symbol = ? AND date = ?
... lalu UPDATE atau INSERT ...
```

**MySQL** dapat menggunakan `INSERT ... ON DUPLICATE KEY UPDATE` yang lebih efisien:

```python
cursor.execute("""
    INSERT INTO stock_data
        (symbol, date, open, previous_close, high, low, close, volume,
         created_at, created_by, updated_at, updated_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        open = VALUES(open),
        previous_close = VALUES(previous_close),
        high = VALUES(high),
        low = VALUES(low),
        close = VALUES(close),
        volume = VALUES(volume),
        updated_at = VALUES(updated_at),
        updated_by = VALUES(updated_by)
""", (
    ticker, date_str, open_val, prev_close,
    high_val, low_val, close_val, volume_val,
    now, SYSTEM_USER, now, SYSTEM_USER,
))
```

> **Keuntungan:** Dengan `ON DUPLICATE KEY UPDATE`, kita tidak perlu melakukan SELECT terlebih dahulu — cukup satu query INSERT yang otomatis menjadi UPDATE jika record sudah ada. Ini lebih cepat dan lebih sederhana.

#### 2h. Ubah Fungsi `get_distinct_dates()` dan `find_missing_date_ranges()`

Tidak ada perubahan signifikan selain placeholder `?` → `%s`.

---

### Tahap 3: Validasi & Testing

Setelah semua perubahan selesai, lakukan pengujian berikut:

#### 3a. Cek Koneksi Database
Jalankan script Python sederhana untuk memastikan koneksi MySQL berhasil:

```bash
python -c "from service.db import _get_connection; conn = _get_connection(); print('Connected!'); conn.close()"
```

#### 3b. Cek Inisialisasi Database
Jalankan fungsi `init_db()` dan `inspect_table()`:

```bash
python -c "from service.db import init_db, inspect_table; init_db(); inspect_table()"
```

Pastikan output menampilkan struktur tabel `stock_data` dengan benar.

#### 3c. Coba Jalankan Pipeline Utama
Jalankan aplikasi dengan ticker dan rentang tanggal sederhana:

```bash
python src/main.py -t BTC-USD -i 5
```

Perhatikan output untuk memastikan:
- Koneksi MySQL berhasil
- Data berhasil disimpan ke MySQL
- Data berhasil dibaca kembali dari MySQL
- Chart tetap tergenerate dengan benar

#### 3d. Verifikasi Data di MySQL
Gunakan MySQL command-line client untuk memverifikasi data:

```bash
mysql -u root -p
```

```sql
USE stock_data;
SELECT COUNT(*) FROM stock_data;
SELECT symbol, MIN(date), MAX(date) FROM stock_data GROUP BY symbol;
```

---

## ⚠️ Potensi Masalah & Troubleshooting

### 1. MySQL Service Tidak Berjalan
**Gejala:** `mysql.connector.errors.DatabaseError: 2003: Can't connect to MySQL server on 'localhost'`
**Solusi:** Pastikan MySQL server sudah dijalankan:
- **Windows:** `net start MySQL80` atau buka `Services.msc` → cari `MySQL80` → Start.
- **Linux/Mac:** `sudo systemctl start mysql` atau `sudo service mysql start`.

### 2. Database `stock_data` Belum Dibuat
**Gejala:** `mysql.connector.errors.DatabaseError: 1049: Unknown database 'stock_data'`
**Solusi:** Buat database terlebih dahulu:
```sql
CREATE DATABASE stock_data;
```

### 3. Tabel `stock_data` Belum Ada
**Gejala:** Error saat query INSERT/SELECT.
**Solusi:** Jalankan fungsi `init_db()` yang akan membuat tabel secara otomatis (sudah ada di pipeline).

### 4. Perbedaan Tipe Data
Jika ada error tipe data (misal: `DataError: Truncated incorrect DECIMAL value`), periksa apakah data yang dikirim sesuai dengan tipe kolom. Fungsi `save_stock_data` sudah mengkonversi nilai ke `float()` — pastikan tidak ada `NaN` yang dikirim ke MySQL (ganti dengan `None`).

### 5. Perbedaan Placeholder (`?` vs `%s`)
Ini adalah **kesalahan paling umum**. Pastikan **SEMUA** query parameterized di `db.py` menggunakan `%s`, bukan `?`.

---

## ✅ Checklist Pengujian (Definition of Done)

- [ ] `mysql-connector-python` terinstal (tertulis di `requirements.txt`).
- [ ] Semua `import sqlite3` dihapus, diganti `import mysql.connector`.
- [ ] Konstanta `DB_DIR` dan `DB_PATH` dihapus atau dinonaktifkan.
- [ ] Fungsi `_get_connection()` menggunakan `mysql.connector.connect(...)`.
- [ ] Semua placeholder query `?` sudah diganti menjadi `%s`.
- [ ] Fungsi `save_stock_data()` menggunakan `ON DUPLICATE KEY UPDATE` (atau logika upsert yang setara).
- [ ] Fungsi `inspect_table()` menggunakan `DESCRIBE` / `SHOW COLUMNS`.
- [ ] Aplikasi dapat berjalan dari awal sampai akhir tanpa error koneksi database.
- [ ] Data tersimpan dan terbaca kembali dari MySQL dengan benar.
- [ ] Output chart (PNG & MP4) tetap sesuai ekspektasi.
