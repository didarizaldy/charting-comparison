# Yahoo Finance Ticker Chart Visualizer

A Python module for generating static PNG and animated MP4 charts from Yahoo Finance data with IDR conversion.

## Features

- **Static PNG Chart**: 1920x1080 landscape format for social media posts
- **Animated MP4 Chart**: 1080x1920 vertical format for TikTok, Instagram Reels, YouTube Shorts
- **Real-time IDR Conversion**: Automatically fetches USD/IDR exchange rate
- **Dark Theme**: Professional dark theme with glow effects
- **Smart Date Formatting**: Shows month only for same-year data, month-year for cross-year data
- **Multiple Ticker Support**: Visualize multiple stocks in one chart

## Requirements

- Python 3.7+
- Required packages: `yfinance`, `matplotlib`, `pandas`, `numpy`, `moviepy`
- FFmpeg (for MP4 animation)

## Installation

1. Create and activate virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install yfinance matplotlib pandas numpy moviepy
   ```

## Usage

Run the main script:
```bash
python src/service/chart.py
```

This will:
1. Fetch USD/IDR exchange rate
2. Download 3 months of data for AAPL, NVDA, MSFT
3. Generate `static_chart.png` (1920x1080)
4. Generate `animated_chart.mp4` (1080x1920)

## Customization

Edit `src/service/chart.py` to:
- Change tickers in the `main()` function
- Adjust time period (default: "3mo")
- Modify output file paths
- Customize colors and styling

## Project Structure

```
saham_x_crypto/
├── src/
│   └── service/
│       └── chart.py          # Main chart generation module
├── venv/                     # Virtual environment
├── static_chart.png          # Generated static chart
├── animated_chart.mp4        # Generated animated chart
└── README.md                 # This file
```

## Visual Specifications

- **Background Color**: `#0f172a` (Dark Theme)
- **Text Color**: `#FFFFFF` (White)
- **Font Size**: 11
- **Glow Effect**: Double plotting with alpha transparency
- **Area Fill**: Transparent fill under lines
- **Grid**: Subtle white grid with alpha 0.15
- **Legend**: Dark glass style with semi-transparent background
- **Header Format**: 3-line centered text with ticker symbols, date range, and leading ticker

## Output Examples

- `static_chart.png`: Landscape 1920x1080 PNG
- `animated_chart.mp4`: Vertical 1080x1920 MP4 with smooth line animation

## License

MIT