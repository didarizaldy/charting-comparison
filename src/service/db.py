"""
Database module for stock data storage and retrieval.
Uses MySQL as the database engine.

Table: stock_data
Columns: symbol, date, open, previous_close, high, low, close, volume,
         created_at, created_by, updated_at, updated_by
"""

import os
import mysql.connector
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))

# Created/updated metadata
SYSTEM_USER = "API_YAHOO"


def _get_connection() -> mysql.connector.MySQLConnection:
    """Get a connection to the MySQL database."""
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', 'root'),
        database=os.getenv('MYSQL_DATABASE', 'stock_data'),
    )
    return conn


def init_db() -> None:
    """
    Create the stock_data table if it does not already exist.
    Also verifies the schema matches expected columns.
    """
    conn = _get_connection()
    cursor = conn.cursor()

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
            created_by      VARCHAR(100) DEFAULT 'API_YAHOO',
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            updated_by      VARCHAR(100) DEFAULT 'API_YAHOO',
            UNIQUE(symbol, date)
        )
    """)

    conn.commit()

    # Add changes column if not exists
    try:
        cursor.execute("""
            ALTER TABLE stock_data
            ADD COLUMN changes DECIMAL(10,4) DEFAULT NULL
            AFTER volume
        """)
        conn.commit()
    except Exception:
        pass  # Column already exists — skip

    conn.close()
    print("Database initialized: MySQL stock_data")


def init_simulate_table() -> None:
    """Create the stock_simulate_data table if it does not already exist."""
    conn = _get_connection()
    cursor = conn.cursor()

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

    # Add changes column if not exists
    try:
        cursor.execute("""
            ALTER TABLE stock_simulate_data
            ADD COLUMN changes DECIMAL(10,4) DEFAULT NULL
            AFTER volume
        """)
        conn.commit()
    except Exception:
        pass  # Column already exists — skip

    conn.commit()
    conn.close()
    print("Database initialized: MySQL stock_simulate_data")


def inspect_table() -> None:
    """Print the table schema for debugging/verification purposes."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW COLUMNS FROM stock_data")
    columns = cursor.fetchall()
    conn.close()

    print("\n=== Table: stock_data ===")
    print(f"{'Field':<20} {'Type':<20} {'Null':<8} {'Key':<8} {'Default':<20} {'Extra':<20}")
    print("-" * 95)
    for col in columns:
        field, col_type, null, key, default, extra = col
        print(f"{field:<20} {str(col_type):<20} {null:<8} {key:<8} {str(default):<20} {extra:<20}")


