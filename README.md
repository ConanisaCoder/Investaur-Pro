# INVESTAUR PRO — Code & Math Guide

This document explains how every file works, how they connect, and all the math used.

---

## 1. How the files work together

```
main.py
   └── calls app.main()
         └── app.py  (InvestaurPro)
               ├── imports config   → colors, fonts, refresh intervals
               ├── imports models   → PortfolioState, WatchlistState, SimulatorState, Holding, get_company_info
               └── imports utils    → styled_entry, stat_card, divider, scrollable, fmt_big
```

- **config.py**: Constants only. No logic. App and utils read from it.
- **models.py**: Data structures and business logic (portfolio math, simulator). Uses **yfinance** for prices.
- **utils.py**: Pure UI helpers and number formatting. Uses **config** for colors/fonts.
- **app.py**: One big `InvestaurPro(tk.Tk)` class. Builds UI, calls **models** for data, **utils** for widgets, **config** for theme. Runs all tabs and real-time timers.

**Entry point**: `main.py` → `from app import main` → `main()` creates `InvestaurPro()` and runs `mainloop()`.

---

## 2. config.py — What it does

- **Colors**: `BG`, `PANEL`, `CARD`, `BORDER`, `ACCENT`, `ACCENT2`, `FG`, `FG_DIM`, `POS`, `NEG`, `BLUE`, `ORANGE` (hex strings). Used everywhere for a consistent dark theme.
- **Fonts**: `FONT_TITLE`, `FONT_MONO`, `FONT_SMALL`, `FONT_NUM` (family, size, weight).
- **Timers**: `REFRESH_PULSE_MS`, `REFRESH_PORTFOLIO_MS`, `REFRESH_ANALYSIS_MS`, `REFRESH_MARKETS_MS` (milliseconds). Drive how often sidebar, portfolio P&L, analysis price, and markets tab refresh.

No math. Just configuration.

---

## 3. models.py — Data and core math

### 3.1 COMPANY_INFO and get_company_info

- **COMPANY_INFO**: Dict of ticker → `{mission, summary, founded, employees, hq}`. Fallback when Yahoo has no data.
- **get_company_info(ticker)**: Returns that dict for a ticker, or a default “N/A” record.

### 3.2 Holding (dataclass)

- Fields: `ticker`, `shares`, `avg_price`, `purchase_date`.
- No methods. Just a record.

### 3.3 PortfolioState — Your real portfolio

- **holdings**: `dict[ticker → Holding]`.
- **add(t, s, a, date)**: Inserts/overwrites `Holding(ticker, shares, avg_price, date)`.
- **remove(t)**: Deletes holding by ticker.
- **snapshot()** (math):
  - For each holding: fetch last close `p` (yfinance 2d), else use `avg_price`.
  - **Market value**: $ v = p \times \text{shares} $
  - **Cost basis**: $ c = \text{avg\_price} \times \text{shares} $
  - **P&L**: $ \text{pl} = v - c $
  - **Return %**: $ \text{pct} = \frac{\text{pl}}{c} \times 100 $ (if $ c \ne 0 $)
  - Returns list of `(ticker, shares, avg_price, price, value, pl, pct)`, plus **total_v** (sum of $v$) and **total_pl** = total_v − total_cost.
- **historical_values(period)** (math):
  - For each holding: `yf.history(period)` → `Close * shares` per date.
  - Align all series on **common dates** (intersection of indices).
  - **Portfolio value time series** = sum of (aligned) value series. Used for “Portfolio vs SPY” growth chart.

### 3.4 WatchlistState

- **symbols**: list of ticker strings.
- **add(sym)** / **remove(sym)**: Append (if not present) or filter out. No math.

### 3.5 SimulatorState — Paper trading

- **cash**, **positions** `{ticker: {shares, avg}}`, **history** (list of trades), **start_cash** (e.g. 100_000).
- **buy(t, p, s)** (math):
  - **cost** = $ p \times s $. If cost > cash → fail.
  - cash -= cost; update or create position; running **average price** implied by adding shares at price $p$.
  - Log trade.
- **sell(t, p, s)**: cash += $ p \times s $; reduce shares; remove position if 0. Log trade.
- **portfolio_value()** (math):
  - **Total** = cash + $\sum_{\text{positions}} \text{last price} \times \text{shares}$. Last price from yfinance 1d.

---

## 4. utils.py — UI helpers and one math helper

