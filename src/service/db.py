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
SYSTEM_USER = "yahoo_api"


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
            created_by      VARCHAR(100) DEFAULT 'yahoo_api',
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            updated_by      VARCHAR(100) DEFAULT 'yahoo_api',
            UNIQUE(symbol, date)
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized: MySQL stock_data")


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
        SELECT symbol, date, open, previous_close, high, low, close, volume
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

        try:
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
