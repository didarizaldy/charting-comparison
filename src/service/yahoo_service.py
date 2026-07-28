"""
Yahoo Finance data fetching service.
Handles fetching stock/asset data from yfinance, date parsing, and IDR conversion.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings('ignore')


# ---------------------------------------------------------------------------
# Ticker classification helpers
# ---------------------------------------------------------------------------

def is_idr_ticker(ticker: str) -> bool:
    """
    Check if a ticker is already priced in IDR (Indonesian Rupiah).

    Indonesian tickers on Yahoo Finance are already in IDR:
    - ^JKSE (Jakarta Composite Index / IHSG)
    - ^IHSG (alternative name for Jakarta Composite Index)
    - *.JK  (stocks listed on Jakarta Stock Exchange, e.g., BBCA.JK, BRI.JK)

    Args:
        ticker: Yahoo Finance ticker symbol

    Returns:
        True if the ticker is already priced in IDR
    """
    ticker_upper = ticker.upper().strip()

    # Indonesian index tickers
    idr_indices = {'^JKSE', '^IHSG'}
    if ticker_upper in idr_indices:
        return True

    # Indonesian stocks listed on Jakarta Stock Exchange (.JK suffix)
    if ticker_upper.endswith('.JK'):
        return True

    return False


# ---------------------------------------------------------------------------
# Exchange rate
# ---------------------------------------------------------------------------

def get_usd_to_idr_rate() -> float:
    """
    Get realtime USD to IDR exchange rate using yfinance (USDIDR=X).
    Falls back to a fixed rate if the API call fails.

    Returns:
        float: USD to IDR exchange rate
    """
    try:
        usd_idr = yf.Ticker("USDIDR=X")
        hist = usd_idr.history(period="1d")
        if not hist.empty:
            rate = float(hist['Close'].iloc[-1])
            print(f"USD to IDR rate: {rate:,.2f}")
            return rate
    except Exception as e:
        print(f"Error fetching USD/IDR rate: {e}")

    # Fallback rate (approximate)
    fallback_rate = 15500.0
    print(f"Using fallback rate: {fallback_rate:,.2f}")
    return fallback_rate


# ---------------------------------------------------------------------------
# Date / period parsing
# ---------------------------------------------------------------------------

def parse_period_to_dates(period_str: str) -> Tuple[str, str]:
    """
    Convert a yfinance period string to a (start_date, end_date) tuple.

    Supported values: 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y

    Args:
        period_str: Period string (e.g., '1mo', '6mo', '1y')

    Returns:
        Tuple of (start_date, end_date) in 'YYYY-MM-DD' format
    """
    period_map = {
        '5d': 5,
        '1mo': 30,
        '3mo': 91,
        '6mo': 182,
        '1y': 365,
        '2y': 730,
        '5y': 1825,
    }

    period_lower = period_str.strip().lower()
    if period_lower not in period_map:
        raise ValueError(
            f"Unsupported period '{period_str}'. "
            f"Supported: {', '.join(period_map.keys())}"
        )

    days = period_map[period_lower]
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


def parse_interval_to_dates(days: int) -> Tuple[str, str]:
    """
    Convert an interval (number of days) to a (start_date, end_date) tuple.

    Args:
        days: Number of days to look back from today

    Returns:
        Tuple of (start_date, end_date) in 'YYYY-MM-DD' format
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=int(days))
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


# ---------------------------------------------------------------------------
# Yahoo Finance data fetching
# ---------------------------------------------------------------------------