- **styled_entry(parent, **kwargs)**: Builds a `tk.Entry` and strips unsupported options like `padx`/`pady`.
- **stat_card(parent, label, value, color, font_size)**: Frame with label (uppercase) and value; used for metric cards. Uses **config** for `CARD`, `FONT_SMALL`, `FG_DIM`.
- **divider(parent, color)**: Thin horizontal line (1px). Uses **config** `BORDER` by default.
- **scrollable(parent, bg)**: Canvas + scrollbar, inner frame, mousewheel/button bindings. Returns `(outer, inner, canvas)` so app packs `outer` and adds content to `inner`.
- **fmt_big(v)** (math):
  - If $ v \ge 10^{12} $ → `"$x.xxT"` (trillions).
  - Else if $ v \ge 10^9 $ → `"$x.xxB"` (billions).
  - Else if $ v \ge 10^6 $ → `"$x.xxM"` (millions).
  - Else format as integer with commas. Used for market cap, volume, etc.

---

## 5. app.py — Structure and flow

### 5.1 InvestaurPro.__init__

1. Window setup (title, geometry, bg from **config**).
2. **State**: `portfolio` (PortfolioState), `watchlist` (WatchlistState), `simulator` (SimulatorState), `current_sym` (StringVar), `_loading`, `_last_range`.
3. **Seed data**: Add sample holdings and watchlist symbols.
4. **Styles**: ttk theme (TFrame, TNotebook, Treeview, Scrollbar, TCombobox) using **config** colors/fonts.
5. **Layout**: `_build_sidebar` → `_build_header` → `_build_tabs`. Tabs are built by calling one builder per tab (Analysis, Company, Portfolio, Markets, News, Insight, Simulator, Dividends, Screener).
6. **Deferred work**: `after(200, run_analysis "6M")`, `after(800, _refresh_markets)`, `_schedule_realtime_updates()` (timers for pulse, portfolio P&L, analysis price, markets, simulator).

All heavy work (yfinance, network) runs in **daemon threads**; UI updates are done with `self.after(0, lambda: ...)` so they run on the main thread.

### 5.2 Sidebar

- Watchlist: list of symbols; add via entry + button; click symbol → `_load_symbol(sym)` (set current ticker, run analysis, switch to tab 0); ✕ → remove from watchlist.
- **Market pulse**: SPY, QQQ, BTC-USD. In a background thread, `_update_pulse` fetches 2d history, computes:
  - **Change %**: $ \text{chg} = \frac{\text{close}_{-1} - \text{close}_{-2}}{\text{close}_{-2}} \times 100 $
  - Updates labels; reschedules itself after `REFRESH_PULSE_MS`.
- **Portfolio P&L**: Label updated by `refresh_portfolio_sidebar` from `portfolio.snapshot()` → total_pl; runs every `REFRESH_PORTFOLIO_MS`.

### 5.3 Header

- **Ticker**: Combobox bound to `current_sym`; values = common tickers + watchlist. Return / selection → `_on_ticker_analyze()` → `run_analysis("6M")`.
- **Buttons**: ANALYZE (same), + WATCHLIST (add current to watchlist), COMPANY (switch to Company tab and load profile for current ticker).
- **Clock**: `_tick_clock` every 1s; shows time and “OPEN”/“CLOSED” based on weekday and 9:30–16:00.

### 5.4 Tab 1 — Analysis

- **Range buttons**: 1D, 5D, 1M, 3M, 6M, 1Y, 5Y, MAX. Each calls `run_analysis(r)`.
- **Chart type**: Line / Candle / Area; re-runs analysis with same range.
- **run_analysis(r)**: Gets current ticker, sets `_last_range`, starts thread that calls `_fetch_analysis(sym, r)`.
- **_fetch_analysis(sym, r)**:
  - Maps range to (period, interval) for yfinance (e.g. MAX → `("max","1mo")`).
  - `hist = t.history(period=..., interval=..., auto_adjust=True)`, `info = t.info`.
  - On success: `_render_analysis(sym, hist, info, r)`; on error: `_analysis_err(msg)`.

**Math in _render_analysis**:

- **Start / current price**:  
  $ P_{\text{start}} = \text{hist['Close'].iloc[0]} $,  
  $ P_{\text{curr}} = \text{info['regularMarketPrice'] or info['currentPrice'] or last close} $.
- **Change**: $ \Delta P = P_{\text{curr}} - P_{\text{start}} $.
- **Return %**: $ \text{chg\_pct} = \frac{\Delta P}{P_{\text{start}}} \times 100 $ (if $ P_{\text{start}} \ne 0 $).

Chart: price series from `hist["Close"]`; volume below; candlesticks use O/H/L/C. Stats panel uses **utils.fmt_big** and info (P/E, 52W high/low, etc.).

### 5.5 Tab 2 — Company

