# Issue #10: Enhance Visualisasi Chart Image `.png` (Tanpa Mengubah Format `.mp4`)

## 📌 Ringkasan Tugas
Dokumen perencanaan ini dibuat sebagai panduan langkah-demi-langkah (*step-by-step implementation guide*) untuk **Junior Programmer** atau **AI Model** dalam mengimplementasikan peningkatan (*enhancement*) visualisasi chart **statis `.png`**.

**Tujuan Utama:**
1. Melakukan *enhancement* hanya pada visualisasi chart image **`.png`**.
2. **TIDAK** mengubah sama sekali output chart animasi **`.mp4`**.
3. Mengubah tampilan `.png` agar lebih bersih: **background transparan**, **tanpa legend**, **tanpa title**, **warna berbeda**, **X-axis horizontal**, **teks berwarna `#f2eae5`**, dan menambahkan **point di harga tertinggi** untuk setiap ticker yang disebutkan.

> **⚠️  Aturan Emas:** Semua perubahan hanya boleh dilakukan pada bagian kode yang membuat chart **PNG** (fungsi `create_static_chart()` / `generate_png_chart()`). Fungsi `create_animated_chart()` / `generate_mp4_animation()` dan semua konstanta visual milik MP4 **wajib tetap utuh / tidak boleh disentuh**.

---

## 🗂️ File yang Akan Dimodifikasi

| File | Perubahan |
| :--- | :--- |
| `src/service/chart.py` | Tambah konstanta warna khusus PNG; modifikasi fungsi `create_static_chart()` saja |

> **Catatan:** Tidak ada file baru yang perlu dibuat. Semua perubahan dilakukan pada file `src/service/chart.py` dan **hanya di bagian fungsi PNG**.

---

## 📋 Spesifikasi & Aturan Detail

Berikut daftar 8 aturan yang harus dipenuhi pada output chart **`.png`**:

| # | Aturan | Keterangan Singkat |
| :--- | :--- | :--- |
| 1 | **Enhance visualisasi `.png`** | Hanya ubah tampilan chart PNG, bukan MP4 |
| 2 | **Hilangkan background color** | Background figure & axes dibuat **transparan** |
| 3 | **Hilangkan legend** | Legend pada PNG **dihapus / tidak dirender** |
| 4 | **Warna berbeda dari `.mp4`** | Gunakan palet warna baru khusus PNG (lihat di bawah) |
| 5 | **Tambah "point" di harga tertinggi** | Tandai harga tertinggi untuk **setiap ticker yang disebutkan di list** saja |
| 6 | **X-axis horizontal** | Label sumbu X dibuat **mendatar** (tidak miring 45°) |
| 7 | **Hapus semua teks di title** | Title / header PNG dihapus total (baris 1, 2, dan 3) |
| 8 | **Warna seluruh teks `#f2eae5`** | Semua teks (tick label, axis label, dll.) berwarna `#f2eae5` |

### Palet Warna Baru Khusus PNG (Aturan #4)

Gunakan warna berikut **hanya untuk chart PNG**:

```python
PNG_TICKER_COLORS = [
    '#FF0509',  # Merah
    '#F0B90A',  # Kuning emas
    '#617DE9',  # Biru-ungu
    '#00AAE3',  # Biru cyan
    '#13F194',  # Hijau
    '#3CC6E6',  # Cyan muda
]
```

> **⚠️  Catatan Penting:** Di dokumen brief tertulis `"##617DE9"` (dua tanda pagar `##`). Ini adalah **typo** — nilai warna yang benar adalah **`#617DE9`** (satu tanda pagar `#`). Pastikan tidak menyalin tanda pagar ganda.

### Warna Teks Khusus PNG (Aturan #8)

```python
PNG_TEXT_COLOR = '#f2eae5'
```

---

## 🛠️ Tahapan Implementasi (Step-by-Step Guide)

Semua tahapan dilakukan di file **`src/service/chart.py`**. Gunakan editor/IDE dan cari lokasi berdasarkan nama fungsi / baris yang disebutkan.

### Tahap 1: Tambah Konstanta Warna Baru (Khusus PNG)

**Lokasi:** Area konstanta visual di bagian atas file (sekitar baris 28–43, di dekat `TICKER_COLORS`).

**Langkah-langkah:**

1. Buka file `src/service/chart.py`.
2. Cari blok konstanta visual, tepatnya setelah `TICKER_COLORS` (sekitar baris 40–44).
3. Tambahkan **dua konstanta baru** di bawah `TICKER_COLORS`:

