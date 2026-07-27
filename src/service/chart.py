"""
Yahoo Finance Ticker Chart Visualizer
Generates static PNG and animated MP4 charts with IDR conversion.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import dates as mdates
from datetime import datetime, timedelta
import requests
import warnings
import os
from typing import List, Dict, Optional

# Suppress warnings
warnings.filterwarnings('ignore')

# Constants
DARK_BG = '#0f172a'
TEXT_COLOR = '#FFFFFF'
FONT_SIZE = 20
GRID_ALPHA = 0.15
FILL_ALPHA = 0.2
GLOW_ALPHA = 0.3
LEGEND_BG = '#1e293b'
LEGEND_BORDER = '#334155'
LEGEND_ALPHA = 0.8

# Color palette for tickers
TICKER_COLORS = [
    '#3b82f6',  # Blue
    '#10b981',  # Green
    '#ef4444',  # Red
    '#f59e0b',  # Yellow
    '#8b5cf6',  # Purple
    '#ec4899',  # Pink
]

def is_idr_ticker(ticker: str) -> bool:
    """
    Check if a ticker is already priced in IDR (Indonesian Rupiah).
    
    Indonesian tickers on Yahoo Finance are already in IDR:
    - ^JKSE (Jakarta Composite Index / IHSG)
    - ^IHSG (alternative name for Jakarta Composite Index)
    - *.JK (stocks listed on Jakarta Stock Exchange, e.g., BBCA.JK, BRI.JK)
    
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


def get_usd_to_idr_rate() -> float:
    """
    Get realtime USD to IDR exchange rate using yfinance (USDIDR=X).
    Fallback to a fixed rate if API fails.
    
    Returns:
        float: USD to IDR exchange rate
    """
    try:
        # Using yfinance for USD/IDR exchange rate
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

def fetch_ticker_data(tickers: List[str], period: str = "6mo") -> Dict[str, pd.DataFrame]:
    """
    Fetch historical data for multiple tickers from Yahoo Finance.
    
    Args:
        tickers: List of ticker symbols
        period: Time period (e.g., "6mo", "1y", "3mo")
    
    Returns:
        Dict mapping ticker symbol to DataFrame with 'Date', 'Close_IDR' columns
    """
    data_frames = {}
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            
            if hist.empty:
                print(f"No data for {ticker}")
                continue
                
            # Reset index to get Date as column
            hist = hist.reset_index()
            
            # Keep only necessary columns
            # Use generic name 'Close_Original' since some tickers are already in IDR
            hist = hist[['Date', 'Close']].copy()
            hist.columns = ['Date', 'Close_Original']
            
            data_frames[ticker] = hist
            print(f"Fetched {len(hist)} days of data for {ticker}")
            
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
    
    return data_frames