def get_stock_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Retrieve stock data from the database for a given ticker and date range.

    Args:
        ticker: Stock ticker symbol (e.g., 'BBCA.JK', 'BTC-USD')
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format

    Returns:
        DataFrame with columns: symbol, date, open, previous_close, high, low, close, volume
    """
    conn = _get_connection()
    query = """
        SELECT symbol, date, open, previous_close, high, low, close, volume, changes
        FROM stock_data
        WHERE symbol = %s AND date >= %s AND date <= %s
        ORDER BY date ASC
    """
    df = pd.read_sql_query(query, conn, params=(ticker, start_date, end_date))
    conn.close()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])

    return df


def check_data_completeness(ticker: str, start_date: str, end_date: str) -> bool:
    """
    Check if data for the given ticker and date range is already stored in DB.
    Uses business-day calculation to determine expected data count, then
    compares against actual DB rows.

    Args:
        ticker: Stock ticker symbol
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format

    Returns:
        True if data exists for the full range (within tolerance), False otherwise
    """
    df = get_stock_data(ticker, start_date, end_date)
    if df.empty:
        return False

    # Calculate expected number of business days in the requested range
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    expected_days = int(np.busday_count(start_dt.date(), (end_dt + timedelta(days=1)).date()))

    # Count unique dates in DB for this range
    db_dates = pd.to_datetime(df['date']).dt.date
    unique_dates = set(db_dates)
    actual_days = len(unique_dates)

    # Tolerance: allow up to 3 missing days (unexpected market holidays, etc.)
    tolerance = 3
    missing_days = expected_days - actual_days
    is_complete = missing_days <= tolerance

    if is_complete:
        db_min = df['date'].min()
        db_max = df['date'].max()
        print(f"  DB check [{ticker}]: data found ({actual_days}/{expected_days} business days, "
              f"{db_min.strftime('%Y-%m-%d')} to {db_max.strftime('%Y-%m-%d')})")
    else:
        print(f"  DB check [{ticker}]: incomplete ({actual_days}/{expected_days} business days, "
              f"missing {missing_days} days)")

    return is_complete


def save_stock_data(df: pd.DataFrame, ticker: str) -> int:
    """
    Save stock data DataFrame to the database using UPSERT logic.
    - If a row for (symbol, date) does NOT exist → INSERT.
    - If a row for (symbol, date) ALREADY exists → UPDATE (so data can be refreshed).

    Validates that required columns exist and rows are non-empty before saving.

    Args:
        df: DataFrame with columns matching yfinance output:
            Date, Open, High, Low, Close, Volume
            OR already formatted: date, open, high, low, close, volume
        ticker: The ticker symbol to associate with this data

    Returns:
        Number of rows inserted or updated
    """
    if df.empty:
        print(f"  No data to save for {ticker}")
        return 0

    # ── Validation: required columns ──────────────────────────────────
    col_map = {}
    for col in df.columns:
        col_lower = col.lower()
        if col_lower == 'date':
            col_map['date'] = col
        elif col_lower == 'open':
            col_map['open'] = col
        elif col_lower == 'high':
            col_map['high'] = col
        elif col_lower == 'low':
            col_map['low'] = col
        elif col_lower == 'close':
            col_map['close'] = col
        elif col_lower == 'volume':
            col_map['volume'] = col

    if 'date' not in col_map:
        print(f"  ERROR: DataFrame for {ticker} has no 'date'/'Date' column — cannot save")
        return 0

    if 'close' not in col_map:
        print(f"  ERROR: DataFrame for {ticker} has no 'close'/'Close' column — cannot save")
        return 0

    # ── Upsert logic ─────────────────────────────────────────────────
    conn = _get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    rows_affected = 0

    close_series = df[col_map['close']].values if 'close' in col_map else [None] * len(df)

    for idx in range(len(df)):
        row = df.iloc[idx]

        # Parse date
        date_val = row[col_map['date']] if 'date' in col_map else None
        if date_val is not None:
            if hasattr(date_val, 'strftime'):
                date_str = date_val.strftime('%Y-%m-%d')
            else:
                date_str = str(pd.to_datetime(date_val).strftime('%Y-%m-%d'))
        else:
            continue

        # Previous close is the close of the prior row
        prev_close = float(close_series[idx - 1]) if idx > 0 and pd.notna(close_series[idx - 1]) else None

        open_val = float(row[col_map['open']]) if 'open' in col_map and pd.notna(row[col_map['open']]) else None
        high_val = float(row[col_map['high']]) if 'high' in col_map and pd.notna(row[col_map['high']]) else None
        low_val = float(row[col_map['low']]) if 'low' in col_map and pd.notna(row[col_map['low']]) else None
        close_val = float(row[col_map['close']]) if 'close' in col_map and pd.notna(row[col_map['close']]) else None
        volume_val = float(row[col_map['volume']]) if 'volume' in col_map and pd.notna(row[col_map['volume']]) else None

        # Calculate changes: % change from previous close (rounded to 2 decimals)
        if prev_close is not None and prev_close != 0 and close_val is not None:
            changes_val = round(((close_val - prev_close) / prev_close) * 100, 2)
        else:
            changes_val = None

        try:
            cursor.execute("""
                INSERT INTO stock_data
                    (symbol, date, open, previous_close, high, low, close, volume, changes,
                     created_at, created_by, updated_at, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            """, (
                ticker, date_str, open_val, prev_close,
                high_val, low_val, close_val, volume_val, changes_val,
                now, SYSTEM_USER, now, SYSTEM_USER,
            ))
            rows_affected += 1
        except Exception as e:
            print(f"  Error saving row for {ticker} on {date_str}: {e}")

    conn.commit()
    conn.close()

    if rows_affected > 0:
        print(f"  Saved {rows_affected} rows for {ticker} (upsert)")
    else:
        print(f"  No rows saved for {ticker}")

    return rows_affected


def get_distinct_dates(ticker: str) -> list:
    """Get all dates stored for a ticker (for debugging)."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT date FROM stock_data WHERE symbol = %s ORDER BY date",
        (ticker,)
    )
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    return dates


