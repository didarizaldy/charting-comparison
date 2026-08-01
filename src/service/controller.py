"""
Controller / Orchestrator module.
Connects db, yahoo_service, and chart modules to execute the full pipeline:

    1. Resolve date range from CLI parameters
    2. For each ticker, check DB → fetch from Yahoo Finance if missing → save to DB
    3. Load final datasets from DB
    4. Convert to IDR and align dates for chart visualization
    5. Generate PNG and MP4 output files
"""

import os
import sys
from datetime import datetime
from typing import List, Tuple

# Allow imports to work regardless of CWD
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from service import db
from service import yahoo_service
from service import chart


# ---------------------------------------------------------------------------
# Date resolution
# ---------------------------------------------------------------------------

def resolve_dates(
    date_mode: str,
    date_start: str = None,
    date_end: str = None,
    interval_days: int = None,
    period: str = None,
) -> Tuple[str, str]:
    """
    Resolve CLI date parameters into (start_date, end_date) strings in 'YYYY-MM-DD' format.

    Args:
        date_mode:     One of 'date', 'interval', 'period'
        date_start:    Start date string 'DD/MM/YYYY' (for date mode)
        date_end:      End date string 'DD/MM/YYYY' (for date mode)
        interval_days: Number of days to look back (for interval mode)
        period:        yfinance period string (for period mode)

    Returns:
        Tuple of (start_date, end_date) in 'YYYY-MM-DD' format
    """
    if date_mode == 'date':
        # Convert DD/MM/YYYY → YYYY-MM-DD
        start = datetime.strptime(date_start, '%d/%m/%Y').strftime('%Y-%m-%d')
        end = datetime.strptime(date_end, '%d/%m/%Y').strftime('%Y-%m-%d')
        return start, end

    elif date_mode == 'interval':
        return yahoo_service.parse_interval_to_dates(interval_days)

    elif date_mode == 'period':
        return yahoo_service.parse_period_to_dates(period)

    else:
        raise ValueError(f"Unknown date mode: {date_mode}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(
    tickers: List[str] = None,
    is_ihsp_mode: bool = False,
    date_mode: str = None,
    date_start: str = None,
    date_end: str = None,
    interval_days: int = None,
    period: str = None,
) -> None:
    """
    Execute the full application pipeline.

    Args:
        tickers:       List of ticker symbols (None for IHSP mode)
        is_ihsp_mode:  If True, run IHSP (^PEARL) vs IHSG (^JKSE) mode
        date_mode:     'date', 'interval', or 'period'
        date_start:    Start date 'DD/MM/YYYY' (date mode)
        date_end:      End date 'DD/MM/YYYY' (date mode)
        interval_days: Days to look back (interval mode)
        period:        yfinance period string (period mode)
    """
    print("=" * 60)
    print("  Stock / Asset Multi-Ticker Visualizer")
    print("=" * 60)

    # ── Step 1: Resolve dates ──────────────────────────────────────────
    start_date, end_date = resolve_dates(date_mode, date_start, date_end,
                                         interval_days, period)
    print(f"\nDate range: {start_date} -> {end_date}")
    if not is_ihsp_mode:
        print(f"Tickers   : {', '.join(tickers)}")

    # ── IHSP Mode: IHSP (^PEARL) vs IHSG (^JKSE) ──────────────────────
    if is_ihsp_mode:
        print("\n-- IHSP Mode: IHSP (^PEARL) vs IHSG (^JKSE) --")

        # Step IHSP-1: Initialise database (both tables)
        print("\n-- Initialising database --")
        db.init_db()
        db.init_simulate_table()

        # Step IHSP-2: Fetch missing data for all symbols + ^JKSE
        print("\n-- Checking / fetching data for all symbols + ^JKSE --")
        symbols = db.get_all_symbols_except_jkse()
        all_tickers = symbols + ['^JKSE']
        print(f"  Found {len(symbols)} symbols (excl. ^JKSE) + ^JKSE = {len(all_tickers)} total")

        # Extend fetch range 1 day back so H-1 is always available for forward-fill
        from datetime import datetime as dt, timedelta as td
        fetch_start = (dt.strptime(start_date, '%Y-%m-%d') - td(days=1)).strftime('%Y-%m-%d')

        for ticker in all_tickers:
            print(f"\n  [{ticker}]")

            # Always fetch fresh data for -x mode (skip cache shortcut).
            # Check what's already in DB and only fetch missing ranges.
            existing_df = db.get_stock_data(ticker, fetch_start, end_date)
            if not existing_df.empty:
                missing_ranges = db.find_missing_date_ranges(existing_df, fetch_start, end_date)
                if missing_ranges:
                    print(f"    >> Data parsial ({len(existing_df)} rows), fetching {len(missing_ranges)} missing range(s)...")
                    for miss_start, miss_end in missing_ranges:
                        print(f"    >> Fetch missing: {miss_start} to {miss_end}")
                        partial_df = yahoo_service.fetch_yfinance_data(ticker, miss_start, miss_end)
                        if not partial_df.empty:
                            db.save_stock_data(partial_df, ticker)
                        else:
                            print(f"    >> WARNING: No data for {miss_start} to {miss_end}")
                else:
                    print(f"    >> Data lengkap ({len(existing_df)} rows) — tidak ada yang perlu di-fetch")
            else:
                print(f"    >> Tidak ada data — fetch dari Yahoo Finance...")
                yf_df = yahoo_service.fetch_yfinance_data(ticker, fetch_start, end_date)
                if yf_df.empty:
                    print(f"    >> WARNING: Tidak ada data untuk {ticker}")
                    continue
                db.save_stock_data(yf_df, ticker)

        # Step IHSP-3: Calculate & save IHSP from all symbols except ^JKSE
        print("\n-- Calculating IHSP from all symbols (except ^JKSE) --")
        ihsp_df = db.calculate_and_save_ihsp(start_date, end_date)

        if ihsp_df.empty:
            print("\nERROR: Gagal menghitung IHSP. Pastikan data stock_data tersedia. Exiting.")
            return

        # Step IHSP-4: Load IHSG (^JKSE) data from stock_data
        print("\n-- Loading IHSG (^JKSE) data --")
        jkse_df = db.get_stock_data('^JKSE', start_date, end_date)

        if jkse_df.empty:
            print("\nERROR: Tidak ada data IHSG (^JKSE) di database. Exiting.")
            return

        # Step IHSP-5: Prepare data for chart
        print("\n-- Preparing data for IHSP vs IHSG chart --")

        # Rename columns for chart compatibility (chart expects 'Date' and 'Close_IDR')
        ihsp_chart = ihsp_df.copy()
        ihsp_chart = ihsp_chart.rename(columns={'date': 'Date', 'close': 'Close_IDR'})

        jkse_chart = jkse_df.copy()
        if 'date' in jkse_chart.columns and 'Date' not in jkse_chart.columns:
            jkse_chart = jkse_chart.rename(columns={'date': 'Date'})
        if 'close' in jkse_chart.columns and 'Close_IDR' not in jkse_chart.columns:
            jkse_chart = jkse_chart.rename(columns={'close': 'Close_IDR'})

        # Align dates: only keep dates present in BOTH datasets
        ihsp_dates = set(ihsp_chart['Date'].dt.date)
        jkse_dates = set(jkse_chart['Date'].dt.date)
        common_dates = sorted(ihsp_dates & jkse_dates)

        if not common_dates:
            print("\nERROR: Tidak ada tanggal yang sama antara IHSP dan IHSG. Exiting.")
            return

        ihsp_chart = ihsp_chart[ihsp_chart['Date'].dt.date.isin(common_dates)].reset_index(drop=True)
        jkse_chart = jkse_chart[jkse_chart['Date'].dt.date.isin(common_dates)].reset_index(drop=True)

        print(f"  Aligned data: {len(common_dates)} common dates from "
              f"{common_dates[0].strftime('%d/%m/%Y')} to {common_dates[-1].strftime('%d/%m/%Y')}")

        chart_data = {
            '^PEARL': ihsp_chart,
            '^JKSE': jkse_chart,
        }

        # Step IHSP-6: Generate output
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "output"
        )
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        png_path = os.path.join(output_dir, f"chart_ihsp_vs_ihsg_{timestamp}.png")
        mp4_path = os.path.join(output_dir, f"chart_ihsp_vs_ihsg_{timestamp}.mp4")

        # 6a. Static PNG — with custom IHSP title
        print("\n-- Generating IHSP vs IHSG static PNG chart --")
        try:
            dates_list = ihsp_chart['Date'].tolist()
            date_range_str = f"{dates_list[0].strftime('%d %b %Y')} - {dates_list[-1].strftime('%d %b %Y')}"
            chart.generate_png_chart(chart_data, png_path, title_lines=[
                "IHSP (^PEARL)  vs  IHSG (^JKSE)",
                date_range_str,
                None,  # Auto-calculate leading performer
            ])
        except Exception as e:
            print(f"  ERROR generating PNG: {e}")

        # 6b. Animated MP4
        print("\n-- Generating IHSP vs IHSG animated MP4 chart --")
        try:
            chart.generate_mp4_animation(chart_data, mp4_path)
        except Exception as e:
            print(f"  ERROR generating MP4: {e}")
            print("  Make sure ffmpeg is installed: https://ffmpeg.org/download.html")

        print("\n" + "=" * 60)
        print("  IHSP vs IHSG — Done!")
        print("=" * 60)
        return

    # -- Step 2: Initialise database --
    print("\n-- Initialising database --")
    db.init_db()

    # -- Step 3: For each ticker, check DB -> fetch (partial if needed) -> save --
    print("\n-- Checking / fetching data --")
    usd_to_idr = None  # Lazy-initialised (only fetched if needed)

    for ticker in tickers:
        print(f"\n[{ticker}]")

        # 3a. Check if data already exists in DB (full range)
        if db.check_data_completeness(ticker, start_date, end_date):
            print(f"  >> Data lengkap di database — menggunakan cache")
            continue

        # 3b. Check for partial data in DB
        existing_df = db.get_stock_data(ticker, start_date, end_date)
        if not existing_df.empty:
            # Partial data exists — fetch only the missing date ranges
            print(f"  >> Data parsial ditemukan ({len(existing_df)} rows), mencari tanggal yang kurang...")
            missing_ranges = db.find_missing_date_ranges(existing_df, start_date, end_date)

            if missing_ranges:
                for miss_start, miss_end in missing_ranges:
                    print(f"  >> Fetch missing range: {miss_start} to {miss_end}")
                    partial_df = yahoo_service.fetch_yfinance_data(ticker, miss_start, miss_end)
                    if not partial_df.empty:
                        db.save_stock_data(partial_df, ticker)
                        print(f"  >> Saved {len(partial_df)} rows for missing range")
                    else:
                        print(f"  >> WARNING: No data returned for missing range {miss_start} to {miss_end}")
            else:
                print(f"  >> No missing ranges detected — data should be complete")
        else:
            # 3c. No data at all — fetch full range from Yahoo Finance
            print(f"  >> Tidak ada data di DB — fetch dari Yahoo Finance...")
            yf_df = yahoo_service.fetch_yfinance_data(ticker, start_date, end_date)

            if yf_df.empty:
                print(f"  >> WARNING: Tidak ada data untuk {ticker}")
                continue

            # Validate: confirm data covers the requested date range
            fetched_start = yf_df['Date'].min().strftime('%Y-%m-%d')
            fetched_end = yf_df['Date'].max().strftime('%Y-%m-%d')
            print(f"  >> Rentang data: {fetched_start} -> {fetched_end}")

            # 3d. Save to database
            db.save_stock_data(yf_df, ticker)

    # -- Step 4: Load all data from DB --
    print("\n-- Loading data from database --")
    raw_data = {}
    for ticker in tickers:
        df = db.get_stock_data(ticker, start_date, end_date)
        if not df.empty:
            raw_data[ticker] = df
            print(f"  {ticker}: {len(df)} rows loaded")
        else:
            print(f"  {ticker}: no data in DB (skipped)")

    if not raw_data:
        print("\nERROR: No data available for any ticker. Exiting.")
        return

    # -- Step 5: Convert to IDR & align dates for chart --
    print("\n-- Converting to IDR & aligning dates --")

    # Only fetch exchange rate if there are non-IDR tickers
    has_non_idr = any(not yahoo_service.is_idr_ticker(t) for t in raw_data.keys())
    if has_non_idr:
        usd_to_idr = yahoo_service.get_usd_to_idr_rate()
    else:
        usd_to_idr = 1.0  # All tickers are already in IDR

    # The DB data uses lowercase column names; rename Close → Close for convert_to_idr
    # convert_to_idr expects a dict of DataFrames with 'Date' and a close-price column
    renamed_data = {}
    for ticker, df in raw_data.items():
        df_copy = df.copy()
        # Ensure 'Date' column exists (DB returns 'date' lowercase)
        if 'date' in df_copy.columns and 'Date' not in df_copy.columns:
            df_copy = df_copy.rename(columns={'date': 'Date'})
        if 'close' in df_copy.columns and 'Close' not in df_copy.columns:
            df_copy = df_copy.rename(columns={'close': 'Close'})
        renamed_data[ticker] = df_copy

    # Debug: write close prices to file for inspection
    debug_lines = []
    for t, df in renamed_data.items():
        close_col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
        if close_col:
            debug_lines.append(f"{t} (before convert): {df[close_col].tolist()}")

    idr_data = yahoo_service.convert_to_idr(renamed_data, usd_to_idr)

    for t, df in idr_data.items():
        debug_lines.append(f"{t} (after convert): {df['Close_IDR'].tolist()}")
        # Also show dates
        debug_lines.append(f"{t} dates: {df['Date'].tolist()}")

    debug_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "debug_output.txt")
    with open(debug_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(debug_lines))
    print(f"  Debug data written to {debug_path}")

    if not idr_data:
        print("\nERROR: Could not align data across tickers. Exiting.")
        return

    # -- Step 6: Generate output --
    # Use idr_data directly (no zero-baseline injection — chart normalizes from first actual price)
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ticker_label = '_'.join([t.replace('-', '').replace('^', '').replace('.', '') for t in tickers])

    png_path = os.path.join(output_dir, f"chart_comparison_{ticker_label}_{timestamp}.png")
    mp4_path = os.path.join(output_dir, f"chart_animation_{ticker_label}_{timestamp}.mp4")

    # 6a. Static PNG chart
    print("\n-- Generating static PNG chart --")
    try:
        chart.generate_png_chart(idr_data, png_path)
    except Exception as e:
        print(f"  ERROR generating PNG: {e}")

    # 6b. Animated MP4 chart
    print("\n-- Generating animated MP4 chart --")
    try:
        chart.generate_mp4_animation(idr_data, mp4_path)
    except Exception as e:
        print(f"  ERROR generating MP4: {e}")
        print("  Make sure ffmpeg is installed: https://ffmpeg.org/download.html")

    print("\n" + "=" * 60)
    print("  Done!")
    print("=" * 60)