def convert_to_idr(data_frames: Dict[str, pd.DataFrame], usd_to_idr: float) -> Dict[str, pd.DataFrame]:
    """
    Convert prices to IDR and align dates.
    Ticklers already in IDR (e.g., ^JKSE, *.JK) are kept as-is.
    Other tickers (priced in USD) are multiplied by the exchange rate.
    
    Uses approximate date alignment (forward-fill with tolerance) to handle
    tickers with different trading calendars (e.g., crypto 7d/week vs stock exchange days).
    
    Args:
        data_frames: Dict of ticker DataFrames with 'Close_Original' column
        usd_to_idr: Exchange rate
    
    Returns:
        Dict of ticker DataFrames with 'Close_IDR' column
    """
    if not data_frames:
        return {}
    
    # Log which tickers are already in IDR
    for ticker in data_frames.keys():
        if is_idr_ticker(ticker):
            print(f"  {ticker}: already priced in IDR - skipping USD conversion")
        else:
            print(f"  {ticker}: priced in USD - will convert to IDR (rate: {usd_to_idr:,.2f})")
    
    # Normalize dates to date-only (strip time component) for all tickers
    normalized = {}
    for ticker, df in data_frames.items():
        df_copy = df.copy()
        df_copy['Date'] = pd.to_datetime(df_copy['Date']).dt.tz_localize(None).dt.normalize()
        # Drop duplicate dates (keep last)
        df_copy = df_copy.drop_duplicates(subset='Date', keep='last')
        df_copy = df_copy.sort_values('Date').reset_index(drop=True)
        normalized[ticker] = df_copy
    
    # Find common date RANGE (not exact intersection)
    min_dates = [df['Date'].min() for df in normalized.values()]
    max_dates = [df['Date'].max() for df in normalized.values()]
    range_start = max(min_dates)
    range_end = min(max_dates)
    
    if range_start > range_end:
        print("No overlapping date range found")
        return {}
    
    print(f"Common date range: {range_start.strftime('%Y-%m-%d')} to {range_end.strftime('%Y-%m-%d')}")
    
    # Use the ticker with the fewest dates as the reference calendar
    # (typically stock index — most restrictive trading calendar)
    ref_ticker = min(normalized.keys(), key=lambda t: len(normalized[t]))
    ref_df = normalized[ref_ticker]
    ref_dates = ref_df[(ref_df['Date'] >= range_start) & (ref_df['Date'] <= range_end)]
    common_dates = ref_dates['Date'].reset_index(drop=True)
    
    print(f"Using {ref_ticker} as reference calendar ({len(common_dates)} dates)")
    
    # Align all tickers to the reference dates using merge_asof (nearest within tolerance)
    aligned_data = {}
    for ticker, df in normalized.items():
        df_range = df[(df['Date'] >= range_start) & (df['Date'] <= range_end)].copy()
        df_range = df_range.sort_values('Date').reset_index(drop=True)
        
        # Use merge_asof to align to reference dates (tolerance of 3 days)
        ref_df_temp = pd.DataFrame({'Date': common_dates})
        aligned = pd.merge_asof(
            ref_df_temp, df_range,
            on='Date',
            direction='nearest',
            tolerance=pd.Timedelta('3D')
        )
        
        # Drop rows where no match was found
        aligned = aligned.dropna(subset=['Close_Original'])
        
        # Convert to IDR: skip for tickers already priced in IDR
        if is_idr_ticker(ticker):
            aligned['Close_IDR'] = aligned['Close_Original']  # Already in IDR
            print(f"  {ticker}: kept original IDR prices (no conversion)")
        else:
            aligned['Close_IDR'] = aligned['Close_Original'] * usd_to_idr
            print(f"  {ticker}: converted USD -> IDR (x{usd_to_idr:,.2f})")
        
        aligned_data[ticker] = aligned[['Date', 'Close_IDR']].reset_index(drop=True)
        print(f"  {ticker}: aligned to {len(aligned_data[ticker])} dates")
    
    return aligned_data

