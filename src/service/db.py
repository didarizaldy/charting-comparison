"""
Database module for stock data storage and retrieval.
Uses SQLite as the database engine.

Table: stock_data
Columns: symbol, date, open, previous_close, high, low, close, volume,
         created_at, created_by, updated_at, updated_by
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime
from typing import Optional

# Database file path (relative to project root)
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
DB_PATH = os.path.join(DB_DIR, "stock_data.db")

# Created/updated metadata
SYSTEM_USER = "yahoo_api"


def _get_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database. Creates data directory if needed."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
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
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT    NOT NULL,
            date            DATE    NOT NULL,
            open            REAL,
            previous_close  REAL,
            high            REAL,
            low             REAL,
            close           REAL,
            volume          REAL,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by      TEXT    DEFAULT 'yahoo_api',
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by      TEXT    DEFAULT 'yahoo_api',
            UNIQUE(symbol, date)
        )
    """)

    # Create index for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_data_symbol_date
        ON stock_data(symbol, date)
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")


def inspect_table() -> None:
    """Print the table schema for debugging/verification purposes."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(stock_data);")
    columns = cursor.fetchall()
    conn.close()

    print("\n=== Table: stock_data ===")
    print(f"{'CID':<5} {'Name':<20} {'Type':<15} {'NotNull':<8} {'Default':<20} {'PK':<5}")
    print("-" * 75)
    for col in columns:
        cid, name, col_type, notnull, default, pk = col
        print(f"{cid:<5} {name:<20} {col_type:<15} {notnull:<8} {str(default):<20} {pk:<5}")


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
        WHERE symbol = ? AND date >= ? AND date <= ?
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

    Args:
        ticker: Stock ticker symbol
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format

    Returns:
        True if data exists for the full range, False otherwise
    """
    df = get_stock_data(ticker, start_date, end_date)
    if df.empty:
        return False

    # Check if we have data spanning the requested range
    db_min = df['date'].min()
    db_max = df['date'].max()
    from datetime import datetime as dt
    req_start = dt.strptime(start_date, '%Y-%m-%d')
    req_end = dt.strptime(end_date, '%Y-%m-%d')

    # End date must be strictly covered — no tolerance. If the DB is missing
    # the last requested day, we must re-fetch so the chart ends on the
    # correct date.
    from datetime import timedelta
    start_tolerance = timedelta(days=3)

    has_enough = (db_min <= req_start + start_tolerance) and (db_max >= req_end)
    if has_enough:
        print(f"  DB check [{ticker}]: data found ({len(df)} rows, {db_min.strftime('%Y-%m-%d')} to {db_max.strftime('%Y-%m-%d')})")
    return has_enough


def save_stock_data(df: pd.DataFrame, ticker: str) -> int:
    """
    Save stock data DataFrame to the database.
    Uses INSERT OR IGNORE to avoid duplicate entries (based on UNIQUE(symbol, date)).

    Args:
        df: DataFrame with columns matching yfinance output:
            Date, Open, High, Low, Close, Volume
            OR already formatted: date, open, high, low, close, volume
        ticker: The ticker symbol to associate with this data

    Returns:
        Number of rows inserted (excluding duplicates)
    """
    if df.empty:
        print(f"  No data to save for {ticker}")
        return 0

    conn = _get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    rows_inserted = 0

    # Normalize column names (handle both yfinance raw and pre-formatted)
    col_map = {}
    for col in df.columns:
        col_lower = col.lower()
        if col_lower in ('date',):
            col_map['date'] = col
        elif col_lower in ('open',):
            col_map['open'] = col
        elif col_lower in ('high',):
            col_map['high'] = col
        elif col_lower in ('low',):
            col_map['low'] = col
        elif col_lower in ('close',):
            col_map['close'] = col
        elif col_lower in ('volume',):
            col_map['volume'] = col

    # Calculate previous_close from close prices shifted by 1
    close_series = df[col_map['close']].values if 'close' in col_map else [None] * len(df)

    for idx in range(len(df)):
        row = df.iloc[idx]

        # Parse date
        date_val = row[col_map['date']] if 'date' in col_map else None
        if date_val is not None:
            if hasattr(date_val, 'strftime'):
                date_str = date_val.strftime('%Y-%m-%d')
            else:
                date_str = str(date_val)[:10]
        else:
            continue

        # Previous close is the close of the prior row
        prev_close = float(close_series[idx - 1]) if idx > 0 and close_series[idx - 1] is not None else None

        open_val = float(row[col_map['open']]) if 'open' in col_map and pd.notna(row[col_map['open']]) else None
        high_val = float(row[col_map['high']]) if 'high' in col_map and pd.notna(row[col_map['high']]) else None
        low_val = float(row[col_map['low']]) if 'low' in col_map and pd.notna(row[col_map['low']]) else None
        close_val = float(row[col_map['close']]) if 'close' in col_map and pd.notna(row[col_map['close']]) else None
        volume_val = float(row[col_map['volume']]) if 'volume' in col_map and pd.notna(row[col_map['volume']]) else None

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO stock_data
                    (symbol, date, open, previous_close, high, low, close, volume,
                     created_at, created_by, updated_at, updated_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker, date_str, open_val, prev_close,
                high_val, low_val, close_val, volume_val,
                now, SYSTEM_USER, now, SYSTEM_USER
            ))
            if cursor.rowcount > 0:
                rows_inserted += 1
        except Exception as e:
            print(f"  Error inserting row for {ticker} on {date_str}: {e}")

    conn.commit()
    conn.close()

    if rows_inserted > 0:
        print(f"  Saved {rows_inserted} new rows for {ticker} to database")
    else:
        print(f"  No new rows to insert for {ticker} (all duplicates)")

    return rows_inserted


def get_distinct_dates(ticker: str) -> list:
    """Get all dates stored for a ticker (for debugging)."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT date FROM stock_data WHERE symbol = ? ORDER BY date",
        (ticker,)
    )
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    return dates
