"""
Test script untuk eksplorasi data dari package `yfinance`.
Gunakan file ini untuk cek data apa saja yang bisa diambil dari Yahoo Finance.
"""

import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# ===========================================================================
# CONFIG - Ganti ticker di sini sesuai kebutuhan
# ===========================================================================
TICKER = "BBCA.JK"       # ticker utama yang mau dites
TICKER2 = "AAPL"          # ticker pembanding (US stock)
CRYPTO = "BTC-USD"        # crypto
INDEX = "^JKSE"           # IHSG
FOREX = "USDIDR=X"        # USD/IDR

# ===========================================================================
# 1. BASIC INFO - Ticker object
# ===========================================================================
print("=" * 70)
print("1. TICKER INFO")
print("=" * 70)

ticker = yf.Ticker(TICKER)
print(f"\n>>> Ticker: {TICKER}")
print(f"Type: {type(ticker)}")
print(f"Available methods: {[m for m in dir(ticker) if not m.startswith('_')]}")

# ===========================================================================
# 2. INFO DICT - Semua metadata
# ===========================================================================
print("\n" + "=" * 70)
print("2. INFO DICT (semua metadata)")
print("=" * 70)

info = ticker.info
print(f"\n>>> Jumlah key dalam info: {len(info)}")
print(f"\n--- ALL KEYS ---")
for i, k in enumerate(sorted(info.keys()), 1):
    print(f"  {i:3d}. {k}")

print(f"\n--- SELECTED VALUES ---")
selected = [
    'symbol', 'shortName', 'longName', 'sector', 'industry',
    'marketCap', 'trailingPE', 'forwardPE', 'dividendYield',
    'fiftyTwoWeekHigh', 'fiftyTwoWeekLow', 'previousClose',
    'regularMarketOpen', 'dayHigh', 'dayLow', 'volume',
    'avgVolume', 'beta', 'currency', 'exchange',
    'country', 'website', 'description',
]
for key in selected:
    val = info.get(key, 'N/A')
    print(f"  {key:25s}: {val}")

# ===========================================================================
# 3. HISTORICAL DATA (harga historis)
# ===========================================================================
print("\n" + "=" * 70)
print("3. HISTORY (data historis)")
print("=" * 70)

# Period pendek
hist_5d = ticker.history(period="5d")
print(f"\n>>> 5 hari terakhir ({TICKER})")
print(f"Shape: {hist_5d.shape}")
print(f"Columns: {list(hist_5d.columns)}")
print(hist_5d)

# Period lebih panjang
hist_1mo = ticker.history(period="1mo")
print(f"\n>>> 1 bulan terakhir ({TICKER})")
print(f"Shape: {hist_1mo.shape}")
print(hist_1mo.head())

# ===========================================================================
# 4. DIVIDENDS & SPLITS
# ===========================================================================
print("\n" + "=" * 70)
print("4. DIVIDENDS & SPLITS")
print("=" * 70)

dividends = ticker.dividends
print(f"\n>>> Dividends ({TICKER})")
print(f"Shape: {dividends.shape}")
if not dividends.empty:
    print(dividends.tail(10))

splits = ticker.splits
print(f"\n>>> Splits ({TICKER})")
print(f"Shape: {splits.shape}")
if not splits.empty:
    print(splits)

# ===========================================================================
# 5. ACTIONS (dividends + splits gabungan)
# ===========================================================================
print("\n" + "=" * 70)
print("5. ACTIONS (dividends + splits)")
print("=" * 70)

actions = ticker.actions
print(f"\n>>> Actions ({TICKER})")
print(f"Shape: {actions.shape}")
if not actions.empty:
    print(actions.tail(10))

# ===========================================================================
# 6. FINANCIALS (laporan keuangan)
# ===========================================================================
print("\n" + "=" * 70)
print("6. FINANCIALS (laporan keuangan)")
print("=" * 70)

# Income statement
try:
    income = ticker.financials
    print(f"\n>>> Income Statement ({TICKER})")
    print(f"Shape: {income.shape}")
    print(income)
except Exception as e:
    print(f"  Income statement error: {e}")

# Balance sheet
try:
    balance = ticker.balance_sheet
    print(f"\n>>> Balance Sheet ({TICKER})")
    print(f"Shape: {balance.shape}")
    print(balance)