def fetch_yfinance_data(
    ticker: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data from Yahoo Finance for a single ticker.

    Args:
        ticker:    Yahoo Finance ticker symbol (e.g., 'BTC-USD', 'BBCA.JK')
        start_date: Start date in 'YYYY-MM-DD' format
        end_date:   End date in 'YYYY-MM-DD' format

    Returns:
        DataFrame with columns:
            Date (datetime64), Open, High, Low, Close, Volume, previous_close
        Empty DataFrame if no data is returned by yfinance.
    """
    try:
        stock = yf.Ticker(ticker)
        # yfinance end date is EXCLUSIVE — add 1 day so the user's requested
        # end date is actually included in the returned data.
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        end_date_inclusive = end_dt.strftime('%Y-%m-%d')
        hist = stock.history(start=start_date, end=end_date_inclusive)

        if hist.empty:
            print(f"  No data returned for {ticker} ({start_date} to {end_date})")
            return pd.DataFrame()

        hist = hist.reset_index()

        # Ensure timezone-naive dates
        hist['Date'] = pd.to_datetime(hist['Date']).dt.tz_localize(None)

        # Build result DataFrame
        result = pd.DataFrame({
            'Date':           hist['Date'],
            'Open':           hist['Open'].astype(float),
            'High':           hist['High'].astype(float),
            'Low':            hist['Low'].astype(float),
            'Close':          hist['Close'].astype(float),
            'Volume':         hist['Volume'].astype(float),
            'previous_close': hist['Close'].shift(1).astype(float),
        })

        # Drop the first row which has no previous_close
        result = result.dropna(subset=['Close']).reset_index(drop=True)

        print(f"  Fetched {len(result)} rows for {ticker} from Yahoo Finance")
        return result

    except Exception as e:
        print(f"  Error fetching data for {ticker}: {e}")
        return pd.DataFrame()


def fetch_yfinance_data_by_period(
    ticker: str,
    period: str,
) -> pd.DataFrame:
    """
    Fetch historical data using a yfinance period string (e.g., '1mo', '6mo').

    Args:
        ticker: Yahoo Finance ticker symbol
        period: Period string (e.g., '5d', '1mo', '3mo', '6mo', '1y')

    Returns:
        DataFrame with OHLCV data + previous_close column
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)

        if hist.empty:
            print(f"  No data returned for {ticker} (period={period})")
            return pd.DataFrame()

        hist = hist.reset_index()
        hist['Date'] = pd.to_datetime(hist['Date']).dt.tz_localize(None)

        result = pd.DataFrame({
            'Date':           hist['Date'],
            'Open':           hist['Open'].astype(float),
            'High':           hist['High'].astype(float),
            'Low':            hist['Low'].astype(float),
            'Close':          hist['Close'].astype(float),
            'Volume':         hist['Volume'].astype(float),
            'previous_close': hist['Close'].shift(1).astype(float),
        })

        result = result.dropna(subset=['Close']).reset_index(drop=True)
        print(f"  Fetched {len(result)} rows for {ticker} from Yahoo Finance (period={period})")
        return result

    except Exception as e:
        print(f"  Error fetching data for {ticker}: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Data alignment & IDR conversion (for chart visualization)
# ---------------------------------------------------------------------------

def convert_to_idr(
    data_frames: Dict[str, pd.DataFrame],
    usd_to_idr: float,
) -> Dict[str, pd.DataFrame]:
    """
    Convert prices to IDR and align dates across multiple tickers.

    Tickers already priced in IDR (e.g., ^JKSE, *.JK) are kept as-is.
    Other tickers (priced in USD) are multiplied by the exchange rate.

    Uses approximate date alignment (nearest-merge with tolerance) to handle
    tickers with different trading calendars (e.g., crypto 7d/week vs stock exchange days).

    Args:
        data_frames: Dict of ticker -> DataFrame. Each DF must have 'Date' and
                     at least one price column ('Close' or 'Close_Original').
        usd_to_idr:  USD → IDR exchange rate

    Returns:
        Dict of ticker -> DataFrame with 'Date' and 'Close_IDR' columns,
        aligned to a common set of dates.
    """
    if not data_frames:
        return {}

    # Log which tickers are already in IDR
    for ticker in data_frames.keys():
        if is_idr_ticker(ticker):
            print(f"  {ticker}: already priced in IDR - skipping USD conversion")
        else:
            print(f"  {ticker}: priced in USD - will convert to IDR (rate: {usd_to_idr:,.2f})")

    # Normalise dates to date-only (strip time/tz)
    normalized: Dict[str, pd.DataFrame] = {}
    for ticker, df in data_frames.items():
        df_copy = df.copy()

        # Detect which column holds the close price
        if 'Close_IDR' in df_copy.columns:
            close_col = 'Close_IDR'
        elif 'Close_Original' in df_copy.columns:
            close_col = 'Close_Original'
        elif 'Close' in df_copy.columns:
            close_col = 'Close'
        elif 'close' in df_copy.columns:
            close_col = 'close'
            df_copy = df_copy.rename(columns={'close': 'Close_Original'})
            close_col = 'Close_Original'
        else:
            print(f"  Warning: no Close column found for {ticker}, skipping")
            continue

        if close_col != 'Close_Original':
            df_copy = df_copy.rename(columns={close_col: 'Close_Original'})

        df_copy['Date'] = pd.to_datetime(df_copy['Date']).dt.tz_localize(None).dt.normalize()
        df_copy = df_copy.drop_duplicates(subset='Date', keep='last')
        df_copy = df_copy.sort_values('Date').reset_index(drop=True)
        normalized[ticker] = df_copy[['Date', 'Close_Original']]

    if not normalized:
        return {}

    # Find common date RANGE
    # Use max(max_dates) so the range extends to the latest date available
    # across all tickers. Tickers missing the last day will use their nearest
    # available data via merge_asof.
    min_dates = [df['Date'].min() for df in normalized.values()]
    max_dates = [df['Date'].max() for df in normalized.values()]
    range_start = max(min_dates)
    range_end = max(max_dates)

    if range_start > range_end:
        print("  No overlapping date range found across tickers")
        return {}

    print(f"  Common date range: {range_start.strftime('%Y-%m-%d')} to {range_end.strftime('%Y-%m-%d')}")

    # Use the ticker with the most dates as the reference calendar
    # so common_dates covers the full requested range.
    ref_ticker = max(normalized.keys(), key=lambda t: len(normalized[t]))
    ref_df = normalized[ref_ticker]
    ref_dates = ref_df[(ref_df['Date'] >= range_start) & (ref_df['Date'] <= range_end)]
    common_dates = ref_dates['Date'].reset_index(drop=True)

    print(f"  Using {ref_ticker} as reference calendar ({len(common_dates)} dates)")

    # Align all tickers to reference dates
    # Strategy: use exact merge (inner join) first for same-calendar tickers,
    # then fall back to merge_asof (nearest, 3-day tolerance) for cross-calendar alignment.
    aligned_data: Dict[str, pd.DataFrame] = {}
    ref_df_temp = pd.DataFrame({'Date': common_dates})

    for ticker, df in normalized.items():
        df_range = df[(df['Date'] >= range_start) & (df['Date'] <= range_end)].copy()
        df_range = df_range.sort_values('Date').reset_index(drop=True)

        # Debug: print date types and values
        print(f"  [DBG] {ticker} ref dates dtype: {ref_df_temp['Date'].dtype}, range dtype: {df_range['Date'].dtype}")
        print(f"  [DBG] {ticker} ref head: {ref_df_temp['Date'].head(3).tolist()}")
        print(f"  [DBG] {ticker} range head: {df_range['Date'].head(3).tolist()}")
        print(f"  [DBG] {ticker} range Close_Original: {df_range['Close_Original'].tolist()}")

        # Use left join from reference calendar to ensure all dates are preserved,
        # then forward-fill missing values for tickers that don't have data on all dates.
        aligned = pd.merge(ref_df_temp, df_range, on='Date', how='left')
        aligned['Close_Original'] = aligned['Close_Original'].ffill().bfill()
        method = "left-join+ffill"

        print(f"  [DBG] {ticker} aligned Close_IDR: {aligned['Close_Original'].tolist()}")

        if is_idr_ticker(ticker):
            aligned['Close_IDR'] = aligned['Close_Original']
        else:
            aligned['Close_IDR'] = aligned['Close_Original'] * usd_to_idr

        aligned_data[ticker] = aligned[['Date', 'Close_IDR']].reset_index(drop=True)
        print(f"  {ticker}: aligned to {len(aligned_data[ticker])} dates ({method})")

    return aligned_data


def prepare_chart_data(data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Prepare chart data with a zero-baseline point at H-1 (one day before earliest date).

    Args:
        data: Dict of ticker → DataFrame with 'Date' and 'Close_IDR'

    Returns:
        Dict of ticker → DataFrame with baseline point added at H-1
    """
    if not data:
        return {}

    all_dates = []
    for df in data.values():
        all_dates.extend(df['Date'].tolist())

    if not all_dates:
        return data

    min_date = min(all_dates)
    h_minus_one = min_date - timedelta(days=1)

    result_data = {}
    for ticker, df in data.items():
        df_prepared = df.copy()
        baseline_row = pd.DataFrame({
            'Date': [h_minus_one],
            'Close_IDR': [0.0],
        })
        df_prepared = pd.concat([baseline_row, df_prepared], ignore_index=True)
        df_prepared = df_prepared.sort_values('Date')
        result_data[ticker] = df_prepared

    print(f"  Added zero-baseline at H-1: {h_minus_one.strftime('%Y-%m-%d')}")
    return result_data