- Loads profile for a symbol: `_load_company_info(sym)` → thread `_fetch_company(sym)` (yfinance `info` + **models.get_company_info**), then `_render_company(sym, info, offline)`.
- Renders: name, exchange, sector; cards for Market Cap, Revenue, Net Income, Employees, Founded, HQ, P/E, EPS (from **utils.fmt_big** where needed); About (longBusinessSummary or offline summary); Financial highlights (margins, ROE, ratios — all from `info`, some as percentages $ \times 100 $).

### 5.6 Tab 3 — Portfolio

- **Refresh**: Thread → `portfolio.snapshot()` → `_populate_portfolio(rows, total_v, total_pl)`.
- Table: each row = (ticker, shares, avg cost, **current price**, **value** = price×shares, **P&L** = value−cost, **return%** = P&L/cost×100). Same formulas as **models.PortfolioState.snapshot**.
- **Summary cards**: Total value, total P&L, **total return %** = total_pl / total_cost × 100, number of holdings.
- **Charts**: Pie = allocation (each slice = value for one ticker); bar = P&L per holding.
- **Growth**: `_show_portfolio_growth` opens a window; `_fetch_growth(period)` gets `portfolio.historical_values(period)` and SPY history.

**Math in _render_growth**:

- **Portfolio % return series**: $ \text{pct}_t = \left( \frac{V_t}{V_0} - 1 \right) \times 100 $. $V_0$ = first total value, $V_t$ = total value at date $t$.
- **SPY % return series**: same idea, $ \frac{\text{Close}_t}{\text{Close}_0} - 1 $ in percent.
- Plot both vs time; 0% reference line.

### 5.7 Tab 4 — Markets

- Table: list of symbols (SPY, QQQ, …); for each, 2d history → current/previous close, then:
  - **chg** = current − previous, **chg_pct** = chg/previous×100.
- **Sector heatmap**: sector ETFs, same **chg_pct**; horizontal bar chart sorted by that %.

### 5.8 Tab 5 — News

- Topic buttons; `_load_news(topic)` → fetch Google News RSS → parse and show cards (title, link, source, date). No financial math.

### 5.9 Tab 6 — Insight (AI / Technical)

- **Run analysis**: `_run_ai()` → thread `_fetch_ai(sym)` → 2y history → `_render_ai(sym, closes, hist, info)`.

**All math in _render_ai**:

- **SMA (Simple Moving Average)**  
  $ \text{SMA}_n(P)_t = \frac{1}{n} \sum_{i=0}^{n-1} P_{t-i} $.  
  Implemented as `np.mean(closes[-20:])` etc., and for chart as `np.convolve(closes, np.ones(n)/n, "valid")`.

- **EMA (Exponential Moving Average)**  
  $ k = \frac{2}{n+1} $,  
  $ \text{EMA}_t = k\,P_t + (1-k)\,\text{EMA}_{t-1} $.  
  Used for MACD (and smoothing).

- **RSI (14)**  
  $ \Delta_t = P_t - P_{t-1} $,  
  avg_gain = mean of $\max(\Delta,0)$ over last 14,  
  avg_loss = mean of $\max(-\Delta,0)$ over last 14,  
  $ \text{RSI} = 100 - \frac{100}{1 + \frac{\text{avg\_gain}}{\text{avg\_loss}}} $.  
  (Avoid div by zero with 1e-9.)

- **MACD**  
  - Line: $ \text{EMA}_{12}(P) - \text{EMA}_{26}(P) $.  
  - Signal: $ \text{EMA}_9(\text{MACD}) $.  
  - Histogram: MACD − Signal.

- **Bollinger Bands (20, 2)**  
  $ \mu = \text{mean}(\text{last 20}) $, $ \sigma = \text{std}(\text{last 20}) $,  
  Upper = $ \mu + 2\sigma $, Lower = $ \mu - 2\sigma $.

- **Returns**: $ r_t = \frac{P_t - P_{t-1}}{P_{t-1}} $ → `np.diff(closes)/closes[:-1]`.

- **Annualized volatility** (last 30 days):  
  $ \sigma_{\text{ann}} = \sigma_{\text{daily}} \times \sqrt{252} \times 100 $ (as %).

- **Sharpe ratio** (1y):  
  $ \text{Sharpe} = \frac{\bar{r}}{\sigma_r} \times \sqrt{252} $ (risk-free rate 0). Denominator clamped to avoid 0.

- **Momentum**  
  - 1M: $ \left( \frac{P_{\text{now}}}{P_{22\text{ ago}}} - 1 \right) \times 100 $.  
  - 3M/6M/1Y: same with 63, 126, 252 trading days.

- **Max drawdown**  
  For each $t$: peak_t = max price up to $t$;  
  $ \text{dd}_t = \frac{P_t - \text{peak}_t}{\text{peak}_t} \times 100 $;  
  max_dd = min over time (worst drop from a peak).