except Exception as e:
    print(f"  Balance sheet error: {e}")

# Cash flow
try:
    cashflow = ticker.cashflow
    print(f"\n>>> Cash Flow ({TICKER})")
    print(f"Shape: {cashflow.shape}")
    print(cashflow)
except Exception as e:
    print(f"  Cashflow error: {e}")

# ===========================================================================
# 7. QUARTERLY FINANCIALS
# ===========================================================================
print("\n" + "=" * 70)
print("7. QUARTERLY FINANCIALS")
print("=" * 70)

try:
    q_income = ticker.quarterly_financials
    print(f"\n>>> Quarterly Income ({TICKER})")
    print(f"Shape: {q_income.shape}")
    print(q_income)
except Exception as e:
    print(f"  Quarterly financials error: {e}")

# ===========================================================================
# 8. ANALYSTS / REKOMENDASI
# ===========================================================================
print("\n" + "=" * 70)
print("8. ANALYSTS & RECOMMENDATIONS")
print("=" * 70)

try:
    rec = ticker.recommendations
    print(f"\n>>> Recommendations ({TICKER})")
    if rec is not None and not rec.empty:
        print(rec.tail(10))
    else:
        print("  (tidak tersedia)")
except Exception as e:
    print(f"  Error: {e}")

# ===========================================================================
# 9. MAJOR HOLDERS & INSTITUTIONAL HOLDERS
# ===========================================================================
print("\n" + "=" * 70)
print("9. HOLDERS")
print("=" * 70)

try:
    major = ticker.major_holders
    print(f"\n>>> Major Holders ({TICKER})")
    if major is not None and not major.empty:
        print(major)
    else:
        print("  (tidak tersedia)")
except Exception as e:
    print(f"  Error: {e}")

try:
    inst = ticker.institutional_holders
    print(f"\n>>> Institutional Holders ({TICKER})")
    if inst is not None and not inst.empty:
        print(inst.head(10))
    else:
        print("  (tidak tersedia)")
except Exception as e:
    print(f"  Error: {e}")

# ===========================================================================
# 10. OPTIONS (jika ada)
# ===========================================================================
print("\n" + "=" * 70)
print("10. OPTIONS")
print("=" * 70)

try:
    opt_dates = ticker.options
    print(f"\n>>> Option expiration dates ({TICKER}):")
    if opt_dates:
        print(f"  {len(opt_dates)} dates available")
        print(f"  First 5: {opt_dates[:5]}")
        # Coba ambil option chain untuk date pertama
        if opt_dates:
            chain = ticker.option_chain(opt_dates[0])
            print(f"\n  Calls shape: {chain.calls.shape}")
            print(f"  Puts shape:  {chain.puts.shape}")
    else:
        print("  (tidak tersedia)")
except Exception as e:
    print(f"  Error: {e}")

# ===========================================================================
# 11. MULTI-TICKER DOWNLOAD
# ===========================================================================
print("\n" + "=" * 70)
print("11. MULTI-TICKER DOWNLOAD (yf.download)")
print("=" * 70)

tickers = [TICKER, CRYPTO, FOREX]
print(f"\n>>> Download: {tickers}")
try:
    data = yf.download(tickers, period="5d", group_by="ticker")
    print(f"Type: {type(data)}")
    print(f"Shape: {data.shape}")
    print(f"Columns: {data.columns.tolist()[:10]}...")
    print(data.tail())
except Exception as e:
    print(f"  Error: {e}")

# ===========================================================================
# 12. CRYPTO (BTC, ETH, etc.)
# ===========================================================================
print("\n" + "=" * 70)
print("12. CRYPTO")
print("=" * 70)

print(f"\n>>> Crypto: {CRYPTO}")
crypto_ticker = yf.Ticker(CRYPTO)
crypto_hist = crypto_ticker.history(period="5d")
print(f"Shape: {crypto_hist.shape}")
print(crypto_hist)

# Info crypto
crypto_info = crypto_ticker.info
print(f"\n--- Crypto Info Keys ---")
crypto_keys = ['symbol', 'shortName', 'regularMarketPrice', 'marketCap',
               'volume24Hr', 'circulatingSupply', 'maxSupply']