```python
# Color palette khusus PNG — TIDAK memengaruhi MP4
PNG_TICKER_COLORS = [
    '#FF0509',  # Merah
    '#F0B90A',  # Kuning emas
    '#617DE9',  # Biru-ungu
    '#00AAE3',  # Biru cyan
    '#13F194',  # Hijau
    '#3CC6E6',  # Cyan muda
]

# Warna teks khusus PNG
PNG_TEXT_COLOR = '#f2eae5'
```

4. **JANGAN** mengubah `TICKER_COLORS`, `TEXT_COLOR`, `LEGEND_BG`, `LEGEND_BORDER`, dan `LEGEND_ALPHA` — konstanta itu dipakai oleh MP4.

---

### Tahap 2: Hilangkan Background Color (Transparan)

**Lokasi:** Fungsi `create_static_chart()` di `src/service/chart.py` (sekitar baris 198–200).

**Langkah-langkah:**

1. Cari fungsi `create_static_chart()`.
2. Di bagian pembuatan figure, saat ini ada kode:

```python
fig.patch.set_facecolor(DARK_BG)
ax.set_facecolor(DARK_BG)
```

3. Ubah menjadi **transparan**:

```python
fig.patch.set_alpha(0)   # background figure transparan
ax.patch.set_alpha(0)    # background axes transparan
```

4. Cari bagian `plt.savefig(...)` di akhir fungsi (sekitar baris 287):

```python
# Sebelum:
plt.savefig(output_path, dpi=100, facecolor=fig.get_facecolor(), bbox_inches='tight')

# Sesudah:
plt.savefig(output_path, dpi=100, transparent=True, bbox_inches='tight')
```

> **Penjelasan:** Parameter `transparent=True` memastikan file `.png` yang dihasilkan memiliki background transparan (bukan hitam). Jangan gunakan `facecolor` lagi.

---

### Tahap 3: Hilangkan Legend

**Lokasi:** Fungsi `create_static_chart()` di `src/service/chart.py` (sekitar baris 282–285).

**Langkah-langkah:**

1. Cari blok kode berikut di dalam `create_static_chart()`:

```python
legend = ax.legend(facecolor=LEGEND_BG, edgecolor=LEGEND_BORDER,
                   fontsize=FONT_SIZE, labelcolor=TEXT_COLOR,
                   framealpha=LEGEND_ALPHA, loc='upper left', borderpad=1)
legend.get_frame().set_linewidth(1)
```

2. **Hapus / jangan render** kedua baris tersebut.

> **Catatan:** Walaupun `label=display_name` masih ada di `ax.plot(...)`, legend tidak akan muncul karena `ax.legend()` tidak dipanggil. Ini aman dan tidak berpengaruh ke MP4.

---

### Tahap 4: Ganti Palet Warna (Khusus PNG)

**Lokasi:** Fungsi `create_static_chart()` di `src/service/chart.py` (sekitar baris 207).

**Langkah-langkah:**

1. Cari baris berikut di dalam loop `for i, (ticker, df) in enumerate(data.items()):`:

```python
color = TICKER_COLORS[i % len(TICKER_COLORS)]
```

2. Ganti menjadi:

```python
color = PNG_TICKER_COLORS[i % len(PNG_TICKER_COLORS)]
```

3. **Pastikan** bagian yang sama di `create_animated_chart()` (untuk MP4) **tetap** memakai `TICKER_COLORS`.

---

### Tahap 5: Tambah "Point" di Harga Tertinggi Setiap Ticker

**Lokasi:** Fungsi `create_static_chart()` di `src/service/chart.py` — di dalam loop `for i, (ticker, df) in enumerate(data.items()):` (sekitar baris 207–229).

**Langkah-langkah:**

1. Di dalam loop yang sama (setelah blok *last value marker* / annotation), tambahkan kode untuk menandai **harga tertinggi**:

```python
# Point di harga tertinggi untuk ticker ini (hanya yang disebutkan di list)
max_idx = int(np.argmax(prices))      # indeks harga (Close_IDR) tertinggi
max_date = dates[max_idx]
max_pct = pct_prices[max_idx]

ax.scatter([max_date], [max_pct], color=color, s=400, zorder=4,
           marker='*', edgecolor='white', linewidth=2)
```