- **Signal score**: 9 boolean signals (e.g. price > SMA20, RSI in range, MACD bullish).  
  **bull_pct** = (count true / 9)×100. Used for “BULLISH” / “BEARISH” label and bar width.

Charts: price + SMA20/50/200 + Bollinger band; below, MACD line + signal + histogram.

### 5.10 Tab 7 — Simulator

- Displays: **Current cash** (simulator.cash), **Total value of assets** = `simulator.portfolio_value()` (cash + positions at last price), **P&L** = value − start_cash, **P&L %** = P&L/start_cash×100.
- Buy/Sell: ticker + shares; thread fetches price, calls `simulator.buy(t,p,s)` or `sell(t,p,s)`; then updates cash label, positions list, value/P&L, and account value chart.
- **Edit cash**: dialog to set `simulator.cash` manually.
- Chart: time series of portfolio value (from `_sim_value_history`); horizontal line at start_cash.

### 5.11 Tab 8 — Dividends

- For each portfolio holding: yfinance `info` → dividendRate, dividendYield, exDividendDate.  
  **Annual income** = rate × shares; total annual = sum over holdings.  
  **Monthly** ≈ total/12; **weekly** ≈ total/52.  
  Bar chart: projected quarterly dividends mapped to months (simplified).

### 5.12 Tab 9 — Screener

- Universe: S&P 100 list, or Portfolio, or Watchlist, or Tech, or Crypto.
- Filters: min/max P/E, min div %, max beta, min market cap (parsed e.g. "1B" → 1e9).
- For each symbol: fetch info and 5d history; filter by P/E, div_yield, beta, mcap; build rows (ticker, name, price, P/E, EPS, div%, beta, mcap, sector). **Sort** by selected column (numeric sort for Price, P/E, etc.).
- **utils.fmt_big** used for market cap display.

### 5.13 Real-time refresh (summary)

- **refresh_portfolio_sidebar**: every `REFRESH_PORTFOLIO_MS`, run `portfolio.snapshot()`, update sidebar P&L label.
- **refresh_analysis_price**: every `REFRESH_ANALYSIS_MS`, for current ticker and `_last_range`, fetch same period, recompute **start_price** and **curr** (from info or last close), **chg** and **chg_pct** as in _render_analysis, update price and change labels.
- **refresh_markets_if_visible**: every 5 min, if Markets tab is selected, call `_refresh_markets`.
- **refresh_simulator_if_visible**: every 60s, if Simulator tab is selected, call `_sim_update_value` (recompute portfolio value and P&L).

---

## 6. Math summary (formulas in one place)

| What | Formula |
|------|--------|
| **Price change %** | $ \frac{P_{\text{now}} - P_{\text{start}}}{P_{\text{start}}} \times 100 $ |
| **Value** | $ P \times \text{shares} $ |
| **P&L** | $ V - C $, $ C = \text{avg\_price} \times \text{shares} $ |
| **Return %** | $ \frac{\text{P&L}}{C} \times 100 $ |
| **SMA** | $ \frac{1}{n}\sum_{i=0}^{n-1} P_{t-i} $ |
| **EMA** | $ k = 2/(n+1) $, $ \text{EMA}_t = k P_t + (1-k)\text{EMA}_{t-1} $ |
| **RSI** | $ 100 - \frac{100}{1 + \text{avg\_gain}/\text{avg\_loss}} $ |
| **MACD** | EMA12 − EMA26; Signal = EMA9(MACD); Hist = MACD − Signal |
| **Bollinger** | $ \mu \pm 2\sigma $ on last 20 closes |
| **Volatility (ann.)** | $ \sigma_{\text{daily}} \times \sqrt{252} \times 100 $ |
| **Sharpe** | $ \frac{\bar{r}}{\sigma_r} \sqrt{252} $ |
| **Max drawdown** | $ \min_t \frac{P_t - \text{peak}_t}{\text{peak}_t} \times 100 $ |
| **Period return %** | $ \left( \frac{V_t}{V_0} - 1 \right) \times 100 $ |
| **fmt_big** | Scale by 1e12 / 1e9 / 1e6 for T / B / M |

---

## 7. Data flow (who calls whom)

- **app** creates and owns `portfolio`, `watchlist`, `simulator`; calls their methods and passes data into UI.
- **app** uses **utils** for every card, divider, scroll area, and big-number format.
- **app** uses **config** for all colors, fonts, and timer intervals.
- **models** use **yfinance** only; no UI. **app** never imports yfinance in the sense of “models encapsulate it”; app also calls yf for analysis, markets, simulator price, etc.
- **Threading**: Any yfinance or network work runs in daemon threads; results are applied to the UI via `self.after(0, lambda: ...)` so Tk runs them on the main thread.

This is the full picture of the code and how the math fits in for your Mathahcks presentation.
