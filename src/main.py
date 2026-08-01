"""
CLI entry point for the Stock / Asset Multi-Ticker Visualizer.

Usage examples:

    Mode 1 — Specific date range (-d):
        python src/main.py -t ^JKSE GF=F BTC-USD -d 01/07/2026 23/07/2026

    Mode 2 — Interval days back (-i):
        python src/main.py -t BTC-USD BBCA GOTO -i 5

    Mode 3 — Custom period (-p):
        python src/main.py -t ETH-USD SILVER TLKM -p 1mo

Options -d, -i, and -p are mutually exclusive.
"""

import argparse
import os
import sys

# Fix Windows console encoding (cp1252) to support UTF-8 output
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure the src directory is on the Python path so `service` can be imported
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from service import controller


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog='main.py',
        description='Multi-ticker stock/asset comparison visualizer with DB caching.',
    )

    # ── Tickers OR IHSP mode (mutually exclusive) ────────────────────
    ticker_group = parser.add_mutually_exclusive_group(required=True)

    ticker_group.add_argument(
        '-t', '--tickers',
        nargs='+',
        metavar='TICKER',
        help='One or more ticker symbols (e.g., BTC-USD BBCA.JK ^JKSE)',
    )

    ticker_group.add_argument(
        '-x', '--ihsp',
        action='store_true',
        help='Mode IHSP: visualisasi IHSP (^PEARL) vs IHSG (^JKSE) '
             'menggunakan seluruh data di database (kecuali ^JKSE)',
    )

    # ── Mutually exclusive date-range modes ───────────────────────────
    date_group = parser.add_mutually_exclusive_group(required=True)

    date_group.add_argument(
        '-d', '--date',
        nargs=2,
        metavar=('START', 'END'),
        help='Date range in DD/MM/YYYY format (e.g., 01/07/2026 23/07/2026)',
    )

    date_group.add_argument(
        '-i', '--interval',
        type=int,
        metavar='DAYS',
        help='Number of days to look back from today (e.g., 5)',
    )

    date_group.add_argument(
        '-p', '--period',
        type=str,
        metavar='PERIOD',
        help='yfinance period string (e.g., 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y)',
    )

    return parser


def main() -> None:
    """Parse CLI arguments and delegate to the controller."""
    parser = build_parser()
    args = parser.parse_args()

    # Determine which date mode was chosen
    if args.date:
        date_mode = 'date'
        date_start = args.date[0]
        date_end = args.date[1]
        interval_days = None
        period = None
    elif args.interval is not None:
        date_mode = 'interval'
        date_start = None
        date_end = None
        interval_days = args.interval
        period = None
    elif args.period:
        date_mode = 'period'
        date_start = None
        date_end = None
        interval_days = None
        period = args.period
    else:
        parser.error("You must specify one of: -d, -i, or -p")
        return

    # Determine if IHSP mode is active
    is_ihsp_mode = args.ihsp

    # Run the controller pipeline
    controller.run(
        tickers=args.tickers if not is_ihsp_mode else None,
        is_ihsp_mode=is_ihsp_mode,
        date_mode=date_mode,
        date_start=date_start,
        date_end=date_end,
        interval_days=interval_days,
        period=period,
    )


if __name__ == '__main__':
    main()