2. **Penjelasan:**
   - `np.argmax(prices)` mencari index data dengan `Close_IDR` terbesar untuk ticker tersebut.
   - `pct_prices[max_idx]` adalah nilai persentase (sumbu Y) di titik harga tertinggi.
   - Marker dibedakan (misal bintang `'*'` dan ukuran lebih besar `s=400`) agar berbeda dengan marker nilai terakhir.
   - Karena kode ini berada di dalam loop per ticker, maka **setiap ticker di dalam list yang disebutkan** akan mendapat point di harga tertingginya. **Tidak ada** point tambahan untuk ticker di luar list.

---

### Tahap 6: Jadikan Label Sumbu X Horizontal

**Lokasi:** Fungsi `create_static_chart()` di `src/service/chart.py` (sekitar baris 265–266 dan 274).

**Langkah-langkah:**

1. Cari kode berikut di dalam `create_static_chart()`:

```python
ax.tick_params(axis='x', colors=TEXT_COLOR, labelsize=14, which='minor', labelrotation=45)
```

Ubah menjadi:

```python
ax.tick_params(axis='x', colors=PNG_TEXT_COLOR, labelsize=14, which='minor', labelrotation=0)
```

2. Cari kode berikut:

```python
plt.setp(ax.get_xticklabels(which='major'), rotation=45, ha='right')
```

Ubah menjadi:

```python
plt.setp(ax.get_xticklabels(which='major'), rotation=0, ha='center')
```

3. **Catatan:** Fungsi `create_animated_chart()` (MP4) juga punya `labelrotation=45` — **jangan diubah** karena hanya PNG yang diminta horizontal.

---

### Tahap 7: Hapus Semua Teks di Title

**Lokasi:** Fungsi `create_static_chart()` di `src/service/chart.py` (sekitar baris 232–260).

**Langkah-langkah:**

1. Hapus seluruh blok pembuatan & rendering title, yaitu:
   - Blok `performances = {...}`, `best_ticker = ...`, `worst_ticker = ...` (hanya dipakai untuk title).
   - Blok `if title_lines is None: ... title_lines = [...]`.
   - Semua panggilan `ax.text(...)` untuk title baris 1, 2, dan 3 (title line 1 ticker, line 2 tanggal, line 3 best/worst).

2. **PENTING — Jangan ubah signature fungsi.** Biarkan parameter `title_lines` tetap ada (agar `controller.py` yang memanggil `generate_png_chart(..., title_lines=[...])` tidak error), tetapi **jangan dirender / diabaikan**:

```python
def create_static_chart(
    data: Dict[str, pd.DataFrame],
    output_path: str = "output.png",
    title_lines: Optional[List[str]] = None,
) -> None:
    """..."""
    if not data:
        print("No data to plot")
        return

    tickers = list(data.keys())
    dates = data[tickers[0]]['Date'].tolist()

    # ... (title_lines DIABAIKAN — tidak dirender)

    # Plot each ticker
    for i, (ticker, df) in enumerate(data.items()):
        ...
```

3. Setelah penghapusan, pastikan tidak ada variabel seperti `best_ticker`, `worst_ticker`, `performances`, `title_lines[...]` yang masih dipakai di bagian bawah fungsi (jika ada, hapus juga agar tidak `NameError`).

---

### Tahap 8: Warna Seluruh Teks Menjadi `#f2eae5`

**Lokasi:** Fungsi `create_static_chart()` di `src/service/chart.py` (sekitar baris 263–281).

**Langkah-langkah:**

1. Ganti semua penggunaan `TEXT_COLOR` **di dalam `create_static_chart()`** dengan `PNG_TEXT_COLOR`:

```python
# Sebelum:
ax.tick_params(colors=TEXT_COLOR, labelsize=FONT_SIZE, which='major')
ax.yaxis.label.set_color(TEXT_COLOR)
ax.xaxis.label.set_color(TEXT_COLOR)

# Sesudah:
ax.tick_params(colors=PNG_TEXT_COLOR, labelsize=FONT_SIZE, which='major')
ax.yaxis.label.set_color(PNG_TEXT_COLOR)
ax.xaxis.label.set_color(PNG_TEXT_COLOR)
```

2. Untuk konsistensi visual (opsional tapi disarankan), samakan juga warna grid & spine di fungsi PNG:

```python
ax.grid(True, alpha=GRID_ALPHA, linestyle='--', color=PNG_TEXT_COLOR)

for spine in ax.spines.values():
    spine.set_color(PNG_TEXT_COLOR)
    spine.set_alpha(0.3)
    spine.set_linewidth(0.5)
```