for key in crypto_keys:
    print(f"  {key:25s}: {crypto_info.get(key, 'N/A')}")

# ===========================================================================
# 13. FOREX
# ===========================================================================
print("\n" + "=" * 70)
print("13. FOREX")
print("=" * 70)

print(f"\n>>> Forex: {FOREX}")
fx = yf.Ticker(FOREX)
fx_hist = fx.history(period="5d")
print(f"Shape: {fx_hist.shape}")
print(fx_hist)

# ===========================================================================
# 14. INDEX
# ===========================================================================
print("\n" + "=" * 70)
print("14. INDEX (IHSG)")
print("=" * 70)

print(f"\n>>> Index: {INDEX}")
idx = yf.Ticker(INDEX)
idx_hist = idx.history(period="1mo")
print(f"Shape: {idx_hist.shape}")
print(idx_hist.tail())

# ===========================================================================
# 15. EARNINGS
# ===========================================================================
print("\n" + "=" * 70)
print("15. EARNINGS")
print("=" * 70)

try:
    earnings = ticker.earnings
    print(f"\n>>> Earnings ({TICKER})")
    if earnings is not None and not earnings.empty:
        print(earnings)
    else:
        print("  (tidak tersedia)")
except Exception as e:
    print(f"  Error: {e}")

# ===========================================================================
# 16. %CHG (PERCENTAGE CHANGE)
# ===========================================================================
print("\n" + "=" * 70)
print("16. %CHG (PERCENTAGE CHANGE)")
print("=" * 70)

# --- a. Dari info dict (real-time / daily change %) ---
print(f"\n>>> a. Dari INFO DICT ({TICKER})")
info_chg_keys = [
    'regularMarketChangePercent',
    'regularMarketChange',
    'regularMarketPreviousClose',
    'regularMarketPrice',
    'fiftyDayAverageChangePercent',
    'twoHundredDayAverageChangePercent',
]
for key in info_chg_keys:
    val = info.get(key, 'N/A')
    print(f"  {key:40s}: {val}")

# --- b. Hitung manual dari history (daily %chg) ---
print(f"\n>>> b. Daily %CHG dari history.Close ({TICKER})")
hist_for_chg = ticker.history(period="1mo")
hist_for_chg['%chg_daily'] = hist_for_chg['Close'].pct_change() * 100
print(hist_for_chg[['Close', '%chg_daily']].tail(10))

# --- c. %CHG dari harga pertama ke terakhir dalam periode ---
print(f"\n>>> c. %CHG total (dari hari pertama ke terakhir) ({TICKER})")
first_close = hist_for_chg['Close'].iloc[0]
last_close = hist_for_chg['Close'].iloc[-1]
total_pct = ((last_close - first_close) / first_close) * 100
print(f"  Harga awal : {first_close:,.2f}")
print(f"  Harga akhir: {last_close:,.2f}")
print(f"  Total %CHG : {total_pct:+.2f}%")

# --- d. %CHG intraday (high vs low vs close) ---
print(f"\n>>> d. %CHG intraday ({TICKER})")
hist_5d = ticker.history(period="5d")
hist_5d['%chg_low_to_high'] = ((hist_5d['High'] - hist_5d['Low']) / hist_5d['Low']) * 100
hist_5d['%chg_open_to_close'] = ((hist_5d['Close'] - hist_5d['Open']) / hist_5d['Open']) * 100
print(hist_5d[['Open', 'High', 'Low', 'Close', '%chg_low_to_high', '%chg_open_to_close']])

# --- e. Multi-ticker %CHG comparison ---
print(f"\n>>> e. %CHG comparison (multi-ticker)")
comp_tickers = [TICKER, CRYPTO, "^GSPC"]
comp_data = yf.download(comp_tickers, period="5d", group_by="ticker")
print("\n  (close) raw:")
print(comp_data.xs('Close', axis=1, level=1).tail())
print("\n  (%chg daily):")
pct = comp_data.xs('Close', axis=1, level=1).pct_change() * 100
print(pct.tail())

# ===========================================================================
# DONE
# ===========================================================================
print("\n" + "=" * 70)
print("SELESAI! Semua data berhasil di-fetch.")
print("=" * 70)
