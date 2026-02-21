# INVESTAUR PRO — Professional Stock Terminal

A full-featured desktop stock terminal with real-time updates, built with Python and Tkinter.

## Features

- **Analysis** — Interactive price charts (Line, Candlestick, Area), volume, key stats
- **Company** — Profiles, mission, financials, sector info
- **Portfolio** — Holdings, P&L, allocation pie chart, growth vs SPY benchmark
- **Markets** — Live market table, sector heatmap
- **News** — RSS news by topic (Fed, earnings, crypto, etc.)
- **AI Insight** — Technical analysis (RSI, MACD, Bollinger, SMAs, signals)
- **Simulator** — Paper trading with $100k virtual cash
- **Dividends** — Tracker for portfolio dividend income
- **Screener** — Filter by P/E, dividend, beta, market cap

## Real-time Updates

- Market pulse (SPY, QQQ, BTC) — every 60s
- Portfolio P&L sidebar — every 60s
- Current symbol price in Analysis — every 30s
- Markets tab — every 5 min when visible

## Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Run

```bash
python main.py
# Or with run script:
./run.sh
```

## Project Structure

```
NetWorthonNet/
├── main.py        # Entry point
├── app.py         # Main app & all tabs
├── config.py      # Theme, fonts, refresh intervals
├── models.py      # Portfolio, Watchlist, Simulator, Holding
├── utils.py       # UI helpers (stat_card, scrollable, etc.)
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.8+
- yfinance, matplotlib, numpy, feedparser