3. **Yang TIDAK perlu diubah** (karena bukan "teks"):
   - Warna garis ticker (`color`) — tetap pakai `PNG_TICKER_COLORS`.
   - Warna annotation harga terakhir (`color=color`) — tetap pakai warna ticker.
   - Warna `edgecolor='white'` pada marker — boleh diubah ke `PNG_TEXT_COLOR` atau dibiarkan.

> **⚠️  Catatan:** JANGAN mengubah `TEXT_COLOR` global di bagian atas file, karena itu dipakai oleh MP4. Cukup gunakan konstanta baru `PNG_TEXT_COLOR` di dalam fungsi PNG.

---

### Tahap 9: Pengujian (Testing)

**Tujuan:** Memastikan output `.png` sesuai 8 aturan dan output `.mp4` **tidak berubah**.

**Langkah-langkah:**

1. Jalankan aplikasi untuk menghasilkan chart PNG & MP4, misalnya:

```bash
python src/main.py -t ^JKSE BBCA.JK BMRI.JK -d 14/07/2026 30/07/2026
```

2. **Verifikasi PNG** — buka file `.png` yang dihasilkan dan cek:
   - [ ] Background transparan (tidak ada warna latar).
   - [ ] Tidak ada legend.
   - [ ] Tidak ada teks title (baris 1, 2, 3).
   - [ ] Warna garis sesuai palet `#FF0509`, `#F0B90A`, `#617DE9`, `#00AAE3`, `#13F194`, `#3CC6E6`.
   - [ ] Ada marker khusus (*point*) di harga tertinggi untuk **setiap ticker di list**.
   - [ ] Label sumbu X mendatar (tidak miring).
   - [ ] Seluruh teks berwarna `#f2eae5`.

3. **Verifikasi MP4** — buka file `.mp4` yang dihasilkan dan pastikan:
   - [ ] Tampilan **sama persis** seperti sebelum perubahan (background `#0f172a`, ada legend, ada title, warna `TICKER_COLORS`, X-axis miring 45°).

4. **Cek error di terminal** — pastikan tidak ada `NameError` / `KeyError` setelah penghapusan blok title.

---

## 🔍 Ringkasan Perubahan Kode di `chart.py`

| Bagian | Perubahan |
| :--- | :--- |
| **Konstanta visual** | Tambah `PNG_TICKER_COLORS` dan `PNG_TEXT_COLOR` (tidak menyentuh konstanta MP4) |
| `create_static_chart()` — background | `fig.patch.set_alpha(0)` & `ax.patch.set_alpha(0)` (transparan) |
| `create_static_chart()` — savefig | `transparent=True` |
| `create_static_chart()` — legend | Hapus blok `ax.legend(...)` |
| `create_static_chart()` — warna | Pakai `PNG_TICKER_COLORS` pada loop plot |
| `create_static_chart()` — point tertinggi | Tambah `ax.scatter` di harga tertinggi tiap ticker |
| `create_static_chart()` — X-axis | `labelrotation=0` & `plt.setp(..., rotation=0, ha='center')` |
| `create_static_chart()` — title | Hapus rendering title (baris 1–3); biarkan parameter `title_lines` ada tapi diabaikan |
| `create_static_chart()` — warna teks | Semua `TEXT_COLOR` di fungsi ini → `PNG_TEXT_COLOR` (`#f2eae5`) |
| `create_animated_chart()` / `generate_mp4_animation()` | **TIDAK diubah** |

---

## ✅ Checklist Pengujian (Definition of Done)

- [ ] Output `.png` memiliki **background transparan** (tidak ada background color).
- [ ] Output `.png` **tanpa legend**.
- [ ] Output `.png` menggunakan palet warna `#FF0509`, `#F0B90A`, `#617DE9`, `#00AAE3`, `#13F194`, `#3CC6E6`.
- [ ] Output `.png` memiliki **point di harga tertinggi** untuk setiap ticker yang disebutkan (hanya yang disebutkan saja).
- [ ] Label **sumbu X pada `.png` horizontal** (tidak miring).
- [ ] **Semua teks pada `.png` dihapus dari title** (tidak ada teks title).
- [ ] Seluruh teks pada `.png` berwarna **`#f2eae5`**.
- [ ] Output **`.mp4` tidak berubah** (background, legend, title, warna, dan rotasi X-axis tetap seperti sebelumnya).
- [ ] Script `src/main.py` (atau `src/test.py`) berjalan tanpa error.
