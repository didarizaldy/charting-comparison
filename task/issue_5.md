# Issue #5: Chart Animation (.mp4) Visualization Enhancement & Date Range Bug Fix

## 📌 Context & Goal
Dokumen perencanaan ini dibuat sebagai panduan teknis (*task breakdown*) untuk implementasi oleh **Junior Programmer** atau **AI Code Assistant**. Goal utama dari issue ini adalah memperbaiki beberapa bug visualisasi pada chart animasi `.mp4` serta memastikan kelengkapan rentang tanggal data yang diambil.

---

## 🎯 Ringkasan Kebutuhan & Output
- **Target File**: Modul visualisasi (misal: `src/visualization/`, `src/utils/`, `src/main.py`, `src/data_loader.py`).
- **Output**: Visualisasi `.mp4` yang ditingkatkan (enhanced) dan perbaikan data tanggal terakhir (*fixing*).
- **Status Response**: `fixing and enhance`

---

## 📋 Daftar Perubahan & Spesifikasi Teknis

### 1. Stripping Akhiran `.JK` Pada Visualisasi Chart
* **Masalah**: Ticker saham Indonesia menggunakan akhiran `.JK` (contoh: `TLKM.JK`, `BMRI.JK`). Karakter `.JK` ini memenuhi tampilan chart dan visual kurang bersih.
* **Solusi**:
  * Buat helper function untuk pembersihan nama ticker (misal `clean_ticker_name(ticker_str)`).
  * Hapus kemunculan string `.JK` HANYA pada label tampilan teks di chart animasi (legend, watermark, header text, line label).
  * **Catatan**: Jangan ubah nama ticker asli di proses data/fetching agar pemanggilan API (seperti `yfinance`) tetap valid.

```python
# Contoh Helper Function
def clean_ticker_symbol(ticker: str) -> str:
    return ticker.replace('.JK', '')
```

---

### 2. Tampilkan Kembali Seluruh Line/Bar Ticker Pada Canvas Chart
* **Masalah**: Pada iterasi sebelumnya, ada regresi di mana chart hanya menampilkan sebagian ticker.
* **Solusi**:
  * Kembalikan logika plotting agar **semua ticker** yang diinputkan pengguna pada command line tetap dirender garis/grafiknya di atas canvas chart dari awal sampai akhir animasi.

---

### 3. Teks Dynamic Top 3 Leading Tickers di Bagian Atas
* **Masalah**: Header/teks atas chart terlalu ramai jika meng-list semua ticker ketika input > 3 ticker.
* **Solusi**:
  * **PENTING**: Hanya ringkasan teks di bagian atas (header text) yang dibatasi maksimal 3 ticker utama. **BUKAN** menghilangkan garis/bar grafik ticker lainnya dari chart canvas!
  * **Logika Per Frame (Animation Loop)**:
    1. Hitung performa/return relatif dari seluruh ticker pada frame/tanggal tersebut.
    2. Urutkan ticker dari return tertinggi ke terendah.
    3. Jika jumlah ticker > 3, ambil **Top 3** teratas. Jika jumlah ticker <= 3, tampilkan semuanya.
    4. Format string header secara dinamis mengikuti urutan pergerakan di frame tersebut.

```python
# Pseudo-code dalam animation loop per frame (frame_idx)
current_returns = returns_df.iloc[frame_idx].sort_values(ascending=False)

if len(current_returns) > 3:
    top_leading = current_returns.head(3)
else:
    top_leading = current_returns

# Format teks header dengan ticker name yang sudah di-clean
top_text_items = [f"{clean_ticker_symbol(tk)}: {val:+.2f}%" for tk, val in top_leading.items()]
header_str = " | ".join(top_text_items)
```

---

### 4. Perbaikan Format Tanda Plus/Minus (`+`) Pada Top Leading Profit
* **Masalah**: Ketika nilai return/profit bernilai negatif (minus), format penulisan terkadang menghasilkan karakter ganda seperti `+-1.25%` atau `+ -1.25%`.
* **Solusi**:
  * Perbaiki string formatting. Tanda `+` hanya dimunculkan jika nilai return > 0.
  * Jika nilai return <= 0, biarkan tanda minus `-` bawaan dari angka negatif yang bekerja tanpa menambahkan tanda `+` di depannya.

```python
# Formatting yang benar
def format_profit_percentage(value: float) -> str:
    if value > 0:
        return f"+{value:.2f}%"
    else:
        # Nilai nol atau negatif sudah otomatis menyertakan tanda '-' jika < 0
        return f"{value:.2f}%"
```

---

### 5. Fix Tanggal Terakhir Data (*Inclusive End Date Issue*)
* **Masalah**:
  Pengujian dengan perintah:
  `python src/main.py -t TPIA.JK ^JKSE BRPT.JK BUVA.JK TLKM.JK BMRI.JK BUMI.JK BULL.JK -d 14/07/2026 28/07/2026`
  Menghasilkan chart yang berhenti di tanggal **27/07/2026**, padahal batas `-d` adalah **28/07/2026**.