def prepare_chart_data(data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Prepare chart data with zero-baseline at H-1 date.
    
    Args:
        data: Dict of ticker DataFrames with 'Date' and 'Close_IDR' columns
    
    Returns:
        Dict of ticker DataFrames with baseline point added at H-1
    """
    if not data:
        return {}
    
    # Find the earliest date across all tickers
    all_dates = []
    for df in data.values():
        all_dates.extend(df['Date'].tolist())
    
    if not all_dates:
        return data
    
    min_date = min(all_dates)
    
    # Calculate H-1 (one day before the earliest date)
    h_minus_one = min_date - timedelta(days=1)
    
    # Prepare result with baseline
    result_data = {}
    for ticker, df in data.items():
        # Create a copy
        df_prepared = df.copy()
        
        # Add baseline point at H-1 with value 0
        baseline_row = pd.DataFrame({
            'Date': [h_minus_one],
            'Close_IDR': [0.0]
        })
        
        # Concatenate baseline with original data
        df_prepared = pd.concat([baseline_row, df_prepared], ignore_index=True)
        df_prepared = df_prepared.sort_values('Date')
        
        result_data[ticker] = df_prepared
    
    print(f"Added zero-baseline at H-1: {h_minus_one.strftime('%Y-%m-%d')}")
    return result_data

def format_idr_price(price: float) -> str:
    """
    Format IDR price with full nominal without abbreviations.
    
    Args:
        price: Price in IDR
    
    Returns:
        Formatted string (e.g., "Rp 2.304.299")
    """
    # Format with thousand separators using dots
    formatted = f"{price:,.0f}".replace(",", ".")
    return f"Rp {formatted}"

def format_currency_full(value: float) -> str:
    """
    Format currency with full nominal without abbreviations.
    Same as format_idr_price but more generic name.
    
    Args:
        value: Price in IDR
    
    Returns:
        Formatted string (e.g., "Rp 2.304.299")
    """
    return format_idr_price(value)

def format_y_axis_label(value: float) -> str:
    """
    Format Y-axis label with proper rounding and no trailing zeros.
    For large values, shows unit (juta/miliar) but with integer values.
    
    Args:
        value: Price in IDR
    
    Returns:
        Formatted string (e.g., "Rp 2 juta" not "Rp 2.0 juta")
    """
    if value >= 1_000_000_000:  # Miliar
        unit_value = value / 1_000_000_000
        # Round to nearest integer if close to integer, otherwise keep 1 decimal
        if abs(unit_value - round(unit_value)) < 0.01:
            unit_value = int(round(unit_value))
            return f"Rp {unit_value} Miliar"
        else:
            # Remove trailing zeros
            unit_str = f"{unit_value:.1f}".rstrip('0').rstrip('.')
            return f"Rp {unit_str} Miliar"
    elif value >= 1_000_000:  # Juta
        unit_value = value / 1_000_000
        # Round to nearest integer if close to integer
        if abs(unit_value - round(unit_value)) < 0.01:
            unit_value = int(round(unit_value))
            return f"Rp {unit_value} juta"
        else:
            # Remove trailing zeros
            unit_str = f"{unit_value:.1f}".rstrip('0').rstrip('.')
            return f"Rp {unit_str} juta"
    else:
        # Format with thousand separators
        formatted = f"{value:,.0f}".replace(",", ".")
        return f"Rp {formatted}"

def setup_date_axis(ax, dates: List[datetime]) -> None:
    """
    Configure the X-axis date formatting with intelligent month display.
    
    When dates span multiple months, major ticks are placed at month
    boundaries (showing month names), and minor ticks are placed at
    weekly intervals (showing day numbers). This avoids repeating the
    same month name for every tick within that month.
    
    When all dates are within the same month, only day numbers are shown.
    
    Args:
        ax: matplotlib Axes object
        dates: List of datetime objects for the chart data
    """
    if not dates:
        return

    min_date = min(dates)
    max_date = max(dates)
    same_year = min_date.year == max_date.year
    same_month = same_year and min_date.month == max_date.month

    if same_month:
        # All dates within same month: use weekly ticks with day numbers
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d"))
        ax.xaxis.set_minor_locator(mdates.DayLocator())
        ax.xaxis.set_minor_formatter(plt.FuncFormatter(lambda x, pos: ""))
        return

    # Multiple months: major ticks at month boundaries, minor at weekly
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    if same_year:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    # Minor ticks: weekly (Mondays) with day numbers
    ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax.xaxis.set_minor_formatter(plt.FuncFormatter(
        lambda x, pos: mdates.num2date(x).strftime("%d") if pos is not None else ""
    ))

    # Style minor tick labels smaller and dimmer after they are rendered
    # (done via tick_params in the calling function)

def calculate_performance(df: pd.DataFrame) -> float:
    """
    Calculate percentage performance from first to last value.
    
    Args:
        df: DataFrame with 'Close_IDR' column
    
    Returns:
        Percentage change
    """
    if len(df) < 2:
        return 0.0
    
    first = df['Close_IDR'].iloc[0]
    last = df['Close_IDR'].iloc[-1]
    
    return ((last - first) / first) * 100

def normalize_to_pct_change(prices: List[float]) -> List[float]:
    """
    Normalize a list of prices to percentage change from the first value.
    
    Args:
        prices: List of absolute prices
    
    Returns:
        List of percentage changes (e.g., [0.0, 2.5, -1.3, ...])
    """
    if not prices:
        return []
    base = prices[0]
    if base == 0:
        # Use first non-zero value as base
        for p in prices:
            if p > 0:
                base = p
                break
    if base == 0:
        return [0.0] * len(prices)
    return [((p - base) / base) * 100 for p in prices]

def create_static_chart(
    data: Dict[str, pd.DataFrame],
    output_path: str = "output.png",
    title_lines: Optional[List[str]] = None
) -> None:
    """
    Create static landscape chart (1920x1080).
    
    Args:
        data: Dict of ticker DataFrames with 'Date' and 'Close_IDR'
        output_path: Path to save PNG
        title_lines: Custom title lines (3 lines)
    """
    if not data:
        print("No data to plot")
        return
    
    # Prepare data
    tickers = list(data.keys())
    dates = data[tickers[0]]['Date'].tolist()
    
    # Create figure
    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    
    # Set background color
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)
    
    # Plot each ticker with glow effect (normalized to % change)
    for i, (ticker, df) in enumerate(data.items()):
        color = TICKER_COLORS[i % len(TICKER_COLORS)]
        prices = df['Close_IDR'].tolist()
        pct_prices = normalize_to_pct_change(prices)
        pct_change = pct_prices[-1] if pct_prices else 0
        
        # Glow effect: thicker line with alpha
        ax.plot(dates, pct_prices,
                color=color,
                linewidth=8,
                alpha=GLOW_ALPHA,
                zorder=1)
        
        # Main line
        line = ax.plot(dates, pct_prices,
                      color=color,
                      linewidth=3,
                      label=ticker,
                      zorder=2)
        
        # Fill under line
        ax.fill_between(dates, pct_prices,
                       alpha=FILL_ALPHA,
                       color=color,
                       zorder=0)
        
        # Last value marker
        last_date = dates[-1]
        last_pct = pct_prices[-1]
        last_price = prices[-1]
        ax.scatter([last_date], [last_pct],
                  color=color,
                  s=200,
                  zorder=3,
                  edgecolor='white',
                  linewidth=2)
        
        # Last value annotation: actual price + % change
        ax.annotate(f"{format_currency_full(last_price)}\n({pct_change:+.1f}%)",
                   xy=(last_date, last_pct),
                   xytext=(10, 0),
                   textcoords='offset points',
                   color=color,
                   fontsize=FONT_SIZE + 2,
                   fontweight='bold',
                   va='center')
    
    # Calculate performances for title coloring
    performances = {ticker: calculate_performance(df)
                   for ticker, df in data.items()}
    best_ticker = max(performances.items(), key=lambda x: x[1])
    worst_ticker = min(performances.items(), key=lambda x: x[1])
    
    if title_lines is None:
        date_range_str = f"{dates[0].strftime('%d %b %Y')} - {dates[-1].strftime('%d %b %Y')}"
        
        title_lines = [
            ', '.join([f'${t}' for t in tickers]),
            date_range_str,
            f'{best_ticker[0]} Leading (+{best_ticker[1]:.1f}%)'
        ]
    
    # Line 1: all tickers in white
    ax.text(0.5, 1.06, '  '.join([f'${t}' for t in tickers]),
            color=TEXT_COLOR, fontsize=FONT_SIZE + 5, fontweight='bold',
            ha='center', va='bottom',
            transform=ax.transAxes, clip_on=False)
    
    # Line 2: date range
    ax.text(0.5, 1.03, title_lines[1], color=TEXT_COLOR,
            fontsize=FONT_SIZE + 4,
            ha='center', va='bottom',
            transform=ax.transAxes, clip_on=False)
    
    # Line 3: high (green) and low (red)
    high_text = f"[{best_ticker[0]} +{best_ticker[1]:.1f}%]"
    ax.text(0.42, 1.005, high_text, color='#10b981',
            fontsize=FONT_SIZE + 2, fontweight='bold',
            ha='right', va='bottom',
            transform=ax.transAxes, clip_on=False)
    
    if len(tickers) >= 2:
        low_text = f"[{worst_ticker[0]} {worst_ticker[1]:+.1f}%]"
        ax.text(0.58, 1.005, low_text, color='#ef4444',
                fontsize=FONT_SIZE + 2, fontweight='bold',
                ha='left', va='bottom',
                transform=ax.transAxes, clip_on=False)
    
    # Configure axes
    ax.tick_params(colors=TEXT_COLOR, labelsize=FONT_SIZE, which='major')
    ax.tick_params(axis='x', colors=TEXT_COLOR, labelsize=14, which='minor', labelrotation=45)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.xaxis.label.set_color(TEXT_COLOR)
    
    # Format Y-axis as percentage change
    ax.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda x, pos: f"{x:+.1f}%"
    ))
    
    # Smart date formatting for X-axis (month shown once, days on minor ticks)
    setup_date_axis(ax, dates)
    
    # Rotate date labels for readability
    plt.setp(ax.get_xticklabels(which='major'), rotation=45, ha='right')
    
    # Grid
    ax.grid(True, alpha=GRID_ALPHA, linestyle='--', color=TEXT_COLOR)
    
    # Spine styling
    for spine in ax.spines.values():
        spine.set_color(TEXT_COLOR)
        spine.set_alpha(0.3)
        spine.set_linewidth(0.5)
    
    # Legend with dark glass style
    legend = ax.legend(facecolor=LEGEND_BG, 
                      edgecolor=LEGEND_BORDER,
                      fontsize=FONT_SIZE,
                      labelcolor=TEXT_COLOR,
                      framealpha=LEGEND_ALPHA,
                      loc='upper left',
                      borderpad=1)
    legend.get_frame().set_linewidth(1)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_path, 
               dpi=100, 
               facecolor=fig.get_facecolor(),
               bbox_inches='tight')
    print(f"Static chart saved to {output_path}")
    plt.close()

def create_animated_chart(
    data: Dict[str, pd.DataFrame],
    output_path: str = "output.mp4",
    fps: int = 30
) -> None:
    """
    Create animated vertical chart (1080x1920) for video.
    
    The X-axis is dynamic: the start (left edge) is frozen at the first
    date, while the right edge expands to follow the chart's progress.
    This creates a growing view that always shows from the beginning
    up to the current data point.
    
    Args:
        data: Dict of ticker DataFrames with 'Date' and 'Close_IDR'
        output_path: Path to save MP4
        fps: Frames per second
    """
    if not data:
        print("No data to animate")
        return
    
    # Animation speed/duration settings
    frames_per_point = 5    # Each data point shown for ~0.2s (5 frames at 24fps = 0.208s), semakin tinggi = lama, semakin dikit = cepet
    hold_seconds = 1.5      # Hold final state at end for viewer to absorb
    x_padding_days = 2      # Extra days of padding on the right edge
    
    # Prepare data
    tickers = list(data.keys())
    dates = data[tickers[0]]['Date'].tolist()
    total_dates = len(dates)
    
    # Pre-compute percentage change data for plotting
    pct_data = {}
    for ticker, df in data.items():
        prices = df['Close_IDR'].tolist()
        pct_data[ticker] = normalize_to_pct_change(prices)
    
    # Pre-compute full range for axis calculations
    full_x_range = (dates[-1] - dates[0]).days
    x_padding = timedelta(days=x_padding_days)
    
    # Pre-compute full Y-axis limits from all data
    all_pcts = []
    for pct_list in pct_data.values():
        all_pcts.extend(pct_list)
    pct_min_full = min(all_pcts)
    pct_max_full = max(all_pcts)
    pct_range_full = pct_max_full - pct_min_full if pct_max_full != pct_min_full else 1
    y_margin = pct_range_full * 0.15  # 15% margin for dynamic Y
    
    # Create figure with vertical orientation
    fig, ax = plt.subplots(figsize=(10.8, 19.2), dpi=100)
    
    # Set background color
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)
    
    # Initialize lines, markers
    lines = []
    markers = []
    
    for i, (ticker, df) in enumerate(data.items()):
        color = TICKER_COLORS[i % len(TICKER_COLORS)]
        
        # Initialize empty lines
        line, = ax.plot([], [], color=color, linewidth=4, label=ticker, zorder=2)
        glow_line, = ax.plot([], [], color=color, linewidth=10, alpha=GLOW_ALPHA, zorder=1)
        marker = ax.scatter([], [], color=color, s=200, zorder=3,
                           edgecolor='white', linewidth=2)
        
        lines.append((line, glow_line))
        markers.append(marker)
    
    # ---- Title text objects ----
    # Line 1: single white text for all tickers
    title_line1_text = ax.text(0.5, 1.06, '', color=TEXT_COLOR,
                               fontsize=FONT_SIZE + 5,
                               fontweight='bold',
                               ha='center', va='bottom',
                               transform=ax.transAxes,
                               clip_on=False, visible=False, zorder=10)
    
    # Line 2: date (white)
    title_line2_text = ax.text(0.5, 1.03, '', color=TEXT_COLOR,
                               fontsize=FONT_SIZE + 4,
                               ha='center', va='bottom',
                               transform=ax.transAxes,
                               clip_on=False, visible=False, zorder=10)
    
    # Line 3: high (green) and low (red)
    title_line3_high = ax.text(0.42, 1.005, '', color='#10b981',
                               fontsize=FONT_SIZE + 2,
                               fontweight='bold',
                               ha='right', va='bottom',
                               transform=ax.transAxes,
                               clip_on=False, visible=False, zorder=10)
    
    title_line3_low = ax.text(0.58, 1.005, '', color='#ef4444',
                              fontsize=FONT_SIZE + 2,
                              fontweight='bold',
                              ha='left', va='bottom',
                              transform=ax.transAxes,
                              clip_on=False, visible=False, zorder=10)
    
    # ---- Floating badges (at end of each ticker line) ----
    badges = []
    for i, ticker in enumerate(tickers):
        tc = TICKER_COLORS[i % len(TICKER_COLORS)]
        badge = ax.text(0, 0, '',
                        color=tc, fontsize=FONT_SIZE,
                        ha='center', va='bottom',
                        zorder=4,
                        visible=False)
        badges.append(badge)
    
    # --- Configure static axes styles ---
    ax.tick_params(colors=TEXT_COLOR, labelsize=FONT_SIZE, which='major')
    ax.tick_params(axis='x', colors=TEXT_COLOR, labelsize=14, which='minor', labelrotation=45)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.xaxis.label.set_color(TEXT_COLOR)
    
    # Format Y-axis as percentage change
    ax.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda x, pos: f"{x:+.1f}%"
    ))
    
    # Grid
    ax.grid(True, alpha=GRID_ALPHA, linestyle='--', color=TEXT_COLOR)
    
    # Spine styling
    for spine in ax.spines.values():
        spine.set_color(TEXT_COLOR)
        spine.set_alpha(0.3)
        spine.set_linewidth(0.5)
    
    # Legend
    legend = ax.legend(facecolor=LEGEND_BG,
                      edgecolor=LEGEND_BORDER,
                      fontsize=FONT_SIZE,
                      labelcolor=TEXT_COLOR,
                      framealpha=LEGEND_ALPHA,
                      loc='upper left',
                      borderpad=1)
    legend.get_frame().set_linewidth(1)
    
    # Adjust layout with padding to prevent clipping
    plt.subplots_adjust(
        top=0.88,      # More space at top for 3-line title
        bottom=0.12,   # More space at bottom for X-axis labels
        left=0.18,     # More space at left for Y-axis labels
        right=0.82     # More space at right for badge panel
    )
    
    def _compute_xlim(current_idx: int):
        """
        Compute dynamic X-axis limits based on the current animation position.
        
        Strategy: The left edge is always frozen at the start date (dates[0]).
        The right edge dynamically follows the current frame's date + padding,
        expanding from left to right as the chart draws forward.
        On the final frame, it shows the full date range with padding.
        """
        current_date = dates[current_idx]
        left_edge = dates[0]  # Always frozen at start
        
        if current_idx < total_dates - 1:
            right_edge = current_date + x_padding
        else:
            # Final frame: show full range with padding
            right_edge = dates[-1] + x_padding
        
        return left_edge, right_edge
    
    def _update_axis_dates(current_idx: int):
        """Update X-axis limits and re-configure date formatting."""
        left_edge, right_edge = _compute_xlim(current_idx)
        ax.set_xlim(left_edge, right_edge)
        
        # Build a list of dates currently in the visible range for tick setup
        visible_dates = [d for d in dates if left_edge <= d <= right_edge]
        if visible_dates:
            setup_date_axis(ax, visible_dates)
    
    def _update_axis_y(current_idx: int):
        """Update Y-axis limits to fit visible data with smooth margins."""
        visible_pcts = []
        for pct_list in pct_data.values():
            if current_idx < len(pct_list):
                visible_pcts.extend(pct_list[:current_idx + 1])
        
        if not visible_pcts:
            return
        
        v_min = min(visible_pcts)
        v_max = max(visible_pcts)
        v_range = v_max - v_min if v_max != v_min else 1
        margin = max(v_range * 0.2, y_margin * 0.3)  # at least some margin
        ax.set_ylim(v_min - margin, v_max + margin)
    
    # Animation initialization
    def init():
        # Start with a narrow X-axis that will expand dynamically
        initial_right = dates[0] + timedelta(days=max(int(full_x_range * 0.05), 3))
        ax.set_xlim(dates[0], initial_right)
        
        # Set Y-axis limits based on full range initially
        ax.set_ylim(pct_min_full - y_margin, pct_max_full + y_margin)
        
        # Setup initial date axis
        setup_date_axis(ax, dates[:4])  # few dates to start
        
        # Hide title and badge elements initially
        title_line1_text.set_visible(False)
        title_line2_text.set_visible(False)
        title_line3_high.set_visible(False)
        title_line3_low.set_visible(False)
        for badge in badges:
            badge.set_visible(False)
        
        # Return all animated artists
        artists = [item for pair in lines for item in pair] + markers + badges
        artists += [title_line1_text, title_line2_text, title_line3_high, title_line3_low]
        return artists
    
    # Animation update function
    def update(frame):
        current_idx = min(frame // frames_per_point, len(dates) - 1)
        current_date = dates[current_idx]
        
        # Update dynamic X-axis and Y-axis
        _update_axis_dates(current_idx)
        _update_axis_y(current_idx)
        
        # Calculate performance for each ticker at current frame
        performances = {}
        current_prices_dict = {}
        
        for i, (ticker, df) in enumerate(data.items()):
            current_prices = df['Close_IDR'].tolist()[:current_idx + 1]
            if current_prices:
                current_price = current_prices[-1]
                current_prices_dict[ticker] = current_price
                
                # Calculate percentage change from baseline (first non-zero value)
                non_zero_prices = [p for p in current_prices if p > 0]
                if non_zero_prices:
                    first_price = non_zero_prices[0]
                    percent_change = ((current_price - first_price) / first_price) * 100
                    performances[ticker] = percent_change
        
        # Update each line
        for i, (ticker, df) in enumerate(data.items()):
            line, glow_line = lines[i]
            marker = markers[i]
            badge = badges[i]
            
            # Get data up to current frame
            current_dates = dates[:current_idx + 1]
            current_pcts = pct_data[ticker][:current_idx + 1]
            current_prices = df['Close_IDR'].tolist()[:current_idx + 1]
            
            # Update lines (using percentage change)
            line.set_data(current_dates, current_pcts)
            glow_line.set_data(current_dates, current_pcts)
            
            # Update marker and floating badge
            if current_pcts:
                current_pct = current_pcts[-1]
                current_price = current_prices[-1]
                marker.set_offsets([[current_date, current_pct]])
                
                # Update floating badge at line end
                if ticker in performances:
                    percent_change = performances[ticker]
                    price_str = format_currency_full(current_price)
                    percent_str = f"{percent_change:+.1f}%"
                    badge.set_text(f"{price_str}\n{percent_str}")
                    badge.set_position((current_date, current_pct + 0.5))
                    badge.set_visible(True)
                else:
                    badge.set_visible(False)
        
        # Update title with dynamic overlay (3 lines)
        date_str = current_date.strftime('%d %b %Y')
        
        # Find best and worst performers
        best_ticker = None
        worst_ticker = None
        if performances:
            best_ticker = max(performances.items(), key=lambda x: x[1])
            worst_ticker = min(performances.items(), key=lambda x: x[1])
        
        # Update title line 1: all tickers in white
        title_line1_text.set_text('  '.join([f'${t}' for t in tickers]))
        title_line1_text.set_visible(True)
        
        # Update title line 2: date
        title_line2_text.set_text(date_str)
        title_line2_text.set_visible(True)
        
        # Update title line 3: high (green) and low (red)
        if best_ticker:
            best_symbol, best_percent = best_ticker
            title_line3_high.set_text(f"[{best_symbol} +{best_percent:.1f}%]")
            title_line3_high.set_visible(True)
        else:
            title_line3_high.set_visible(False)
        
        if worst_ticker and len(tickers) >= 2:
            worst_symbol, worst_percent = worst_ticker
            title_line3_low.set_text(f"[{worst_symbol} {worst_percent:+.1f}%]")
            title_line3_low.set_visible(True)
        else:
            title_line3_low.set_visible(False)
        
        # Return all animated artists
        artists = [item for pair in lines for item in pair] + markers + badges
        artists += [title_line1_text, title_line2_text, title_line3_high, title_line3_low]
        return artists
    
    # Calculate total frames: animation frames + hold frames at the end
    anim_frames = len(dates) * frames_per_point
    hold_frames = int(fps * hold_seconds)
    total_frames = anim_frames + hold_frames
    total_seconds = total_frames / fps
    
    print(f"Animation: {len(dates)} data points x {frames_per_point} frames/point = {anim_frames} anim frames")
    print(f"  + {hold_frames} hold frames ({hold_seconds}s)")
    print(f"  = {total_frames} total frames ({total_seconds:.1f}s at {fps}fps)")
    print(f"  X-axis: dynamic expanding (start frozen, right edge follows chart)")
    
    # Create animation (blit=False required for dynamic axis limits)
    anim = animation.FuncAnimation(fig, update,
                                  frames=total_frames,
                                  init_func=init,
                                  blit=False,
                                  interval=1000/fps)
    
    # Save animation
    writer = animation.FFMpegWriter(fps=fps)
    anim.save(output_path, writer=writer)
    print(f"Animated chart saved to {output_path}")
    plt.close()

def main():
    """Main function to demonstrate the chart generation."""
    print("Yahoo Finance Ticker Chart Visualizer")
    print("=" * 50)
    
    # Step 1: Get exchange rate
    usd_to_idr = get_usd_to_idr_rate()
    
    # Step 2: Define tickers
    tickers = ['BTC-USD', 'GC=F', '^JKSE']
    
    # Step 3: Fetch data
    print(f"\nFetching data for {tickers}...")
    raw_data = fetch_ticker_data(tickers, period="6mo")
    
    if not raw_data:
        print("No data fetched. Exiting.")
        return
    
    # Step 4: Convert to IDR and align
    print("\nConverting to IDR and aligning dates...")
    idr_data = convert_to_idr(raw_data, usd_to_idr)
    
    if not idr_data:
        print("No aligned data. Exiting.")
        return
    
    # Step 5: Create static chart
    print("\nCreating static chart...")
    create_static_chart(idr_data, "static_chart.png")
    
    # Step 6: Create animated chart
    print("\nCreating animated chart...")
    try:
        create_animated_chart(idr_data, "animated_chart.mp4", fps=24)
    except Exception as e:
        print(f"Error creating animation (may need ffmpeg): {e}")
        print("Install ffmpeg: https://ffmpeg.org/download.html")
    
    print("\nDone!")

if __name__ == "__main__":
    main()