def find_missing_date_ranges(
    existing_df: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> List[Tuple[str, str]]:
    """
    Detect date ranges that are missing from existing DB data.

    Compares the full calendar range [start_date, end_date] against the dates
    present in *existing_df* and returns contiguous gaps as (gap_start, gap_end)
    pairs suitable for passing to fetch_yfinance_data().

    Args:
        existing_df: DataFrame with at least a 'date' column (from get_stock_data).
        start_date:  Requested start date 'YYYY-MM-DD'.
        end_date:    Requested end date 'YYYY-MM-DD'.

    Returns:
        List of (missing_start, missing_end) tuples in 'YYYY-MM-DD' format.
        Empty list if no gaps are found.
    """
    # Build set of dates already in DB
    existing_dates = set(pd.to_datetime(existing_df['date']).dt.date)

    # Build full calendar range (every day, not just business days)
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    all_dates = []
    current = start_dt
    while current <= end_dt:
        all_dates.append(current)
        current += timedelta(days=1)

    # Walk through the calendar and collect contiguous gaps
    missing_ranges: List[Tuple[str, str]] = []
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

    # Handle trailing gap
    if in_gap:
        missing_ranges.append((
            gap_start.strftime('%Y-%m-%d'),
            end_dt.strftime('%Y-%m-%d'),
        ))

    return missing_ranges


# ---------------------------------------------------------------------------
# IHSP (Indeks Harga Saham Pearl) — simulate table functions
# ---------------------------------------------------------------------------

def get_all_symbols_except_jkse() -> List[str]:
    """
    Ambil semua simbol unik dari tabel stock_list, kecuali '^JKSE'.

    Returns:
        List of ticker symbols (strings)
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT symbol FROM stock_list WHERE symbol != '^JKSE' ORDER BY symbol"
    )
    symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    return symbols


def get_all_stock_data_except_jkse(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Ambil data close price dari semua simbol di stock_list (kecuali ^JKSE)
    dalam rentang tanggal, dengan JOIN ke stock_data.

    Args:
        start_date: Start date 'YYYY-MM-DD'
        end_date:   End date 'YYYY-MM-DD'

    Returns:
        DataFrame dengan kolom: symbol, date, close (diurutkan berdasarkan date, symbol)
    """
    conn = _get_connection()
    query = """
        SELECT sd.symbol, sd.date, sd.close, sd.volume
        FROM stock_data sd
        INNER JOIN stock_list sl ON sd.symbol = sl.symbol
        WHERE sl.symbol != '^JKSE'
          AND sd.date >= %s AND sd.date <= %s
        ORDER BY sd.date ASC, sd.symbol ASC
    """
    df = pd.read_sql_query(query, conn, params=(start_date, end_date))
    conn.close()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])

    return df


def save_simulate_data(df: pd.DataFrame, symbol: str) -> int:
    """
    Simpan data simulasi ke tabel stock_simulate_data (upsert).

    Args:
        df:     DataFrame dengan kolom minimal 'date' dan 'close'
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

    # Map columns
    close_col = None
    date_col = None
    for col in df.columns:
        if col.lower() == 'close':
            close_col = col
        elif col.lower() == 'date':
            date_col = col

    if date_col is None or close_col is None:
        print(f"  ERROR: DataFrame missing 'date' or 'close' column — cannot save")
        return 0

    for idx in range(len(df)):
        row = df.iloc[idx]

        date_val = row[date_col]
        if hasattr(date_val, 'strftime'):
            date_str = date_val.strftime('%Y-%m-%d')
        else:
            date_str = str(pd.to_datetime(date_val).strftime('%Y-%m-%d'))

        close_val = float(row[close_col]) if pd.notna(row[close_col]) else None

        # Previous close is the close of the prior row
        prev_close = float(df.iloc[idx - 1][close_col]) if idx > 0 and pd.notna(df.iloc[idx - 1][close_col]) else None

        # Check for optional columns
        open_val = float(row['open']) if 'open' in df.columns and pd.notna(row['open']) else None
        high_val = float(row['high']) if 'high' in df.columns and pd.notna(row['high']) else None
        low_val = float(row['low']) if 'low' in df.columns and pd.notna(row['low']) else None
        volume_val = float(row['volume']) if 'volume' in df.columns and pd.notna(row['volume']) else None

        # Calculate changes: use pre-computed value from DataFrame if available,
        # otherwise fallback to % change from previous close (rounded to 2 decimals)
        if 'changes' in df.columns:
            raw = row['changes']
            changes_val = float(round(raw, 2)) if pd.notna(raw) else None
        elif prev_close is not None and prev_close != 0 and close_val is not None:
            changes_val = round(((close_val - prev_close) / prev_close) * 100, 2)
        else:
            changes_val = None

        try:
            cursor.execute("""
                INSERT INTO stock_simulate_data
                    (symbol, date, open, previous_close, high, low, close, volume, changes,
                     created_at, created_by, updated_at, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            """, (
                symbol, date_str, open_val, prev_close,
                high_val, low_val, close_val, volume_val, changes_val,
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
        symbol:     Simbol custom (misal '^PEARL')
        start_date: Start date 'YYYY-MM-DD'
        end_date:   End date 'YYYY-MM-DD'

    Returns:
        DataFrame dengan kolom: symbol, date, open, previous_close, high, low, close, volume
    """
    conn = _get_connection()
    query = """
        SELECT symbol, date, open, previous_close, high, low, close, volume, changes
        FROM stock_simulate_data
        WHERE symbol = %s AND date >= %s AND date <= %s
        ORDER BY date ASC
    """
    df = pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))
    conn.close()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])

    return df


