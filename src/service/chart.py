"""
Chart visualization module.
Generates static PNG (line chart) and animated MP4 charts with IDR conversion.

Public API (called by controller.py):
    - generate_png_chart(df_dict, output_path)
    - generate_mp4_animation(df_dict, output_path)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server/CLI use
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import dates as mdates
from datetime import datetime, timedelta
import os
import warnings
from typing import List, Dict, Optional

# Suppress warnings
warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# Visual constants
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def clean_ticker_symbol(ticker: str) -> str:
    """Remove .JK suffix from ticker for display purposes only."""
    return ticker.replace('.JK', '')


def format_profit_percentage(value: float) -> str:
    """
    Format a profit/return value as a percentage string.

    - Positive values get a '+' prefix: '+1.25%'
    - Negative values keep the '-' prefix: '-1.25%'
    - Zero is displayed without a sign: '0.00%'
    """
    if value > 0:
        return f"+{value:.2f}%"
    else:
        return f"{value:.2f}%"

def format_idr_price(price: float) -> str:
    """Format IDR price with full nominal (e.g., 'Rp 2.304.299')."""
    formatted = f"{price:,.0f}".replace(",", ".")
    return f"Rp {formatted}"


def format_currency_full(value: float) -> str:
    """Alias for format_idr_price."""
    return format_idr_price(value)


def format_y_axis_label(value: float) -> str:
    """Format Y-axis label with unit (juta/miliar) for large values."""
    if value >= 1_000_000_000:
        unit_value = value / 1_000_000_000
        if abs(unit_value - round(unit_value)) < 0.01:
            unit_value = int(round(unit_value))
            return f"Rp {unit_value} Miliar"
        else:
            unit_str = f"{unit_value:.1f}".rstrip('0').rstrip('.')
            return f"Rp {unit_str} Miliar"
    elif value >= 1_000_000:
        unit_value = value / 1_000_000
        if abs(unit_value - round(unit_value)) < 0.01:
            unit_value = int(round(unit_value))
            return f"Rp {unit_value} juta"
        else:
            unit_str = f"{unit_value:.1f}".rstrip('0').rstrip('.')
            return f"Rp {unit_str} juta"
    else:
        formatted = f"{value:,.0f}".replace(",", ".")
        return f"Rp {formatted}"


def normalize_to_pct_change(prices: List[float]) -> List[float]:
    """Normalize prices to percentage change from the first value."""
    if not prices:
        return []
    base = prices[0]
    if base == 0:
        for p in prices:
            if p > 0:
                base = p
                break
    if base == 0:
        return [0.0] * len(prices)
    return [((p - base) / base) * 100 for p in prices]


def calculate_performance(df: pd.DataFrame) -> float:
    """Calculate percentage performance from first to last Close_IDR value."""
    if len(df) < 2:
        return 0.0
    first = df['Close_IDR'].iloc[0]
    last = df['Close_IDR'].iloc[-1]
    if first == 0:
        return 0.0
    return ((last - first) / first) * 100


def setup_date_axis(ax, dates: List[datetime]) -> None:
    """
    Configure X-axis date formatting — month-focused display.

    Rules:
    - Single month: major ticks at month start with month name, minor at weekly.
    - Multi-month within same year: major ticks monthly (Jan, Feb, Mar ...).
    - Multi-year: major ticks monthly with year on January (Jan 26, Feb 26 ...).
    - Never show day-of-month on major ticks (only as minor when zoomed to 1 month).
    """
    if not dates:
        return

    min_date = min(dates)
    max_date = max(dates)
    same_year = min_date.year == max_date.year
    same_month = same_year and min_date.month == max_date.month

    # Always use monthly major ticks
    ax.xaxis.set_major_locator(mdates.MonthLocator())

    if same_month:
        # Single month: show month name on the 1st, minor ticks at week boundaries
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
        ax.xaxis.set_minor_formatter(plt.FuncFormatter(lambda x, pos: ""))
    elif same_year:
        # Multi-month, same year: show month abbreviations only
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
        ax.xaxis.set_minor_formatter(plt.FuncFormatter(lambda x, pos: ""))
    else:
        # Multi-year: show month + 2-digit year (e.g. "Nov 25", "Jan 26")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
        ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
        ax.xaxis.set_minor_formatter(plt.FuncFormatter(lambda x, pos: ""))


# ---------------------------------------------------------------------------
# Public API — Static chart (PNG)
# ---------------------------------------------------------------------------

def create_static_chart(
    data: Dict[str, pd.DataFrame],
    output_path: str = "output.png",
    title_lines: Optional[List[str]] = None,
) -> None:
    """
    Create a static landscape chart (1920×1080, 300 DPI) comparing multiple tickers.

    Args:
        data:        Dict of ticker → DataFrame with 'Date' and 'Close_IDR'
        output_path: Path to save the PNG file
        title_lines: Optional 3-element list of custom title strings
    """
    if not data:
        print("No data to plot")
        return

    tickers = list(data.keys())
    dates = data[tickers[0]]['Date'].tolist()

    # Create figure at 1920×1080 effective pixels (19.2×10.8 inches × 100 DPI)
    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)

    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)

    # Plot each ticker
    for i, (ticker, df) in enumerate(data.items()):
        color = TICKER_COLORS[i % len(TICKER_COLORS)]
        prices = df['Close_IDR'].tolist()
        pct_prices = normalize_to_pct_change(prices)
        pct_change = pct_prices[-1] if pct_prices else 0
        display_name = clean_ticker_symbol(ticker)

        # Glow effect
        ax.plot(dates, pct_prices, color=color, linewidth=8, alpha=GLOW_ALPHA, zorder=1)
        # Main line
        ax.plot(dates, pct_prices, color=color, linewidth=3, label=display_name, zorder=2)
        # Fill under line
        ax.fill_between(dates, pct_prices, alpha=FILL_ALPHA, color=color, zorder=0)

        # Last value marker
        last_date = dates[-1]
        last_pct = pct_prices[-1]
        last_price = prices[-1]
        ax.scatter([last_date], [last_pct], color=color, s=200, zorder=3,
                   edgecolor='white', linewidth=2)

        # Annotation: actual price + % change
        ax.annotate(
            f"{format_currency_full(last_price)}\n({format_profit_percentage(pct_change)})",
            xy=(last_date, last_pct), xytext=(10, 0),
            textcoords='offset points', color=color,
            fontsize=FONT_SIZE + 2, fontweight='bold', va='center',
        )

    # Performance summary
    performances = {t: calculate_performance(d) for t, d in data.items()}
    best_ticker = max(performances.items(), key=lambda x: x[1])
    worst_ticker = min(performances.items(), key=lambda x: x[1])

    if title_lines is None:
        date_range_str = f"{dates[0].strftime('%d %b %Y')} - {dates[-1].strftime('%d %b %Y')}"
        clean_tickers = [clean_ticker_symbol(t) for t in tickers]
        title_lines = [
            ', '.join(clean_tickers),
            date_range_str,
            f'{clean_ticker_symbol(best_ticker[0])} Leading (+{best_ticker[1]:.1f}%)',
        ]

    # Title line 1: all tickers
    clean_tickers_display = [clean_ticker_symbol(t) for t in tickers]
    ax.text(0.5, 1.06, '  '.join(clean_tickers_display),
            color=TEXT_COLOR, fontsize=FONT_SIZE + 5, fontweight='bold',
            ha='center', va='bottom', transform=ax.transAxes, clip_on=False)

    # Title line 2: date range
    ax.text(0.5, 1.03, title_lines[1], color=TEXT_COLOR,
            fontsize=FONT_SIZE + 4, ha='center', va='bottom',
            transform=ax.transAxes, clip_on=False)

    # Title line 3: best / worst
    high_text = f"[{clean_ticker_symbol(best_ticker[0])} {format_profit_percentage(best_ticker[1])}]"
    ax.text(0.42, 1.005, high_text, color='#10b981',
            fontsize=FONT_SIZE + 2, fontweight='bold',
            ha='right', va='bottom', transform=ax.transAxes, clip_on=False)

    if len(tickers) >= 2:
        low_text = f"[{clean_ticker_symbol(worst_ticker[0])} {format_profit_percentage(worst_ticker[1])}]"
        ax.text(0.58, 1.005, low_text, color='#ef4444',
                fontsize=FONT_SIZE + 2, fontweight='bold',
                ha='left', va='bottom', transform=ax.transAxes, clip_on=False)

    # Axes styling
    ax.tick_params(colors=TEXT_COLOR, labelsize=FONT_SIZE, which='major')
    ax.tick_params(axis='x', colors=TEXT_COLOR, labelsize=14, which='minor', labelrotation=45)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.xaxis.label.set_color(TEXT_COLOR)

    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, pos: f"{x:+.1f}%"))
    setup_date_axis(ax, dates)
    plt.setp(ax.get_xticklabels(which='major'), rotation=45, ha='right')

    ax.grid(True, alpha=GRID_ALPHA, linestyle='--', color=TEXT_COLOR)

    for spine in ax.spines.values():
        spine.set_color(TEXT_COLOR)
        spine.set_alpha(0.3)
        spine.set_linewidth(0.5)

    legend = ax.legend(facecolor=LEGEND_BG, edgecolor=LEGEND_BORDER,
                       fontsize=FONT_SIZE, labelcolor=TEXT_COLOR,
                       framealpha=LEGEND_ALPHA, loc='upper left', borderpad=1)
    legend.get_frame().set_linewidth(1)

    plt.tight_layout()

    plt.savefig(output_path, dpi=100, facecolor=fig.get_facecolor(), bbox_inches='tight')
    print(f"Static chart saved to {output_path}")
    plt.close()


def generate_png_chart(df_dict: Dict[str, pd.DataFrame], output_path: str) -> None:
    """
    Generate a static PNG comparison chart.

    This is the public entry-point called by controller.py.

    Args:
        df_dict:     Dict of ticker → DataFrame with 'Date' and 'Close_IDR' columns
        output_path: File path where the PNG will be saved
    """
    create_static_chart(df_dict, output_path)


# ---------------------------------------------------------------------------
# Public API — Animated chart (MP4)
# ---------------------------------------------------------------------------

def create_animated_chart(
    data: Dict[str, pd.DataFrame],
    output_path: str = "output.mp4",
    fps: int = 30,
) -> None:
    """
    Create an animated vertical chart (1080×1920) as MP4 video.

    The X-axis is dynamic: the start (left edge) is frozen at the first
    date, while the right edge expands to follow the chart's progress.

    Args:
        data:        Dict of ticker → DataFrame with 'Date' and 'Close_IDR'
        output_path: Path to save the MP4
        fps:         Frames per second
    """
    if not data:
        print("No data to animate")
        return

    frames_per_point = 5
    hold_seconds = 1.5
    x_padding_days = 2

    tickers = list(data.keys())
    dates = data[tickers[0]]['Date'].tolist()
    total_dates = len(dates)

    # Pre-compute percentage data
    pct_data: Dict[str, List[float]] = {}
    for ticker, df in data.items():
        pct_data[ticker] = normalize_to_pct_change(df['Close_IDR'].tolist())

    full_x_range = (dates[-1] - dates[0]).days
    x_padding = timedelta(days=x_padding_days)

    all_pcts = [p for lst in pct_data.values() for p in lst]
    pct_min_full = min(all_pcts)
    pct_max_full = max(all_pcts)
    pct_range_full = pct_max_full - pct_min_full if pct_max_full != pct_min_full else 1
    y_margin = pct_range_full * 0.15

    # Figure: vertical orientation
    fig, ax = plt.subplots(figsize=(10.8, 19.2), dpi=100)
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)

    # Artists
    lines = []
    markers = []
    for i, ticker in enumerate(tickers):
        color = TICKER_COLORS[i % len(TICKER_COLORS)]
        display_name = clean_ticker_symbol(ticker)
        line, = ax.plot([], [], color=color, linewidth=4, label=display_name, zorder=2)
        glow_line, = ax.plot([], [], color=color, linewidth=10, alpha=GLOW_ALPHA, zorder=1)
        marker = ax.scatter([], [], color=color, s=200, zorder=3,
                            edgecolor='white', linewidth=2)
        lines.append((line, glow_line))
        markers.append(marker)

    # Title objects
    title_line1_text = ax.text(0.5, 1.06, '', color=TEXT_COLOR,
                               fontsize=FONT_SIZE + 5, fontweight='bold',
                               ha='center', va='bottom', transform=ax.transAxes,
                               clip_on=False, visible=False, zorder=10)
    title_line2_text = ax.text(0.5, 1.03, '', color=TEXT_COLOR,
                               fontsize=FONT_SIZE + 4, ha='center', va='bottom',
                               transform=ax.transAxes, clip_on=False, visible=False, zorder=10)
    title_line3_high = ax.text(0.42, 1.005, '', color='#10b981',
                               fontsize=FONT_SIZE + 2, fontweight='bold',
                               ha='right', va='bottom', transform=ax.transAxes,
                               clip_on=False, visible=False, zorder=10)
    title_line3_low = ax.text(0.58, 1.005, '', color='#ef4444',
                              fontsize=FONT_SIZE + 2, fontweight='bold',
                              ha='left', va='bottom', transform=ax.transAxes,
                              clip_on=False, visible=False, zorder=10)

    # Floating badges
    badges = []
    for i, ticker in enumerate(tickers):
        tc = TICKER_COLORS[i % len(TICKER_COLORS)]
        badge = ax.text(0, 0, '', color=tc, fontsize=FONT_SIZE,
                        ha='center', va='bottom', zorder=4, visible=False)
        badges.append(badge)

    # Static axis styling
    ax.tick_params(colors=TEXT_COLOR, labelsize=FONT_SIZE, which='major')
    ax.tick_params(axis='x', colors=TEXT_COLOR, labelsize=14, which='minor', labelrotation=45)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, pos: f"{x:+.1f}%"))
    ax.grid(True, alpha=GRID_ALPHA, linestyle='--', color=TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_color(TEXT_COLOR)
        spine.set_alpha(0.3)
        spine.set_linewidth(0.5)
    legend = ax.legend(facecolor=LEGEND_BG, edgecolor=LEGEND_BORDER,
                       fontsize=FONT_SIZE, labelcolor=TEXT_COLOR,
                       framealpha=LEGEND_ALPHA, loc='upper left', borderpad=1)
    legend.get_frame().set_linewidth(1)
    plt.subplots_adjust(top=0.88, bottom=0.12, left=0.18, right=0.82)

    # --- Helpers ---
    def _compute_xlim(current_idx: int):
        current_date = dates[current_idx]
        left_edge = dates[0]
        if current_idx < total_dates - 1:
            right_edge = current_date + x_padding
        else:
            right_edge = dates[-1] + x_padding
        return left_edge, right_edge

    def _update_axis_dates(current_idx: int):
        left_edge, right_edge = _compute_xlim(current_idx)
        ax.set_xlim(left_edge, right_edge)
        visible_dates = [d for d in dates if left_edge <= d <= right_edge]
        if visible_dates:
            setup_date_axis(ax, visible_dates)

    def _update_axis_y(current_idx: int):
        visible_pcts = []
        for pct_list in pct_data.values():
            if current_idx < len(pct_list):
                visible_pcts.extend(pct_list[:current_idx + 1])
        if not visible_pcts:
            return
        v_min = min(visible_pcts)
        v_max = max(visible_pcts)
        v_range = v_max - v_min if v_max != v_min else 1
        margin = max(v_range * 0.2, y_margin * 0.3)
        ax.set_ylim(v_min - margin, v_max + margin)

    # --- Animation callbacks ---
    def init():
        initial_right = dates[0] + timedelta(days=max(int(full_x_range * 0.05), 3))
        ax.set_xlim(dates[0], initial_right)
        ax.set_ylim(pct_min_full - y_margin, pct_max_full + y_margin)
        setup_date_axis(ax, dates[:4])

        title_line1_text.set_visible(False)
        title_line2_text.set_visible(False)
        title_line3_high.set_visible(False)
        title_line3_low.set_visible(False)
        for badge in badges:
            badge.set_visible(False)

        artists = [item for pair in lines for item in pair] + markers + badges
        artists += [title_line1_text, title_line2_text, title_line3_high, title_line3_low]
        return artists

    def update(frame):
        current_idx = min(frame // frames_per_point, len(dates) - 1)
        current_date = dates[current_idx]

        _update_axis_dates(current_idx)
        _update_axis_y(current_idx)

        performances = {}
        for i, (ticker, df) in enumerate(data.items()):
            current_prices = df['Close_IDR'].tolist()[:current_idx + 1]
            if current_prices:
                current_price = current_prices[-1]
                non_zero = [p for p in current_prices if p > 0]
                if non_zero:
                    performances[ticker] = ((current_price - non_zero[0]) / non_zero[0]) * 100

        # Determine Top 3 tickers for this frame (for header text only)
        if len(tickers) > 3:
            sorted_perf = sorted(performances.items(), key=lambda x: x[1], reverse=True)
            top3_tickers = set(t for t, _ in sorted_perf[:3])
        else:
            top3_tickers = set(tickers)

        for i, (ticker, df) in enumerate(data.items()):
            line, glow_line = lines[i]
            marker = markers[i]
            badge = badges[i]

            # Show ALL tickers (no hiding — all lines remain visible)
            line.set_visible(True)
            glow_line.set_visible(True)

            current_dates = dates[:current_idx + 1]
            current_pcts = pct_data[ticker][:current_idx + 1]
            current_prices = df['Close_IDR'].tolist()[:current_idx + 1]

            line.set_data(current_dates, current_pcts)
            glow_line.set_data(current_dates, current_pcts)

            if current_pcts:
                current_pct = current_pcts[-1]
                current_price = current_prices[-1]
                marker.set_offsets([[current_date, current_pct]])
                marker.set_visible(True)
                if ticker in performances:
                    pct_change = performances[ticker]
                    badge.set_text(f"{format_currency_full(current_price)}\n{format_profit_percentage(pct_change)}")
                    badge.set_position((current_date, current_pct + 0.5))
                    badge.set_visible(True)
                else:
                    badge.set_visible(False)

        # Update title
        date_str = current_date.strftime('%d %b %Y')
        best_ticker = max(performances.items(), key=lambda x: x[1]) if performances else None
        worst_ticker = min(performances.items(), key=lambda x: x[1]) if performances else None

        # Show top 3 tickers in title with profit format if more than 3 total
        if len(tickers) > 3 and performances:
            sorted_perf = sorted(performances.items(), key=lambda x: x[1], reverse=True)
            top3_items = sorted_perf[:3]
            header_parts = [f"{clean_ticker_symbol(t)}: {format_profit_percentage(v)}" for t, v in top3_items]
            header_str = " | ".join(header_parts)
            title_line1_text.set_text(header_str)
        else:
            display_tickers = [clean_ticker_symbol(t) for t in tickers]
            title_line1_text.set_text('  '.join(display_tickers))
        title_line1_text.set_visible(True)
        title_line2_text.set_text(date_str)
        title_line2_text.set_visible(True)

        if best_ticker:
            title_line3_high.set_text(f"[{clean_ticker_symbol(best_ticker[0])} {format_profit_percentage(best_ticker[1])}]")
            title_line3_high.set_visible(True)
        else:
            title_line3_high.set_visible(False)

        if worst_ticker and len(tickers) >= 2:
            title_line3_low.set_text(f"[{clean_ticker_symbol(worst_ticker[0])} {format_profit_percentage(worst_ticker[1])}]")
            title_line3_low.set_visible(True)
        else:
            title_line3_low.set_visible(False)

        artists = [item for pair in lines for item in pair] + markers + badges
        artists += [title_line1_text, title_line2_text, title_line3_high, title_line3_low]
        return artists

    # Build & save animation
    anim_frames = len(dates) * frames_per_point
    hold_frames = int(fps * hold_seconds)
    total_frames = anim_frames + hold_frames
    total_seconds = total_frames / fps

    print(f"Animation: {len(dates)} points x {frames_per_point} frames/point = {anim_frames} anim frames")
    print(f"  + {hold_frames} hold frames ({hold_seconds}s)")
    print(f"  = {total_frames} total frames ({total_seconds:.1f}s at {fps}fps)")

    anim = animation.FuncAnimation(fig, update, frames=total_frames,
                                   init_func=init, blit=False, interval=1000 / fps)
    writer = animation.FFMpegWriter(fps=fps)
    anim.save(output_path, writer=writer)
    print(f"Animated chart saved to {output_path}")
    plt.close()


def generate_mp4_animation(df_dict: Dict[str, pd.DataFrame], output_path: str) -> None:
    """
    Generate an animated MP4 chart.

    This is the public entry-point called by controller.py.

    Args:
        df_dict:     Dict of ticker → DataFrame with 'Date' and 'Close_IDR' columns
        output_path: File path where the MP4 will be saved
    """
    create_animated_chart(df_dict, output_path, fps=24)