* **Akar Masalah (Root Cause Analysis)**:
  * Penggunaan library `yfinance` atau filter pandas `df[start:end]` bersifat *exclusive* pada parameter `end` jika format date berupa string, atau perbandingan jam `2026-07-28 00:00:00` membuat data di hari tersebut terpotong.
* **Solusi**:
  1. Pada modul *data loader / fetcher*, tambahkan 1 hari pada `end_date` saat memanggil data provider/API:
     `fetch_end_date = user_end_date + timedelta(days=1)`
  2. Saat melakukan filtering pada DataFrame Pandas, gunakan perbandingan *inclusive*:
     `df = df[(df.index >= start_date) & (df.index <= user_end_date)]`
  3. Pastikan waktu diubah ke *end-of-day* (`23:59:59`) atau dinormalisasi tanggalnya saja.

---

## 🛠️ Langkah-Langkah Implementasi (Step-by-Step Execution Guide)

### Langkah 1: Audit Data Loader (`src/data_loader.py` atau sejenis)
1. Buka file tempat penarikan data ticker dilakukan.
2. Cek fungsi parsing argumen tanggal `-d` / `--dates`.
3. sesuaikan penarikan data `end_date`:
   ```python
   from datetime import datetime, timedelta

   # Tambah 1 hari khusus untuk query data agar tanggal akhir ter-cover penuh
   query_end_date = end_date + timedelta(days=1)
   ```
4. Jalankan pengujian penarikan data secara independen untuk memastikan tanggal 28/07/2026 masuk ke dalam DataFrame.

### Langkah 2: Tambahkan Helper Cleansing Ticker Symbol
1. Buka file utilitas visualisasi.
2. Buat fungsi helper `clean_ticker_symbol(symbol: str) -> str`.
3. Terapkan fungsi ini di semua titik render teks visualisasi, kecuali pada variabel query data.

### Langkah 3: Update Modul Visualisasi Animation Chart
1. Buka file pembuat animasi `.mp4` (misal menggunakan `matplotlib.animation`, `FuncAnimation`, `plotly`, atau `moviepy`).
2. Pastikan objek grafik/line/bar digambar untuk **seluruh** ticker yang ada dalam dataset.
3. Di dalam fungsi pembaruan frame (`update(frame_idx)`):
   * Ambil data snapshot pada `frame_idx`.
   * Sortir data berdasarkan profit/return dari terbesar ke terkecil.
   * Ambil top 3 item.
   * Gunakan fungsi `format_profit_percentage()` untuk mencegah adanya karakter `+-`.
   * Update teks header/title canvas chart dengan hasil top 3 tersebut.

### Langkah 4: Pengujian & Validasi (Verification Script)
Jalankan perintah tes berikut di terminal:

```bash
python src/main.py -t TPIA.JK ^JKSE BRPT.JK BUVA.JK TLKM.JK BMRI.JK BUMI.JK BULL.JK -d 14/07/2026 28/07/2026
```

**Kriteria Keberhasilan (Checklist Acceptance Criteria)**:
- [ ] File output `.mp4` berhasil dibuat.
- [ ] Label di chart menampilkan `TPIA`, `BRPT`, `BUVA`, `TLKM`, `BMRI`, `BUMI`, `BULL` (karakter `.JK` hilang). `^JKSE` tetap tampil rapi.
- [ ] Semua 8 ticker tampak dalam animasi grafik chart (garis/bar lengkap).
- [ ] Teks ringkasan di atas HANYA menampilkan **3 ticker teratas** secara dinamis per frame.
- [ ] Jika return minus, teks angka hanya menampilkan `-X.XX%` (tidak ada `+-`).
- [ ] Frame terakhir animasi chart menampilkan tanggal **28/07/2026**.

---

## 📄 Ringkasan Perubahan Berkas (Files to Modify)
| File | Deskripsi Perubahan |
| :--- | :--- |
| `src/data_loader.py` | Fix logika `end_date` (+1 hari query) agar tanggal 28/07/2026 ter-fetch. |
| `src/visualization/chart.py` | Tambah helper `clean_ticker_symbol`, fix format profit minus, implementasi dynamic Top 3 text header, pastikan seluruh series dirender. |
| `src/main.py` | Memastikan parsing argumen `-t` dan `-d` diteruskan dengan benar ke modul terkait. |

---

> **Pesan untuk Junior Dev / AI Agent**:
> Implementasikan tugas ini secara modular sesuai urutan langkah di atas. Uji terlebih dahulu perbaikan data tanggal di Langkah 1 sebelum memperbaiki bagian visualisasi animasi pada Langkah 2 dan 3.