def calculate_and_save_ihsp(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Hitung IHSP (Indeks Harga Saham Pearl) dengan rata-rata close price
    seluruh simbol (kecuali ^JKSE) per tanggal, lalu simpan ke tabel
    stock_simulate_data dengan simbol '^PEARL'.

    Rumus:
        IHSP_t       = SUM(close_i,t) / COUNT(symbols_t)
        changes_t    = AVERAGE( (close_i,t - close_i,t-1) / close_i,t-1 * 100 )

    Args:
        start_date: Start date 'YYYY-MM-DD'
        end_date:   End date 'YYYY-MM-DD'

    Returns:
        DataFrame dengan kolom: date, close, previous_close, changes.
        Empty jika tidak ada data.
    """
    # Ambil data dari H-1 agar perubahan hari pertama bisa dihitung
    fetch_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    df = get_all_stock_data_except_jkse(fetch_start, end_date)

    if df.empty:
        print("  WARNING: Tidak ada data untuk menghitung IHSP")
        return pd.DataFrame()

    # Group by date: rata-rata close & jumlah volume dari semua simbol
    ihsp_df = df.groupby('date', as_index=False).agg(
        close=('close', 'mean'),
        volume=('volume', 'sum'),
    )
    ihsp_df = ihsp_df.sort_values('date')

    # Hitung previous_close (nilai IHSP hari sebelumnya)
    ihsp_df['previous_close'] = ihsp_df['close'].shift(1)

    # Hitung changes: rata-rata %change per-ticker per hari
    # Step 1: untuk setiap ticker, hitung %change harian
    symbols = df['symbol'].unique()
    change_frames = []
    for sym in symbols:
        sym_df = df[df['symbol'] == sym].sort_values('date').copy()
        sym_df['pct'] = sym_df['close'].pct_change() * 100
        change_frames.append(sym_df[['date', 'pct']])

    # Step 2: rata-rata %change per hari, rounded 2 desimal
    all_changes = pd.concat(change_frames)
    daily_avg_change = all_changes.groupby('date')['pct'].mean().round(2)
    ihsp_df['changes'] = ihsp_df['date'].map(daily_avg_change)

    # Filter hanya rentang yang diminta (buang data H-1)
    start_dt = pd.to_datetime(start_date)

    # Forward-fill: jika start_date tidak ada data (hari libur/weekend),
    # gunakan data H-1 agar chart tetap dimulai dari tanggal yang diminta
    if start_dt not in ihsp_df['date'].values:
        prev_rows = ihsp_df[ihsp_df['date'] < start_dt]
        if not prev_rows.empty:
            fill_row = prev_rows.iloc[-1:].copy()
            fill_row['date'] = start_dt
            fill_row['previous_close'] = None
            fill_row['changes'] = None
            ihsp_df = pd.concat([fill_row, ihsp_df], ignore_index=True).sort_values('date')

    ihsp_df = ihsp_df[ihsp_df['date'] >= start_dt].copy()

    # Simpan ke stock_simulate_data dengan simbol ^PEARL
    save_simulate_data(ihsp_df, '^PEARL')

    print(f"  IHSP (^PEARL) calculated and saved: {len(ihsp_df)} rows")
    return ihsp_df
