"""
INVESTAUR PRO — Application module (main UI and tabs)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import feedparser
import urllib.parse
import webbrowser
import numpy as np
import threading
import re
from datetime import datetime

import yfinance as yf

from config import (
    BG, PANEL, CARD, BORDER, ACCENT, ACCENT2, FG, FG_DIM, POS, NEG, BLUE, ORANGE,
    FONT_TITLE, FONT_MONO, FONT_SMALL, FONT_NUM,
    REFRESH_PULSE_MS, REFRESH_PORTFOLIO_MS, REFRESH_ANALYSIS_MS, REFRESH_MARKETS_MS,
)
from models import (
    Holding, PortfolioState, WatchlistState, SimulatorState,
    get_company_info,
)
from utils import styled_entry, stat_card, divider, scrollable, fmt_big

# ──────────────────────────────────────────
# MAIN APP
# ──────────────────────────────────────────

class InvestaurPro(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("INVESTAUR PRO  ·  Professional Trading Terminal")
        self.geometry("1400x850")
        self.minsize(1000, 600)
        self.configure(bg=BG)

        self.portfolio   = PortfolioState()
        self.watchlist   = WatchlistState()
        self.simulator   = SimulatorState()
        self.current_sym = tk.StringVar(value="AAPL")
        self._loading    = False
        self._last_range = "6M"

        self._seed_data()
        self._setup_styles()
        self._build_layout()
        self.after(200, lambda: self.run_analysis("6M"))
        self.after(800, self._refresh_markets)
        self._schedule_realtime_updates()

    def _seed_data(self):
        self.portfolio.add("AAPL",   10,   150.0,  "2022-01-15")
        self.portfolio.add("NVDA",    5,   400.0,  "2022-06-10")
        self.portfolio.add("MSFT",    8,   280.0,  "2021-11-20")
        self.portfolio.add("BTC-USD", 0.1, 45000.0,"2023-03-01")
        self.portfolio.add("GOOGL",   3,  2800.0,  "2022-09-05")
        for s in ["TSLA","META","AMZN","AMD","QQQ"]:
            self.watchlist.add(s)

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TFrame", background=BG)
        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=0)
        s.configure("TNotebook.Tab", background=PANEL, foreground=FG_DIM,
                    padding=(20, 10), font=("Consolas", 10, "bold"), borderwidth=0)
        s.map("TNotebook.Tab",
              background=[("selected", ACCENT)],
              foreground=[("selected", BG)])
        s.configure("Treeview", background=CARD, foreground=FG, fieldbackground=CARD,
                    rowheight=34, borderwidth=0, font=FONT_MONO)
        s.configure("Treeview.Heading", background=PANEL, foreground=ACCENT,
                    font=FONT_SMALL, borderwidth=0, padding=(8, 6))
        s.map("Treeview", background=[("selected", BORDER)])
        s.configure("Vertical.TScrollbar", background=PANEL, troughcolor=BG,
                    borderwidth=0, arrowcolor=FG_DIM)
        s.configure("TCombobox", fieldbackground=CARD, background=PANEL, foreground=FG,
                    arrowcolor=ACCENT, bordercolor=BORDER)
        s.map("TCombobox", fieldbackground=[("readonly", CARD)], background=[("active", PANEL)])

    # ── LAYOUT ──────────────────────────────────────
    def _build_layout(self):
        self._build_sidebar()
        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self._build_header(main)
        self._build_tabs(main)

    # ── SIDEBAR ─────────────────────────────────────
    def _build_sidebar(self):
        sb = tk.Frame(self, bg=PANEL, width=200)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tk.Label(sb, text="INVESTAUR", font=("Courier", 14, "bold"),
                 fg=ACCENT, bg=PANEL, pady=16).pack()
        tk.Label(sb, text="PRO", font=("Courier", 10), fg=ACCENT2, bg=PANEL).pack()
        divider(sb)

        tk.Label(sb, text="WATCHLIST", fg=FG_DIM, bg=PANEL, font=FONT_SMALL,
                 padx=14).pack(anchor="w", pady=(4, 4))
        self.watchlist_frame = tk.Frame(sb, bg=PANEL)
        self.watchlist_frame.pack(fill="x")

        add_f = tk.Frame(sb, bg=PANEL, padx=10, pady=6)
        add_f.pack(fill="x")
        self.wl_entry = styled_entry(add_f, font=("Consolas", 10), bg=CARD, fg=FG,
                                     insertbackground=ACCENT, borderwidth=0, width=10)
        self.wl_entry.pack(side="left")
        self.wl_entry.bind("<Return>", self._add_to_watchlist)
        self._btn(add_f, "+", self._add_to_watchlist, ACCENT, BG, width=3).pack(side="left", padx=(4, 0))

        divider(sb)
        tk.Label(sb, text="MARKET PULSE", fg=FG_DIM, bg=PANEL, font=FONT_SMALL, padx=14).pack(anchor="w", pady=(4, 4))
        self.pulse_frame = tk.Frame(sb, bg=PANEL, padx=10)
        self.pulse_frame.pack(fill="x")
        self._pulse_labels = {}
        for sym in ["SPY", "QQQ", "BTC-USD"]:
            row = tk.Frame(self.pulse_frame, bg=PANEL, pady=3)
            row.pack(fill="x")
            tk.Label(row, text=sym, fg=ACCENT, bg=PANEL, font=("Consolas", 9, "bold"),
                     width=8, anchor="w").pack(side="left")
            lbl = tk.Label(row, text="…", fg=FG_DIM, bg=PANEL, font=("Consolas", 9))
            lbl.pack(side="left")
            self._pulse_labels[sym] = lbl

        divider(sb)
        self.pnl_sidebar = tk.Label(sb, text="Portfolio P&L\n$0.00",
                                     fg=FG_DIM, bg=PANEL, font=("Consolas", 9), pady=10)
        self.pnl_sidebar.pack()

        self._refresh_watchlist_ui()
        threading.Thread(target=self._update_pulse, daemon=True).start()

    def _add_to_watchlist(self, event=None):
        sym = self.wl_entry.get().strip().upper()
        if sym:
            self.watchlist.add(sym)
            self.wl_entry.delete(0, "end")
            self._refresh_watchlist_ui()

    def _refresh_watchlist_ui(self):
        for w in self.watchlist_frame.winfo_children():
            w.destroy()
        for sym in self.watchlist.symbols:
            row = tk.Frame(self.watchlist_frame, bg=PANEL, padx=10, pady=3)
            row.pack(fill="x")
            lbl = tk.Label(row, text=sym, fg=FG, bg=PANEL, font=("Consolas", 10),
                           cursor="hand2", anchor="w")
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, s=sym: self._load_symbol(s))
            lbl.bind("<Enter>", lambda e, w=lbl: w.config(fg=ACCENT))
            lbl.bind("<Leave>", lambda e, w=lbl: w.config(fg=FG))
            rm = tk.Label(row, text="✕", fg=FG_DIM, bg=PANEL, font=("Consolas", 8), cursor="hand2")
            rm.pack(side="right")
            rm.bind("<Button-1>", lambda e, s=sym: self._remove_watchlist(s))

    def _remove_watchlist(self, sym):
        self.watchlist.remove(sym)
        self._refresh_watchlist_ui()

    def _load_symbol(self, sym):
        sym = sym.strip().upper()
        if not sym:
            return
        self.current_sym.set(sym)
        if hasattr(self, "search_entry") and self.search_entry.winfo_exists():
            self.search_entry.delete(0, "end")
            self.search_entry.insert(0, sym)
        self.run_analysis("6M")
        self.notebook.select(0)

    def _update_pulse(self):
        for sym in ["SPY", "QQQ", "BTC-USD"]:
            try:
                d = yf.Ticker(sym).history(period="2d")
                if d.empty or len(d) < 2:
                    continue
                c, p = float(d["Close"].iloc[-1]), float(d["Close"].iloc[-2])
                chg = (c - p) / p * 100
                sign = "+" if chg >= 0 else ""
                color = POS if chg >= 0 else NEG
                text = f"${c:,.0f} {sign}{chg:.1f}%" if c > 1000 else f"${c:.2f} {sign}{chg:.1f}%"
                self.after(0, lambda s=sym, t=text, cl=color: self._pulse_labels[s].config(text=t, fg=cl))
            except Exception:
                pass
        self.after(REFRESH_PULSE_MS, lambda: threading.Thread(target=self._update_pulse, daemon=True).start())

    def _schedule_realtime_updates(self):
        """Schedule periodic real-time updates for live data."""
        def refresh_portfolio_sidebar():
            try:
                rows, _, total_pl = self.portfolio.snapshot()
                if rows:
                    sign = "+" if total_pl >= 0 else ""
                    pl_color = POS if total_pl >= 0 else NEG
                    self.after(0, lambda: self.pnl_sidebar.config(
                        text=f"Portfolio P&L\n{sign}${abs(total_pl):,.2f}", fg=pl_color))
            except Exception:
                pass
            self.after(REFRESH_PORTFOLIO_MS, lambda: threading.Thread(target=refresh_portfolio_sidebar, daemon=True).start())

        PERIOD_MAP = {"1D": ("1d","5m"), "5D": ("5d","15m"), "1M": ("1mo","1h"),
                      "3M": ("3mo","1d"), "6M": ("6mo","1d"), "1Y": ("1y","1d"),
                      "5Y": ("5y","1wk"), "MAX": ("max","1mo")}
        def refresh_analysis_price():
            if self._loading:
                self.after(REFRESH_ANALYSIS_MS, refresh_analysis_price)
                return
            sym = self._get_current_ticker()
            r = getattr(self, "_last_range", "6M")
            period, _ = PERIOD_MAP.get(r, ("6mo", "1d"))
            if sym and hasattr(self, "lbl_price") and self.lbl_price.winfo_exists():

                def _fetch():
                    try:
                        t = yf.Ticker(sym)
                        d = t.history(period=period)
                        info = t.info
                        if not d.empty and len(d) >= 1:
                            start_price = float(d["Close"].iloc[0])
                            hist_last = float(d["Close"].iloc[-1])
                            curr = info.get("regularMarketPrice") or info.get("currentPrice")
                            if curr is None or not isinstance(curr, (int, float)):
                                curr = hist_last
                            else:
                                curr = float(curr)
                            chg = curr - start_price
                            chg_pct = (chg / start_price * 100) if start_price and start_price != 0 else 0
                            color_line = POS if chg >= 0 else NEG
                            sign = "+" if chg >= 0 else ""
                            self.after(0, lambda: [
                                self.lbl_price.config(text=f"${curr:,.2f}"),
                                self.lbl_chg.config(text=f"{sign}{chg:.2f} ({sign}{chg_pct:.2f}%)", fg=color_line)
                            ])
                    except Exception:
                        pass
                    self.after(REFRESH_ANALYSIS_MS, refresh_analysis_price)

                threading.Thread(target=_fetch, daemon=True).start()
                return
            self.after(REFRESH_ANALYSIS_MS, refresh_analysis_price)

        def refresh_markets_if_visible():
            try:
                idx = self.notebook.index(self.notebook.select())
                if idx == 3:
                    self.after(0, self._refresh_markets)
            except Exception:
                pass
            self.after(REFRESH_MARKETS_MS, lambda: threading.Thread(target=refresh_markets_if_visible, daemon=True).start())

        def refresh_simulator_if_visible():
            try:
                idx = self.notebook.index(self.notebook.select())
                if idx == 6 and hasattr(self, "sim_port_lbl") and self.sim_port_lbl.winfo_exists():
                    self.after(0, self._sim_update_value)
            except Exception:
                pass
            self.after(REFRESH_PORTFOLIO_MS, lambda: threading.Thread(target=refresh_simulator_if_visible, daemon=True).start())

        self.after(REFRESH_PORTFOLIO_MS, lambda: threading.Thread(target=refresh_portfolio_sidebar, daemon=True).start())
        self.after(REFRESH_PORTFOLIO_MS, lambda: threading.Thread(target=refresh_simulator_if_visible, daemon=True).start())
        self.after(REFRESH_ANALYSIS_MS, refresh_analysis_price)
        self.after(REFRESH_MARKETS_MS, lambda: threading.Thread(target=refresh_markets_if_visible, daemon=True).start())

    # ── HEADER ──────────────────────────────────────
    def _build_header(self, parent):
        hf = tk.Frame(parent, bg=BG, padx=20, pady=12)
        hf.pack(fill="x")

        self.clock_lbl = tk.Label(hf, text="", fg=FG_DIM, bg=BG, font=("Consolas", 9))
        self.clock_lbl.pack(side="right", padx=(0, 8))
        self._tick_clock()

        search_outer = tk.Frame(hf, bg=BORDER, padx=1, pady=1)
        search_outer.pack(side="left", padx=(0, 10))
        search_inner = tk.Frame(search_outer, bg=PANEL, padx=10, pady=5)
        search_inner.pack()
        tk.Label(search_inner, text="⌕ ", fg=FG_DIM, bg=PANEL, font=("Helvetica", 13)).pack(side="left")
        self._update_ticker_combo_values()
        self.search_entry = ttk.Combobox(search_inner, textvariable=self.current_sym,
                                         font=("Consolas", 13), width=12, state="normal")
        self.search_entry["values"] = self._ticker_combo_values
        self.search_entry.pack(side="left")
        self.search_entry.bind("<Return>", lambda e: self._on_ticker_analyze())
        self.search_entry.bind("<<ComboboxSelected>>", lambda e: self._on_ticker_analyze())

        self._btn(hf, "ANALYZE",    self._on_ticker_analyze,              ACCENT, BG).pack(side="left", padx=(0, 6))
        self._btn(hf, "+ WATCHLIST", self._add_current_to_wl,             PANEL,  FG).pack(side="left", padx=3)
        self._btn(hf, "COMPANY",    lambda: [self.notebook.select(1), self._load_company_info(self._get_current_ticker())], PANEL, BLUE).pack(side="left", padx=3)

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(hf, textvariable=self.status_var, fg=FG_DIM, bg=BG,
                 font=("Consolas", 9)).pack(side="left", padx=14)

    def _update_ticker_combo_values(self):
        common = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "NFLX", "SPY", "QQQ", "BTC-USD"]
        self._ticker_combo_values = list(dict.fromkeys(
            common + [s for s in self.watchlist.symbols if s not in common]
        ))

    def _get_current_ticker(self):
        """Read ticker from combobox/entry directly to avoid sync issues."""
        try:
            val = self.search_entry.get().strip().upper()
            return val if val else self.current_sym.get().strip().upper()
        except AttributeError:
            return self.current_sym.get().strip().upper()

    def _on_ticker_analyze(self, event=None):
        sym = self._get_current_ticker()
        if sym:
            self.current_sym.set(sym)
            self.run_analysis("6M")

    def _add_current_to_wl(self):
        sym = self._get_current_ticker()
        if not sym:
            return
        self.watchlist.add(sym)
        self._update_ticker_combo_values()
        if hasattr(self, "search_entry") and self.search_entry.winfo_exists():
            self.search_entry["values"] = self._ticker_combo_values
        self._refresh_watchlist_ui()
        self.status_var.set(f"Added {sym} to watchlist.")

    def _tick_clock(self):
        now = datetime.now()
        mo = now.replace(hour=9, minute=30, second=0, microsecond=0)
        mc = now.replace(hour=16, second=0, microsecond=0)
        status = "🟢 OPEN" if now.weekday() < 5 and mo <= now <= mc else "🔴 CLOSED"
        self.clock_lbl.config(text=now.strftime("%a %b %d  %H:%M:%S") + f"  {status}")
        self.after(1000, self._tick_clock)

    def _btn(self, parent, text, cmd, bg=PANEL, fg=FG, width=None):
        kw = dict(text=text, command=cmd, bg=bg, fg=fg,
                  font=("Consolas", 9, "bold"), padx=12, pady=6,
                  borderwidth=0, cursor="hand2",
                  activebackground=ACCENT, activeforeground=BG)
        if width:
            kw["width"] = width
        return tk.Button(parent, **kw)

    def _style_ax(self, ax):
        ax.set_facecolor(BG)
        ax.tick_params(colors=FG_DIM, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.grid(True, color=BORDER, linewidth=0.5, alpha=0.5)

    # ── TABS ────────────────────────────────────────
    def _build_tabs(self, parent):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        tabs = [
            ("  ANALYSIS  ",   self._build_analysis_tab),
            ("  COMPANY  ",    self._build_company_tab),
            ("  PORTFOLIO  ",  self._build_portfolio_tab),
            ("  MARKETS  ",    self._build_markets_tab),
            ("  NEWS  ",       self._build_news_tab),
            ("  INSIGHT  ", self._build_ai_tab),
            ("  SIMULATOR  ",  self._build_sim_tab),
            ("  DIVIDENDS  ",  self._build_dividends_tab),
            ("  SCREENER  ",   self._build_screener_tab),
        ]
        for label, builder in tabs:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=label)
            builder(frame)

    # ═══════════════════════════════════════════════
    # TAB 1 — ANALYSIS
    # ═══════════════════════════════════════════════
    def _build_analysis_tab(self, tab):
        rb = tk.Frame(tab, bg=BG, padx=14, pady=8)
        rb.pack(fill="x")
        tk.Label(rb, text="RANGE:", fg=FG_DIM, bg=BG, font=FONT_SMALL).pack(side="left", padx=(0, 8))
        self._range_btns = {}
        for r in ["1D", "5D", "1M", "3M", "6M", "1Y", "5Y", "MAX"]:
            b = tk.Button(rb, text=r, command=lambda x=r: self.run_analysis(x),
                          bg=PANEL, fg=FG_DIM, font=("Consolas", 9, "bold"),
                          padx=10, pady=5, borderwidth=0, cursor="hand2",
                          activebackground=ACCENT, activeforeground=BG)
            b.pack(side="left", padx=2)
            self._range_btns[r] = b

        tk.Label(rb, text="  CHART:", fg=FG_DIM, bg=BG, font=FONT_SMALL).pack(side="left", padx=(14, 8))
        self.chart_type = tk.StringVar(value="Line")
        for ct in ["Line", "Candle", "Area"]:
            tk.Radiobutton(rb, text=ct, variable=self.chart_type, value=ct,
                           fg=FG_DIM, bg=BG, selectcolor=PANEL, activebackground=BG,
                           font=("Consolas", 9), command=lambda: self.run_analysis(self._last_range)
                           ).pack(side="left", padx=4)

        content = tk.Frame(tab, bg=BG)
        content.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        # Chart area
        left = tk.Frame(content, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.fig = Figure(facecolor=BG)
        self.gs  = gridspec.GridSpec(2, 1, figure=self.fig, height_ratios=[4, 1], hspace=0.05)
        self.ax  = self.fig.add_subplot(self.gs[0])
        self.axv = self.fig.add_subplot(self.gs[1], sharex=self.ax)
        self.fig.subplots_adjust(left=0.06, right=0.96, top=0.94, bottom=0.12)
        self._style_ax(self.ax)
        self._style_ax(self.axv)
        self.canvas = FigureCanvasTkAgg(self.fig, master=left)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Info panel
        right = tk.Frame(content, bg=PANEL, width=330)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        rpad = tk.Frame(right, bg=PANEL, padx=16, pady=16)
        rpad.pack(fill="both", expand=True)

        self.lbl_name = tk.Label(rpad, text="—", font=("Courier", 13, "bold"),
                                  fg=ACCENT, bg=PANEL, wraplength=290, justify="left")
        self.lbl_name.pack(anchor="w")
        self.lbl_tex = tk.Label(rpad, text="", fg=FG_DIM, bg=PANEL, font=("Consolas", 8))
        self.lbl_tex.pack(anchor="w")

        pf = tk.Frame(rpad, bg=PANEL, pady=6)
        pf.pack(anchor="w")
        self.lbl_price = tk.Label(pf, text="$—", font=("Courier", 26, "bold"), fg=FG, bg=PANEL)
        self.lbl_price.pack(side="left")
        self.lbl_chg = tk.Label(pf, text="", font=("Consolas", 10), fg=FG_DIM, bg=PANEL)
        self.lbl_chg.pack(side="left", padx=(8, 0), anchor="s")

        divider(rpad)
        self.stats_frame = tk.Frame(rpad, bg=PANEL)
        self.stats_frame.pack(fill="x")
        divider(rpad)

        self._btn(rpad, "+ ADD TO PORTFOLIO", self._quick_add_to_portfolio, BORDER, ACCENT).pack(fill="x", pady=2)
        self._btn(rpad, "VIEW COMPANY PROFILE", lambda: [self.notebook.select(1), self._load_company_info(self._get_current_ticker())], BORDER, BLUE).pack(fill="x", pady=2)

    def _highlight_range(self, active):
        for r, b in self._range_btns.items():
            b.config(bg=ACCENT if r == active else PANEL,
                     fg=BG      if r == active else FG_DIM)

    def run_analysis(self, r="6M"):
        if self._loading:
            return
        sym = self._get_current_ticker()
        if not sym:
            return
        self._last_range = r
        self._highlight_range(r)
        self.status_var.set(f"Fetching {sym}…")
        self._loading = True
        threading.Thread(target=self._fetch_analysis, args=(sym, r), daemon=True).start()

    def _fetch_analysis(self, sym, r):
        mapping = {
            "1D": ("1d","5m"), "5D": ("5d","15m"), "1M": ("1mo","1h"),
            "3M": ("3mo","1d"), "6M": ("6mo","1d"), "1Y": ("1y","1d"),
            "5Y": ("5y","1wk"), "MAX": ("max","1mo"),
        }
        period, interval = mapping.get(r, ("6mo", "1d"))
        try:
            t = yf.Ticker(sym)
            hist = t.history(period=period, interval=interval, auto_adjust=True)
            info = t.info
            if hist.empty:
                raise ValueError("No price data returned.")
            self.after(0, lambda: self._render_analysis(sym, hist, info, r))
        except Exception as e:
            self.after(0, lambda: self._analysis_err(str(e)))

    def _render_analysis(self, sym, hist, info, r):
        self._loading = False
        start_price = float(hist["Close"].iloc[0]) if len(hist) > 1 else float(hist["Close"].iloc[-1])
        hist_last = float(hist["Close"].iloc[-1])
        curr = info.get("regularMarketPrice") or info.get("currentPrice")
        if curr is None or not isinstance(curr, (int, float)):
            curr = hist_last
        else:
            curr = float(curr)
        chg = curr - start_price
        chg_pct = (chg / start_price * 100) if start_price and start_price != 0 else 0
        color_line = POS if chg >= 0 else NEG

        self.lbl_name.config(text=info.get("longName") or info.get("shortName") or sym)
        self.lbl_tex.config(text=f"{sym}  ·  {info.get('exchange','')}")
        self.lbl_price.config(text=f"${curr:,.2f}")
        sign = "+" if chg >= 0 else ""
        self.lbl_chg.config(text=f"{sign}{chg:.2f} ({sign}{chg_pct:.2f}%)", fg=color_line)

        self.ax.clear()
        self.axv.clear()
        self._style_ax(self.ax)
        self._style_ax(self.axv)

        ct = self.chart_type.get()
        closes = hist["Close"]

        if ct == "Candle" and all(c in hist.columns for c in ["Open","High","Low","Close"]):
            self._draw_candles(hist)
        elif ct == "Area":
            self.ax.fill_between(hist.index, closes, closes.min(), color=color_line, alpha=0.15)
            self.ax.plot(hist.index, closes, color=color_line, linewidth=1.8)
        else:
            self.ax.plot(hist.index, closes, color=color_line, linewidth=1.8)

        if "Volume" in hist.columns and hist["Volume"].sum() > 0:
            try:
                if "Open" in hist.columns:
                    vol_colors = [POS if hist["Close"].iloc[i] >= hist["Open"].iloc[i] else NEG
                                  for i in range(len(hist))]
                else:
                    vol_colors = [color_line] * len(hist)
                self.axv.bar(hist.index, hist["Volume"], color=vol_colors, alpha=0.5, width=0.8)
                self.axv.set_ylabel("VOL", color=FG_DIM, fontsize=7)
            except:
                pass

        self.ax.set_title(f"{sym}  ·  {r}", color=FG_DIM, fontsize=9, pad=6)
        plt.setp(self.ax.get_xticklabels(), visible=False)
        self.canvas.draw()

        # Stats
        for w in self.stats_frame.winfo_children():
            w.destroy()
        stats = [
            ("Mkt Cap",  fmt_big(info.get("marketCap"))),
            ("P/E",      f"{info.get('trailingPE','N/A'):.1f}" if isinstance(info.get("trailingPE"), float) else "N/A"),
            ("EPS TTM",  f"${info.get('epsTrailingTwelveMonths','N/A')}"),
            ("52W High", f"${info.get('fiftyTwoWeekHigh','N/A')}"),
            ("52W Low",  f"${info.get('fiftyTwoWeekLow','N/A')}"),
            ("Avg Vol",  fmt_big(info.get("averageVolume","N/A")).replace("$","")),
            ("Div Yld",  f"{info.get('dividendYield',0)*100:.2f}%" if info.get("dividendYield") else "N/A"),
            ("Beta",     f"{info.get('beta','N/A')}"),
            ("Sector",   info.get("sector","N/A")),
            ("Country",  info.get("country","N/A")),
        ]
        for key, val in stats:
            row = tk.Frame(self.stats_frame, bg=PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=key, fg=FG_DIM, bg=PANEL, font=("Consolas", 9),
                     width=10, anchor="w").pack(side="left")
            tk.Label(row, text=str(val), fg=FG, bg=PANEL, font=("Consolas", 9, "bold"),
                     anchor="w").pack(side="left", padx=4)

        self.status_var.set(f"{sym} loaded  ·  {datetime.now().strftime('%H:%M:%S')}")

    def _draw_candles(self, hist):
        for i, (idx, row) in enumerate(hist.iterrows()):
            o, h, l, c = row["Open"], row["High"], row["Low"], row["Close"]
            color = POS if c >= o else NEG
            self.ax.plot([i, i], [l, h], color=color, linewidth=0.8)
            rect = mpatches.Rectangle((i-0.35, min(o,c)), 0.7, abs(c-o),
                                       facecolor=color, edgecolor=color, linewidth=0)
            self.ax.add_patch(rect)
        n = len(hist)
        self.ax.set_xlim(-1, n)
        step = max(1, n // 8)
        self.ax.set_xticks(range(0, n, step))
        self.ax.set_xticklabels(
            [hist.index[i].strftime("%b %d") for i in range(0, n, step)],
            fontsize=7, color=FG_DIM, rotation=30)

    def _analysis_err(self, msg):
        self._loading = False
        self.status_var.set(f"Error: {msg}")

    # ═══════════════════════════════════════════════
    # TAB 2 — COMPANY
    # ═══════════════════════════════════════════════
    def _build_company_tab(self, tab):
        ctrl = tk.Frame(tab, bg=BG, padx=14, pady=10)
        ctrl.pack(fill="x")
        tk.Label(ctrl, text="COMPANY PROFILE", fg=ACCENT, bg=BG, font=FONT_TITLE).pack(side="left")
        self._btn(ctrl, "LOAD CURRENT SYMBOL", lambda: self._load_company_info(self.current_sym.get()), ACCENT, BG).pack(side="right")

        outer, self.company_inner, _ = scrollable(tab)
        outer.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._load_company_info("AAPL")

    def _load_company_info(self, sym):
        sym = sym.upper()
        for w in self.company_inner.winfo_children():
            w.destroy()
        tk.Label(self.company_inner, text=f"Loading {sym}…", fg=FG_DIM, bg=BG,
                 font=FONT_MONO, pady=20).pack()
        self.status_var.set(f"Loading company: {sym}…")
        threading.Thread(target=self._fetch_company, args=(sym,), daemon=True).start()

    def _fetch_company(self, sym):
        try:
            info = yf.Ticker(sym).info
        except:
            info = {}
        offline = get_company_info(sym)
        self.after(0, lambda: self._render_company(sym, info, offline))

    def _render_company(self, sym, info, offline):
        for w in self.company_inner.winfo_children():
            w.destroy()

        name = info.get("longName") or info.get("shortName") or sym

        # Hero
        hero = tk.Frame(self.company_inner, bg=PANEL, pady=22, padx=24)
        hero.pack(fill="x", pady=(0, 10))
        tk.Label(hero, text=name, font=("Courier", 18, "bold"), fg=ACCENT, bg=PANEL).pack(anchor="w")
        tk.Label(hero, text=f"{sym}  ·  {info.get('exchange','')}  ·  {info.get('sector','')}",
                 fg=FG_DIM, bg=PANEL, font=("Consolas", 10)).pack(anchor="w", pady=(4,0))

        # Key stats
        stats_row = tk.Frame(self.company_inner, bg=BG)
        stats_row.pack(fill="x", pady=(0, 10))
        emp_raw = info.get("fullTimeEmployees")
        emp_str = f"{emp_raw:,}" if isinstance(emp_raw, int) else offline.get("employees", "N/A")
        city = info.get("city","")
        state = info.get("state","")
        hq = (city + (", "+state if state else "")) or offline.get("hq","N/A")
        card_data = [
            ("Market Cap",  fmt_big(info.get("marketCap"))),
            ("Revenue",     fmt_big(info.get("totalRevenue"))),
            ("Net Income",  fmt_big(info.get("netIncomeToCommon"))),
            ("Employees",   emp_str),
            ("Founded",     offline.get("founded","N/A")),
            ("HQ",          hq),
            ("P/E Ratio",   f"{info.get('trailingPE','N/A'):.1f}" if isinstance(info.get("trailingPE"), float) else "N/A"),
            ("EPS TTM",     f"${info.get('epsTrailingTwelveMonths','N/A')}"),
        ]
        for i, (lbl, val) in enumerate(card_data):
            c = stat_card(stats_row, lbl, str(val), ACCENT if i < 3 else FG)
            c.grid(row=0, column=i, padx=3, pady=3, sticky="nsew")
            stats_row.columnconfigure(i, weight=1)

        # About
        sc = tk.Frame(self.company_inner, bg=CARD, padx=22, pady=18)
        sc.pack(fill="x", pady=(0, 8))
        tk.Label(sc, text="📋  ABOUT", fg=BLUE, bg=CARD, font=FONT_SMALL).pack(anchor="w")
        summary = info.get("longBusinessSummary") or offline.get("summary", "No info available.")
        tk.Label(sc, text=summary, fg=FG, bg=CARD,
                 font=("Consolas", 10), wraplength=1060, justify="left").pack(anchor="w", pady=(8, 0))

        # Financial highlights
        fc = tk.Frame(self.company_inner, bg=CARD, padx=22, pady=18)
        fc.pack(fill="x", pady=(0, 8))
        tk.Label(fc, text="📊  FINANCIAL HIGHLIGHTS", fg=POS, bg=CARD, font=FONT_SMALL).pack(anchor="w", pady=(0, 10))
        fg2 = tk.Frame(fc, bg=CARD)
        fg2.pack(fill="x")
        fin_items = [
            ("Gross Margin",      f"{info.get('grossMargins',0)*100:.1f}%"     if info.get('grossMargins')      else "N/A"),
            ("Operating Margin",  f"{info.get('operatingMargins',0)*100:.1f}%" if info.get('operatingMargins')  else "N/A"),
            ("Profit Margin",     f"{info.get('profitMargins',0)*100:.1f}%"    if info.get('profitMargins')     else "N/A"),
            ("Return on Equity",  f"{info.get('returnOnEquity',0)*100:.1f}%"   if info.get('returnOnEquity')    else "N/A"),
            ("Debt/Equity",       str(info.get('debtToEquity','N/A'))),
            ("Current Ratio",     str(info.get('currentRatio','N/A'))),
            ("Free Cash Flow",    fmt_big(info.get("freeCashflow"))),
            ("Insider Ownership", f"{info.get('heldPercentInsiders',0)*100:.1f}%" if info.get('heldPercentInsiders') else "N/A"),
        ]
        for i, (k, v) in enumerate(fin_items):
            cell = tk.Frame(fg2, bg=PANEL, padx=12, pady=10)
            cell.grid(row=i//4, column=i%4, padx=4, pady=4, sticky="nsew")
            tk.Label(cell, text=k, fg=FG_DIM, bg=PANEL, font=FONT_SMALL).pack(anchor="w")
            tk.Label(cell, text=v, fg=FG, bg=PANEL, font=FONT_NUM).pack(anchor="w", pady=(4, 0))
            fg2.columnconfigure(i%4, weight=1)

        self.status_var.set(f"Company loaded: {sym}")

    # ═══════════════════════════════════════════════
    # TAB 3 — PORTFOLIO
    # ═══════════════════════════════════════════════
    def _build_portfolio_tab(self, tab):
        ctrl = tk.Frame(tab, bg=BG, padx=14, pady=10)
        ctrl.pack(fill="x")
        tk.Label(ctrl, text="PORTFOLIO", fg=ACCENT, bg=BG, font=FONT_TITLE).pack(side="left")
        self._btn(ctrl, "↻ REFRESH",  self._refresh_portfolio,     ACCENT, BG).pack(side="right")
        self._btn(ctrl, "📈 GROWTH",  self._show_portfolio_growth, PANEL,  POS).pack(side="right", padx=4)
        self._btn(ctrl, "✕ REMOVE",   self._remove_holding,        PANEL,  NEG).pack(side="right", padx=4)
        self._btn(ctrl, "＋ ADD",     self._add_holding_dialog,    PANEL,  FG ).pack(side="right", padx=4)

        self.port_cards = tk.Frame(tab, bg=BG, padx=14)
        self.port_cards.pack(fill="x", pady=(0, 8))

        cols = ("Ticker","Shares","Avg Cost","Price","Value","P&L","Return%","Date")
        self.p_tree = ttk.Treeview(tab, columns=cols, show="headings", selectmode="browse")
        widths = [100, 80, 110, 110, 130, 130, 100, 110]
        for c, w in zip(cols, widths):
            self.p_tree.heading(c, text=c)
            self.p_tree.column(c, width=w, anchor="center")
        self.p_tree.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        self.p_tree.tag_configure("pos", foreground=POS)
        self.p_tree.tag_configure("neg", foreground=NEG)
        self.p_tree.bind("<Double-1>", lambda e: self._on_port_double())

        self.port_fig = Figure(figsize=(14, 2.8), facecolor=BG)
        self.port_ax  = self.port_fig.add_subplot(121)
        self.port_ax2 = self.port_fig.add_subplot(122)
        self.port_canvas = FigureCanvasTkAgg(self.port_fig, master=tab)
        self.port_canvas.get_tk_widget().pack(fill="x", padx=14, pady=(0, 6))

        self._refresh_portfolio()

    def _on_port_double(self):
        sel = self.p_tree.selection()
        if sel:
            self._load_symbol(self.p_tree.item(sel[0])["values"][0])

    def _refresh_portfolio(self):
        self.status_var.set("Refreshing portfolio…")
        threading.Thread(target=self._do_refresh_portfolio, daemon=True).start()

    def _do_refresh_portfolio(self):
        rows, total_v, total_pl = self.portfolio.snapshot()
        self.after(0, lambda: self._populate_portfolio(rows, total_v, total_pl))

    def _populate_portfolio(self, rows, total_v, total_pl):
        for i in self.p_tree.get_children():
            self.p_tree.delete(i)
        allocation = []
        for r in rows:
            ticker, shares, avg, price, value, pl, pct = r
            sign = "+" if pl >= 0 else ""
            tag = "pos" if pl >= 0 else "neg"
            self.p_tree.insert("", "end", values=(
                ticker, f"{shares:.4g}", f"${avg:.2f}", f"${price:.2f}",
                f"${value:,.2f}", f"{sign}${abs(pl):,.2f}", f"{pct:+.2f}%",
                self.portfolio.holdings.get(ticker, Holding(ticker,0,0)).purchase_date
            ), tags=(tag,))
            allocation.append((ticker, value, pl))

        for w in self.port_cards.winfo_children():
            w.destroy()
        pl_color = POS if total_pl >= 0 else NEG
        sign = "+" if total_pl >= 0 else ""
        total_cost = total_v - total_pl
        ret_pct = (total_pl / total_cost * 100) if total_cost else 0
        for lbl, val, col in [
            ("Total Value", f"${total_v:,.2f}", ACCENT),
            ("Total P&L",   f"{sign}${abs(total_pl):,.2f}", pl_color),
            ("Total Return",f"{ret_pct:+.2f}%", pl_color),
            ("Holdings",    str(len(self.portfolio.holdings)), FG),
        ]:
            stat_card(self.port_cards, lbl, val, col, 13).pack(side="left", padx=(0, 6), pady=4)

        self.pnl_sidebar.config(text=f"Portfolio P&L\n{sign}${abs(total_pl):,.2f}", fg=pl_color)

        # Charts
        self.port_ax.clear()
        self.port_ax2.clear()
        if allocation:
            labels = [a[0] for a in allocation]
            values = [max(a[1], 0) for a in allocation]
            pl_vals = [a[2] for a in allocation]
            colors  = [ACCENT, ACCENT2, BLUE, POS, ORANGE, NEG, "#a78bfa", "#34d399"] * 3
            colors  = colors[:len(labels)]
            if sum(values) > 0:
                self.port_ax.pie(values, labels=labels, colors=colors,
                                  autopct="%1.1f%%", pctdistance=0.75, startangle=140,
                                  textprops={"color": FG, "fontsize": 8},
                                  wedgeprops={"linewidth": 0.5, "edgecolor": BG})
            self.port_ax.set_facecolor(BG)
            self.port_ax.set_title("Allocation", color=FG_DIM, fontsize=9)

            bar_colors = [POS if v >= 0 else NEG for v in pl_vals]
            self.port_ax2.bar(labels, pl_vals, color=bar_colors, edgecolor=BG, linewidth=0.5)
            self.port_ax2.set_facecolor(BG)
            self.port_ax2.tick_params(colors=FG_DIM, labelsize=8)
            for sp in self.port_ax2.spines.values(): sp.set_color(BORDER)
            self.port_ax2.set_title("P&L by Holding", color=FG_DIM, fontsize=9)
            self.port_ax2.axhline(0, color=BORDER, linewidth=0.8)
            self.port_ax2.set_ylabel("$", color=FG_DIM, fontsize=8)
            self.port_fig.patch.set_facecolor(BG)
            self.port_fig.subplots_adjust(left=0.04, right=0.98, top=0.9, bottom=0.2)

        self.port_canvas.draw()
        self.status_var.set("Portfolio updated.")

    def _show_portfolio_growth(self):
        win = tk.Toplevel(self)
        win.title("Portfolio Growth vs Benchmark")
        win.geometry("1050x560")
        win.configure(bg=BG)
        tk.Label(win, text="PORTFOLIO GROWTH", fg=ACCENT, bg=BG,
                 font=FONT_TITLE, padx=20, pady=14).pack(anchor="w")

        pf = tk.Frame(win, bg=BG, padx=20)
        pf.pack(anchor="w")

        fig_g = Figure(figsize=(10, 5), facecolor=BG)
        g_ax  = fig_g.add_subplot(111)
        fig_g.subplots_adjust(left=0.08, right=0.97, top=0.93, bottom=0.12)
        g_canvas = FigureCanvasTkAgg(fig_g, master=win)
        g_canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=10)

        for p in ["3mo","6mo","1y","2y","5y"]:
            tk.Button(pf, text=p.upper(), bg=PANEL, fg=FG_DIM, font=("Consolas",9,"bold"),
                      padx=8, pady=4, borderwidth=0, cursor="hand2",
                      command=lambda x=p: threading.Thread(
                          target=self._fetch_growth, args=(x, g_ax, g_canvas), daemon=True).start()
                      ).pack(side="left", padx=2)

        threading.Thread(target=self._fetch_growth, args=("1y", g_ax, g_canvas), daemon=True).start()

    def _fetch_growth(self, period, ax, canvas):
        try:
            dates, totals = self.portfolio.historical_values(period)
            spy = yf.Ticker("SPY").history(period=period)
            self.after(0, lambda: self._render_growth(dates, totals, spy, period, ax, canvas))
        except Exception as e:
            self.after(0, lambda: self.status_var.set(f"Growth error: {e}"))

    def _render_growth(self, dates, totals, spy, period, ax, canvas):
        ax.clear()
        self._style_ax(ax)
        if totals is not None and len(totals) > 1:
            base = totals[0] or 1
            pct = (totals / base - 1) * 100
            ax.plot(dates, pct, color=ACCENT, linewidth=2.2, label="My Portfolio")
            ax.fill_between(dates, pct, 0, color=ACCENT, alpha=0.08)
        if not spy.empty and len(spy) > 1:
            sb = spy["Close"].values[0] or 1
            sp = (spy["Close"].values / sb - 1) * 100
            ax.plot(spy.index, sp, color=BLUE, linewidth=1.4, linestyle="--", label="SPY (Benchmark)")
        ax.axhline(0, color=BORDER, linewidth=0.8)
        ax.set_ylabel("% Return", color=FG_DIM, fontsize=9)
        ax.set_title(f"Portfolio vs SPY  ·  {period.upper()}", color=FG_DIM, fontsize=10)
        ax.legend(fontsize=8, facecolor=PANEL, labelcolor=FG, edgecolor=BORDER)
        canvas.draw()
        self.status_var.set("Growth chart loaded.")

    def _add_holding_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Add Holding")
        dlg.geometry("360x270")
        dlg.configure(bg=PANEL)
        dlg.grab_set()
        tk.Label(dlg, text="ADD HOLDING", fg=ACCENT, bg=PANEL, font=FONT_TITLE).pack(pady=(18, 12))
        form = tk.Frame(dlg, bg=PANEL)
        form.pack(padx=28)
        entries = {}
        for i, (lbl, key) in enumerate([("Ticker:", "t"), ("Shares:", "s"), ("Avg Price $:", "p"), ("Date (YYYY-MM-DD):", "d")]):
            tk.Label(form, text=lbl, fg=FG_DIM, bg=PANEL, font=("Consolas",10)).grid(row=i, column=0, sticky="w", pady=5)
            e = styled_entry(form, font=("Consolas",10), bg=CARD, fg=FG, insertbackground=ACCENT, borderwidth=0, width=16)
            e.grid(row=i, column=1, padx=8)
            entries[key] = e
        def confirm():
            try:
                t = entries["t"].get().strip().upper()
                s = float(entries["s"].get())
                p = float(entries["p"].get())
                d = entries["d"].get().strip() or datetime.now().strftime("%Y-%m-%d")
                if not t: raise ValueError
                self.portfolio.add(t, s, p, d)
                dlg.destroy()
                self._refresh_portfolio()
            except ValueError:
                messagebox.showerror("Invalid Input", "Check your entries.", parent=dlg)
        self._btn(dlg, "ADD", confirm, ACCENT, BG).pack(pady=14)

    def _remove_holding(self):
        sel = self.p_tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a holding to remove.")
            return
        ticker = self.p_tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Confirm", f"Remove {ticker} from portfolio?"):
            self.portfolio.remove(ticker)
            self._refresh_portfolio()

    def _quick_add_to_portfolio(self):
        sym = self._get_current_ticker()
        dlg = tk.Toplevel(self)
        dlg.title(f"Add {sym}")
        dlg.geometry("340x220")
        dlg.configure(bg=PANEL)
        dlg.grab_set()
        tk.Label(dlg, text=f"ADD {sym}", fg=ACCENT, bg=PANEL, font=FONT_TITLE).pack(pady=(18, 12))
        form = tk.Frame(dlg, bg=PANEL)
        form.pack(padx=28)
        entries = {}
        for i, (lbl, key) in enumerate([("Shares:", "s"), ("Avg Price $:", "p")]):
            tk.Label(form, text=lbl, fg=FG_DIM, bg=PANEL, font=("Consolas",10)).grid(row=i, column=0, sticky="w", pady=5)
            e = styled_entry(form, font=("Consolas",10), bg=CARD, fg=FG, insertbackground=ACCENT, borderwidth=0, width=14)
            e.grid(row=i, column=1, padx=8)
            entries[key] = e
        def confirm():
            try:
                self.portfolio.add(sym, float(entries["s"].get()), float(entries["p"].get()))
                dlg.destroy()
                self._refresh_portfolio()
            except ValueError:
                messagebox.showerror("Invalid Input", "Enter valid numbers.", parent=dlg)
        self._btn(dlg, "CONFIRM", confirm, ACCENT, BG).pack(pady=14)

    # ═══════════════════════════════════════════════
    # TAB 4 — MARKETS
    # ═══════════════════════════════════════════════
    def _build_markets_tab(self, tab):
        ctrl = tk.Frame(tab, bg=BG, padx=14, pady=10)
        ctrl.pack(fill="x")
        tk.Label(ctrl, text="MARKET OVERVIEW", fg=ACCENT, bg=BG, font=FONT_TITLE).pack(side="left")
        self._btn(ctrl, "↻ REFRESH", self._refresh_markets, ACCENT, BG).pack(side="right")

        content = tk.Frame(tab, bg=BG)
        content.pack(fill="both", expand=True, padx=14)

        # Heatmap
        left = tk.Frame(content, bg=BG, width=400)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)
        tk.Label(left, text="SECTOR HEATMAP", fg=FG_DIM, bg=BG, font=FONT_SMALL).pack(anchor="w", pady=(0,6))
        self.heatmap_fig = Figure(figsize=(4, 5.5), facecolor=BG)
        self.heatmap_ax  = self.heatmap_fig.add_subplot(111)
        self.heatmap_canvas = FigureCanvasTkAgg(self.heatmap_fig, master=left)
        self.heatmap_canvas.get_tk_widget().pack(fill="both", expand=True)

        # Table
        right = tk.Frame(content, bg=BG)
        right.pack(side="right", fill="both", expand=True)
        cols = ("Name","Symbol","Price","Chg $","Chg %","Volume","52W High","52W Low")
        self.m_tree = ttk.Treeview(right, columns=cols, show="headings", selectmode="browse")
        for c, w in zip(cols, [180,90,110,100,90,120,110,110]):
            self.m_tree.heading(c, text=c)
            self.m_tree.column(c, width=w, anchor="center")
        self.m_tree.pack(fill="both", expand=True)
        self.m_tree.tag_configure("pos", foreground=POS)
        self.m_tree.tag_configure("neg", foreground=NEG)
        self.m_tree.bind("<Double-1>", lambda e: self._market_double())

    MARKET_SYMS = [
        ("S&P 500 ETF","SPY"),("Nasdaq 100 ETF","QQQ"),("Dow Jones ETF","DIA"),
        ("Russell 2000","IWM"),("VIX","^VIX"),("Gold","GLD"),("Oil","USO"),
        ("Bitcoin","BTC-USD"),("Ethereum","ETH-USD"),("Solana","SOL-USD"),
        ("Apple","AAPL"),("NVIDIA","NVDA"),("Microsoft","MSFT"),
        ("Tesla","TSLA"),("Meta","META"),("Amazon","AMZN"),("AMD","AMD"),
        ("Netflix","NFLX"),("Alphabet","GOOGL"),("Broadcom","AVGO"),
    ]
    SECTORS = [
        ("Technology","XLK"),("Healthcare","XLV"),("Financials","XLF"),
        ("Energy","XLE"),("Utilities","XLU"),("Consumer Disc.","XLY"),
        ("Industrials","XLI"),("Materials","XLB"),("Real Estate","XLRE"),
        ("Comm. Services","XLC"),("Staples","XLP"),
    ]

    def _market_double(self):
        sel = self.m_tree.selection()
        if sel:
            self._load_symbol(self.m_tree.item(sel[0])["values"][1])

    def _refresh_markets(self):
        for i in self.m_tree.get_children():
            self.m_tree.delete(i)
        self.status_var.set("Fetching market data…")
        threading.Thread(target=self._fetch_markets, daemon=True).start()
        threading.Thread(target=self._fetch_heatmap, daemon=True).start()

    def _fetch_markets(self):
        rows = []
        for name, sym in self.MARKET_SYMS:
            try:
                t = yf.Ticker(sym)
                d = t.history(period="2d")
                if d.empty: continue
                curr = float(d["Close"].iloc[-1])
                prev = float(d["Close"].iloc[-2]) if len(d) > 1 else curr
                chg = curr - prev
                chg_pct = (chg / prev * 100) if prev else 0
                vol = int(d["Volume"].iloc[-1]) if "Volume" in d.columns else 0
                info = t.info
                h52 = info.get("fiftyTwoWeekHigh","N/A")
                l52 = info.get("fiftyTwoWeekLow","N/A")
                sign = "+" if chg >= 0 else ""
                rows.append((name, sym,
                              f"${curr:,.2f}" if curr < 100000 else f"${curr:,.0f}",
                              f"{sign}{chg:.2f}", f"{sign}{chg_pct:.2f}%",
                              f"{vol:,}", f"${h52}", f"${l52}", chg >= 0))
            except:
                pass
        self.after(0, lambda: self._populate_markets(rows))

    def _populate_markets(self, rows):
        for i in self.m_tree.get_children():
            self.m_tree.delete(i)
        for r in rows:
            self.m_tree.insert("", "end", values=r[:-1], tags=("pos" if r[-1] else "neg",))
        self.status_var.set(f"Markets updated  ·  {datetime.now().strftime('%H:%M:%S')}")

    def _fetch_heatmap(self):
        results = []
        for name, sym in self.SECTORS:
            try:
                d = yf.Ticker(sym).history(period="2d")
                if d.empty or len(d) < 2: continue
                curr, prev = float(d["Close"].iloc[-1]), float(d["Close"].iloc[-2])
                results.append((name, (curr-prev)/prev*100))
            except:
                pass
        self.after(0, lambda: self._render_heatmap(results))

    def _render_heatmap(self, data):
        self.heatmap_ax.clear()
        if not data: return
        self.heatmap_ax.set_facecolor(BG)
        names = [d[0] for d in data]
        vals  = [d[1] for d in data]
        sorted_data = sorted(zip(vals, names))
        vals  = [x[0] for x in sorted_data]
        names = [x[1] for x in sorted_data]
        colors = [POS if v >= 0 else NEG for v in vals]
        bars = self.heatmap_ax.barh(range(len(names)), vals, color=colors, edgecolor=BG, height=0.7)
        self.heatmap_ax.set_yticks(range(len(names)))
        self.heatmap_ax.set_yticklabels(names, color=FG, fontsize=9)
        self.heatmap_ax.tick_params(colors=FG_DIM, labelsize=8)
        for sp in self.heatmap_ax.spines.values(): sp.set_color(BORDER)
        self.heatmap_ax.axvline(0, color=BORDER, linewidth=0.8)
        self.heatmap_ax.set_xlabel("% Change", color=FG_DIM, fontsize=8)
        self.heatmap_ax.set_title("Sector Performance", color=FG_DIM, fontsize=9)
        for bar, val in zip(bars, vals):
            self.heatmap_ax.text(
                bar.get_width() + (0.04 if val >= 0 else -0.04),
                bar.get_y() + bar.get_height()/2,
                f"{val:+.2f}%", va="center",
                ha="left" if val >= 0 else "right",
                color=FG, fontsize=7)
        self.heatmap_fig.patch.set_facecolor(BG)
        self.heatmap_fig.subplots_adjust(left=0.42, right=0.91, top=0.93, bottom=0.1)
        self.heatmap_canvas.draw()

    # ═══════════════════════════════════════════════
    # TAB 5 — NEWS
    # ═══════════════════════════════════════════════
    def _build_news_tab(self, tab):
        ctrl = tk.Frame(tab, bg=BG, padx=14, pady=10)
        ctrl.pack(fill="x")
        tk.Label(ctrl, text="MARKET NEWS", fg=ACCENT, bg=BG, font=FONT_TITLE).pack(side="left")
        self._btn(ctrl, "↻ REFRESH", lambda: self._load_news(self.news_topic.get()), ACCENT, BG).pack(side="right")

        topics_f = tk.Frame(tab, bg=BG, padx=14)
        topics_f.pack(fill="x", pady=(0, 6))
        self.news_topic = tk.StringVar(value="stock market")
        for t in ["stock market","Federal Reserve","earnings","crypto","economy",
                  "S&P 500","tech stocks","AI stocks","bonds","commodities"]:
            tk.Button(topics_f, text=t.upper(), command=lambda x=t: self._load_news(x),
                      bg=PANEL, fg=FG_DIM, font=("Consolas", 8, "bold"),
                      padx=7, pady=4, borderwidth=0, cursor="hand2",
                      activebackground=ACCENT, activeforeground=BG).pack(side="left", padx=2, pady=2)

        outer, self.news_inner, _ = scrollable(tab)
        outer.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self._load_news("stock market")

    def _load_news(self, topic):
        self.news_topic.set(topic)
        for w in self.news_inner.winfo_children():
            w.destroy()
        tk.Label(self.news_inner, text=f"Loading news: {topic}…",
                 fg=FG_DIM, bg=BG, font=FONT_MONO, pady=20).pack()
        self.status_var.set(f"Fetching news: {topic}…")
        threading.Thread(target=self._fetch_news, args=(topic,), daemon=True).start()

    def _fetch_news(self, topic):
        try:
            q = urllib.parse.quote(topic)
            url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)
            self.after(0, lambda: self._populate_news(feed.entries[:16], topic))
        except Exception as e:
            self.after(0, lambda: self.status_var.set(f"News error: {e}"))

    def _populate_news(self, entries, topic):
        for w in self.news_inner.winfo_children():
            w.destroy()
        if not entries:
            tk.Label(self.news_inner, text="No articles found.", fg=FG_DIM, bg=BG).pack(pady=30)
            return
        stripe_colors = [ACCENT, ACCENT2, BLUE, POS, ORANGE, NEG]
        for i, entry in enumerate(entries):
            card = tk.Frame(self.news_inner, bg=CARD,
                            highlightbackground=BORDER, highlightthickness=1)
            card.pack(fill="x", padx=8, pady=5)
            # Color stripe
            stripe = tk.Frame(card, bg=stripe_colors[i % len(stripe_colors)], width=4)
            stripe.pack(side="left", fill="y")

            body = tk.Frame(card, bg=CARD, padx=16, pady=13)
            body.pack(side="left", fill="x", expand=True)

            # Source + date
            src = getattr(entry, "source", None)
            src_name = src.title.upper() if src else "NEWS"
            pub = getattr(entry, "published", "")[:16]
            tk.Label(body, text=f"{src_name}   ·   {pub}", fg=ACCENT2, bg=CARD,
                     font=("Consolas", 8, "bold")).pack(anchor="w")

            # Title
            title_lbl = tk.Label(body, text=entry.title, fg=FG, bg=CARD,
                                   font=("Helvetica", 12, "bold"),
                                   wraplength=1050, justify="left", cursor="hand2")
            title_lbl.pack(anchor="w", pady=(5, 0))
            title_lbl.bind("<Button-1>", lambda e, l=entry.link: webbrowser.open(l))
            title_lbl.bind("<Enter>", lambda e, w=title_lbl: w.config(fg=ACCENT))
            title_lbl.bind("<Leave>", lambda e, w=title_lbl: w.config(fg=FG))

            # Summary
            summary = getattr(entry, "summary", "")
            if summary:
                clean = re.sub(r"<[^>]+>", "", summary)[:260]
                tk.Label(body, text=clean + "…", fg=FG_DIM, bg=CARD,
                         font=("Consolas", 9), wraplength=1050, justify="left").pack(anchor="w", pady=(4, 0))

        self.status_var.set(f"Loaded {len(entries)} articles: {topic}")

    # ═══════════════════════════════════════════════
    # TAB 6 — AI INSIGHT
    # ═══════════════════════════════════════════════
    def _build_ai_tab(self, tab):
        ctrl = tk.Frame(tab, bg=BG, padx=14, pady=10)
        ctrl.pack(fill="x")
        tk.Label(ctrl, text="TECHNICAL ANALYSIS", fg=ACCENT, bg=BG, font=FONT_TITLE).pack(side="left")
        self._btn(ctrl, "▶ RUN ANALYSIS", self._run_ai, ACCENT, BG).pack(side="right")
        tk.Label(tab, text="Statistical analysis via technical indicators. NOT financial advice.",
                 fg=FG_DIM, bg=BG, font=("Consolas", 9), padx=14).pack(anchor="w", pady=(0, 6))
        outer, self.ai_inner, _ = scrollable(tab)
        outer.pack(fill="both", expand=True, padx=14, pady=(0, 8))

    def _run_ai(self):
        sym = self.current_sym.get().upper()
        for w in self.ai_inner.winfo_children():
            w.destroy()
        tk.Label(self.ai_inner, text=f"Computing analysis for {sym}…",
                 fg=FG_DIM, bg=BG, font=FONT_MONO, pady=20).pack()
        threading.Thread(target=self._fetch_ai, args=(sym,), daemon=True).start()

    def _fetch_ai(self, sym):
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="2y")
            info = t.info
            if hist.empty or len(hist) < 20:
                raise ValueError("Not enough data.")
            self.after(0, lambda: self._render_ai(sym, hist["Close"].values.astype(float), hist, info))
        except Exception as e:
            self.after(0, lambda: self.status_var.set(f"AI error: {e}"))

    def _render_ai(self, sym, closes, hist, info):
        for w in self.ai_inner.winfo_children():
            w.destroy()

        curr  = closes[-1]
        sma20  = np.mean(closes[-20:])
        sma50  = np.mean(closes[-50:]) if len(closes) >= 50 else None
        sma200 = np.mean(closes[-200:]) if len(closes) >= 200 else None

        # RSI
        delta = np.diff(closes)
        avg_g = np.mean(np.maximum(delta[-14:], 0)) if len(delta) >= 14 else 1e-9
        avg_l = np.mean(np.maximum(-delta[-14:], 0)) if len(delta) >= 14 else 1e-9
        rsi   = 100 - (100 / (1 + avg_g / max(avg_l, 1e-9)))

        # MACD
        def ema(s, n):
            k = 2/(n+1); e = [s[0]]
            for p in s[1:]: e.append(p*k + e[-1]*(1-k))
            return np.array(e)
        macd_line  = ema(closes, 12) - ema(closes, 26)
        signal_line = ema(macd_line, 9)
        macd_hist   = macd_line - signal_line

        # Bollinger
        bb_mean = np.mean(closes[-20:])
        bb_std  = np.std(closes[-20:])
        bb_up, bb_lo = bb_mean + 2*bb_std, bb_mean - 2*bb_std

        # Metrics
        returns = np.diff(closes) / closes[:-1]
        vol_ann = np.std(returns[-30:]) * np.sqrt(252) * 100 if len(returns) >= 30 else 0
        sharpe  = (np.mean(returns[-252:]) / max(np.std(returns[-252:]),1e-9)) * np.sqrt(252) if len(returns)>=252 else 0
        mom_1m  = (curr/closes[-22]-1)*100  if len(closes)>=22  else 0
        mom_3m  = (curr/closes[-63]-1)*100  if len(closes)>=63  else 0
        mom_6m  = (curr/closes[-126]-1)*100 if len(closes)>=126 else 0
        mom_1y  = (curr/closes[-252]-1)*100 if len(closes)>=252 else 0
        max_dd  = self._max_drawdown(closes)

        signals = {
            "Price > SMA20":     curr > sma20,
            "Price > SMA50":     sma50 is not None and curr > sma50,
            "Price > SMA200":    sma200 is not None and curr > sma200,
            "RSI < 70 (not OB)": rsi < 70,
            "RSI > 30 (not OS)": rsi > 30,
            "MACD Bullish":      float(macd_line[-1]) > float(signal_line[-1]),
            "Price above BB Mid":curr > bb_mean,
            "1M Momentum +":     mom_1m > 0,
            "3M Momentum +":     mom_3m > 0,
        }
        bull_count = sum(signals.values())
        bull_pct   = bull_count / len(signals) * 100
        direction  = ("STRONG BULLISH" if bull_pct >= 78 else "BULLISH" if bull_pct >= 56 else
                      "NEUTRAL" if bull_pct >= 44 else "BEARISH" if bull_pct >= 22 else "STRONG BEARISH")
        dir_color  = POS if bull_pct >= 56 else (ORANGE if bull_pct >= 44 else NEG)

        # Signal card + RSI card
        top = tk.Frame(self.ai_inner, bg=BG)
        top.pack(fill="x", pady=(0, 10))

        sig = tk.Frame(top, bg=CARD, padx=26, pady=20,
                        highlightbackground=dir_color, highlightthickness=2)
        sig.pack(side="left", padx=(0, 10))
        tk.Label(sig, text=sym, fg=FG_DIM, bg=CARD, font=FONT_SMALL).pack()
        tk.Label(sig, text=direction, fg=dir_color, bg=CARD, font=("Courier", 19, "bold")).pack(pady=4)
        tk.Label(sig, text=f"{bull_count}/{len(signals)} signals bullish  ({bull_pct:.0f}%)",
                 fg=FG, bg=CARD, font=("Consolas", 10)).pack()
        bar_f = tk.Frame(sig, bg=PANEL, width=200, height=7)
        bar_f.pack(pady=(8, 0))
        bar_f.pack_propagate(False)
        fill_w = max(1, int(200 * bull_pct / 100))
        tk.Frame(bar_f, bg=dir_color, width=fill_w, height=7).place(x=0, y=0)

        rsi_col = POS if 30 < rsi < 70 else (ORANGE if rsi <= 30 else NEG)
        rsi_lbl = "NEUTRAL" if 30 < rsi < 70 else ("OVERSOLD" if rsi <= 30 else "OVERBOUGHT")
        rsi_card = tk.Frame(top, bg=CARD, padx=20, pady=20,
                             highlightbackground=BORDER, highlightthickness=1)
        rsi_card.pack(side="left", padx=(0, 10))
        tk.Label(rsi_card, text="RSI (14)", fg=FG_DIM, bg=CARD, font=FONT_SMALL).pack()
        tk.Label(rsi_card, text=f"{rsi:.1f}", fg=rsi_col, bg=CARD, font=("Courier",28,"bold")).pack()
        tk.Label(rsi_card, text=rsi_lbl, fg=rsi_col, bg=CARD, font=FONT_SMALL).pack()

        # Metrics grid
        mf = tk.Frame(top, bg=BG)
        mf.pack(side="left", fill="both", expand=True)
        metrics = [
            ("Volatility Ann",    f"{vol_ann:.1f}%",       FG),
            ("Sharpe Ratio",      f"{sharpe:.2f}",          POS if sharpe>1 else (ORANGE if sharpe>0 else NEG)),
            ("Max Drawdown",      f"{max_dd:.1f}%",         NEG if max_dd<-10 else ORANGE),
            ("BB Upper",          f"${bb_up:.2f}",          FG),
            ("BB Lower",          f"${bb_lo:.2f}",          FG),
            ("MACD",              f"{float(macd_line[-1]):.3f}", POS if float(macd_line[-1])>0 else NEG),
            ("1M Return",         f"{mom_1m:+.2f}%",        POS if mom_1m>=0 else NEG),
            ("3M Return",         f"{mom_3m:+.2f}%",        POS if mom_3m>=0 else NEG),
            ("6M Return",         f"{mom_6m:+.2f}%",        POS if mom_6m>=0 else NEG),
            ("1Y Return",         f"{mom_1y:+.2f}%",        POS if mom_1y>=0 else NEG),
            ("SMA 20",            f"${sma20:.2f}",           POS if curr>sma20 else NEG),
            ("SMA 50",            f"${sma50:.2f}" if sma50 else "N/A", POS if sma50 and curr>sma50 else NEG),
        ]
        for i, (lbl, val, col) in enumerate(metrics):
            stat_card(mf, lbl, val, col).grid(row=i//4, column=i%4, padx=3, pady=3, sticky="nsew")
            mf.columnconfigure(i%4, weight=1)

        # Signal checklist
        sf = tk.Frame(self.ai_inner, bg=CARD, padx=18, pady=14)
        sf.pack(fill="x", pady=(0, 8))
        tk.Label(sf, text="SIGNAL BREAKDOWN", fg=FG_DIM, bg=CARD, font=FONT_SMALL).pack(anchor="w", pady=(0, 8))
        grid_f = tk.Frame(sf, bg=CARD)
        grid_f.pack(fill="x")
        for i, (name, is_bull) in enumerate(signals.items()):
            cell = tk.Frame(grid_f, bg=PANEL, padx=10, pady=8)
            cell.grid(row=i//3, column=i%3, padx=4, pady=3, sticky="nsew")
            tk.Label(cell, text=f"{'✓' if is_bull else '✗'}  {name}",
                     fg=POS if is_bull else NEG, bg=PANEL, font=("Consolas", 9)).pack(anchor="w")
            grid_f.columnconfigure(i%3, weight=1)

        # Chart: price + SMAs + Bollinger / MACD
        fig_ai = Figure(figsize=(14, 5), facecolor=BG)
        fig_ai.subplots_adjust(left=0.05, right=0.97, top=0.93, bottom=0.1, hspace=0.05)
        gs2 = gridspec.GridSpec(2, 1, figure=fig_ai, height_ratios=[3,1], hspace=0.05)
        ax_p = fig_ai.add_subplot(gs2[0])
        ax_m = fig_ai.add_subplot(gs2[1], sharex=ax_p)
        for ax in [ax_p, ax_m]: self._style_ax(ax)

        n  = min(252, len(closes))
        xs = hist.index[-n:]
        ax_p.plot(xs, closes[-n:], color=FG_DIM, linewidth=1.2, label="Price")

        if len(closes) >= 20:
            ma20 = np.convolve(closes, np.ones(20)/20, "valid")
            ax_p.plot(hist.index[19:][-len(ma20):], ma20[-min(n,len(ma20)):],
                      color=BLUE, linewidth=1, label="SMA20")
        if sma50:
            ma50 = np.convolve(closes, np.ones(50)/50, "valid")
            ax_p.plot(hist.index[49:][-len(ma50):], ma50, color=ACCENT, linewidth=1, label="SMA50")
        if sma200:
            ma200 = np.convolve(closes, np.ones(200)/200, "valid")
            ax_p.plot(hist.index[199:][-len(ma200):], ma200, color=ACCENT2, linewidth=1, label="SMA200")

        ax_p.fill_between(xs, bb_up, bb_lo, alpha=0.05, color=BLUE, label="Bollinger")
        ax_p.legend(fontsize=7, facecolor=PANEL, labelcolor=FG, edgecolor=BORDER, ncol=5)
        ax_p.set_title(f"{sym} — Technical  (1Y shown)", color=FG_DIM, fontsize=9)
        ax_p.yaxis.tick_right()

        ax_m.plot(hist.index, macd_line, color=BLUE, linewidth=1, label="MACD")
        ax_m.plot(hist.index, signal_line, color=ORANGE, linewidth=1, label="Signal")
        ax_m.bar(hist.index, macd_hist,
                 color=[POS if v>=0 else NEG for v in macd_hist], alpha=0.6, width=1)
        ax_m.axhline(0, color=BORDER, linewidth=0.8)
        ax_m.set_ylabel("MACD", color=FG_DIM, fontsize=7)
        ax_m.legend(fontsize=7, facecolor=PANEL, labelcolor=FG, edgecolor=BORDER)
        ax_m.yaxis.tick_right()
        plt.setp(ax_p.get_xticklabels(), visible=False)
        fig_ai.patch.set_facecolor(BG)

        c_ai = FigureCanvasTkAgg(fig_ai, master=self.ai_inner)
        c_ai.get_tk_widget().pack(fill="x", pady=(0, 10))
        c_ai.draw()
        self.status_var.set(f"AI analysis complete: {sym}")

    def _max_drawdown(self, prices):
        peak, max_dd = prices[0], 0
        for p in prices:
            if p > peak: peak = p
            dd = (p - peak) / peak * 100
            if dd < max_dd: max_dd = dd
        return max_dd

    # ═══════════════════════════════════════════════
    # TAB 7 — SIMULATOR
    # ═══════════════════════════════════════════════
    def _build_sim_tab(self, tab):
        pane = tk.Frame(tab, bg=BG)
        pane.pack(fill="both", expand=True, padx=14, pady=10)

        left = tk.Frame(pane, bg=BG, width=370)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        tk.Label(left, text="PAPER TRADING", fg=ACCENT, bg=BG, font=FONT_TITLE).pack(anchor="w", pady=(0, 10))

        cash_row = tk.Frame(left, bg=BG)
        cash_row.pack(anchor="w")
        self.sim_cash_lbl = tk.Label(cash_row, text=f"Current Cash Balance:  ${self.simulator.cash:,.2f}",
                                      fg=POS, bg=BG, font=("Consolas", 13, "bold"), cursor="hand2")
        self.sim_cash_lbl.pack(side="left")
        self.sim_cash_lbl.bind("<Button-1>", lambda e: self._sim_edit_cash())
        self._btn(cash_row, "EDIT", self._sim_edit_cash, BORDER, ACCENT).pack(side="left", padx=(8, 0))
        self.sim_port_lbl = tk.Label(left, text="Total Value of Assets:  —", fg=FG, bg=BG, font=("Consolas", 11))
        self.sim_port_lbl.pack(anchor="w", pady=(2, 4))
        self.sim_pnl_lbl  = tk.Label(left, text="P&L:  —", fg=FG_DIM, bg=BG, font=("Consolas", 11))
        self.sim_pnl_lbl.pack(anchor="w", pady=(0, 8))

        divider(left)

        form = tk.Frame(left, bg=BG)
        form.pack(fill="x")
        for lbl_text, attr, default in [("Ticker:", "sim_ticker", "AAPL"), ("Shares:", "sim_qty_e", "1")]:
            row = tk.Frame(form, bg=BG, pady=4)
            row.pack(fill="x")
            tk.Label(row, text=lbl_text, fg=FG_DIM, bg=BG, font=("Consolas",10),
                     width=9, anchor="w").pack(side="left")
            # ← FIX: no padx/pady in Entry kwargs
            e = styled_entry(row, font=("Consolas",11), bg=CARD, fg=FG,
                              insertbackground=ACCENT, borderwidth=0, width=18)
            e.pack(side="left", ipady=5, ipadx=4)
            e.insert(0, default)
            setattr(self, attr, e)

        btn_row = tk.Frame(form, bg=BG, pady=8)
        btn_row.pack(fill="x")
        self._btn(btn_row, "BUY",    self._sim_buy,          POS,   BG).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "SELL",   self._sim_sell,         NEG,   BG).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "VALUE",  self._sim_update_value, PANEL, FG).pack(side="left")

        self._btn(left, "RESET ACCOUNT", self._sim_reset, PANEL, NEG).pack(anchor="w", pady=4)

        divider(left)
        tk.Label(left, text="OPEN POSITIONS", fg=FG_DIM, bg=BG, font=FONT_SMALL).pack(anchor="w", pady=(0, 4))
        self.sim_pos_frame = tk.Frame(left, bg=BG)
        self.sim_pos_frame.pack(fill="x")

        # Right
        right = tk.Frame(pane, bg=BG)
        right.pack(side="right", fill="both", expand=True)

        self.sim_fig = Figure(figsize=(8, 2.8), facecolor=BG)
        self.sim_ax  = self.sim_fig.add_subplot(111)
        self._style_ax(self.sim_ax)
        self.sim_fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.15)
        self.sim_canvas = FigureCanvasTkAgg(self.sim_fig, master=right)
        self.sim_canvas.get_tk_widget().pack(fill="x", pady=(0, 8))
        self._sim_value_history = [self.simulator.cash]
        self._sim_time_history  = [datetime.now()]

        lf = tk.Frame(right, bg=BG)
        lf.pack(fill="x")
        tk.Label(lf, text="TRADE LOG", fg=FG_DIM, bg=BG, font=FONT_SMALL).pack(side="left")
        self._btn(lf, "CLEAR", self._sim_clear_log, PANEL, FG).pack(side="right")

        self.sim_log = tk.Text(right, bg=CARD, fg=FG, font=("Consolas", 9),
                                borderwidth=0, state="disabled", wrap="word",
                                padx=10, pady=8)
        self.sim_log.pack(fill="both", expand=True)
        self.sim_log.tag_configure("BUY",  foreground=POS)
        self.sim_log.tag_configure("SELL", foreground=NEG)
        self.sim_log.tag_configure("ts",   foreground=FG_DIM)
        self.sim_log.tag_configure("fail", foreground=NEG)

        self._sim_refresh_values()

    def _sim_edit_cash(self):
        dlg = tk.Toplevel(self)
        dlg.title("Edit Cash Balance")
        dlg.geometry("320x140")
        dlg.configure(bg=PANEL)
        dlg.grab_set()
        tk.Label(dlg, text="CURRENT CASH BALANCE", fg=ACCENT, bg=PANEL, font=FONT_TITLE).pack(pady=(18, 10))
        e = styled_entry(dlg, font=("Consolas", 12), bg=CARD, fg=FG, insertbackground=ACCENT, width=16)
        e.pack(pady=6)
        e.insert(0, f"{self.simulator.cash:,.2f}")
        e.select_range(0, "end")
        e.focus_set()
        def ok():
            try:
                val = float(e.get().replace(",", ""))
                if val < 0:
                    raise ValueError("Cash cannot be negative.")
                self.simulator.cash = val
                dlg.destroy()
                self.sim_cash_lbl.config(text=f"Current Cash Balance:  ${self.simulator.cash:,.2f}")
                self._sim_refresh_values()
                self.status_var.set(f"Cash updated to ${self.simulator.cash:,.2f}")
            except (ValueError, TypeError):
                messagebox.showerror("Invalid", "Enter a valid positive number.", parent=dlg)
        self._btn(dlg, "UPDATE", ok, ACCENT, BG).pack(pady=12)
        dlg.bind("<Return>", lambda ev: ok())

    def _sim_refresh_values(self):
        """Update cash display and trigger full value refresh."""
        self.sim_cash_lbl.config(text=f"Current Cash Balance:  ${self.simulator.cash:,.2f}")
        self._sim_update_value()

    def _sim_trade(self, action):
        t = self.sim_ticker.get().strip().upper()
        try:
            q = float(self.sim_qty_e.get())
            if q <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter a valid positive quantity.")
            return
        self.status_var.set(f"Fetching price for {t}…")
        threading.Thread(target=self._do_sim_trade, args=(t, q, action), daemon=True).start()

    def _do_sim_trade(self, t, q, action):
        try:
            d = yf.Ticker(t).history(period="1d")
            if d.empty: raise ValueError("No price data.")
            p = float(d["Close"].iloc[-1])
            ok, msg = (self.simulator.buy if action=="buy" else self.simulator.sell)(t, p, q)
            self.after(0, lambda: self._sim_result(ok, msg, action))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Trade Error", str(e)))

    def _sim_buy(self):  self._sim_trade("buy")
    def _sim_sell(self): self._sim_trade("sell")

    def _sim_result(self, ok, msg, action):
        tag = action.upper() if ok else "fail"
        self.sim_log.config(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.sim_log.insert("1.0", "\n")
        self.sim_log.insert("1.0", msg + "\n", tag)
        self.sim_log.insert("1.0", f"[{ts}]  ", "ts")
        self.sim_log.config(state="disabled")
        self.sim_cash_lbl.config(text=f"Current Cash Balance:  ${self.simulator.cash:,.2f}")
        self._sim_update_positions()
        if not ok:
            messagebox.showwarning("Trade Failed", msg)
        self.status_var.set(msg)
        self._sim_update_value()

    def _sim_update_positions(self):
        for w in self.sim_pos_frame.winfo_children():
            w.destroy()
        if not self.simulator.positions:
            tk.Label(self.sim_pos_frame, text="No open positions.", fg=FG_DIM, bg=BG,
                     font=("Consolas", 9)).pack(anchor="w")
            return
        for sym, pos in self.simulator.positions.items():
            row = tk.Frame(self.sim_pos_frame, bg=PANEL, pady=4, padx=8)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=sym, fg=ACCENT, bg=PANEL, font=("Consolas",10,"bold"), width=10).pack(side="left")
            tk.Label(row, text=f"{pos['shares']:.4g} sh  avg ${pos['avg']:.2f}",
                     fg=FG, bg=PANEL, font=("Consolas",9)).pack(side="left")

    def _sim_update_value(self):
        threading.Thread(target=self._fetch_sim_value, daemon=True).start()

    def _fetch_sim_value(self):
        val = self.simulator.portfolio_value()
        pnl = val - self.simulator.start_cash
        sign = "+" if pnl >= 0 else ""
        pc   = POS if pnl >= 0 else NEG
        self.after(0, lambda: [
            self.sim_port_lbl.config(text=f"Total Value of Assets:  ${val:,.2f}",
                                      fg=POS if val >= self.simulator.start_cash else NEG),
            self.sim_pnl_lbl.config(text=f"P&L:  {sign}${abs(pnl):,.2f}  ({sign}{pnl/self.simulator.start_cash*100:.2f}%)",
                                     fg=pc)
        ])
        self._sim_value_history.append(val)
        self._sim_time_history.append(datetime.now())
        self.after(0, self._sim_update_chart)

    def _sim_update_chart(self):
        self.sim_ax.clear()
        self._style_ax(self.sim_ax)
        if len(self._sim_value_history) > 1:
            color = POS if self._sim_value_history[-1] >= self.simulator.start_cash else NEG
            self.sim_ax.plot(self._sim_time_history, self._sim_value_history, color=color, linewidth=2)
            self.sim_ax.axhline(self.simulator.start_cash, color=BORDER, linewidth=0.8, linestyle="--")
            self.sim_ax.fill_between(self._sim_time_history, self._sim_value_history,
                                      self.simulator.start_cash, color=color, alpha=0.1)
        self.sim_ax.set_title("Account Value", color=FG_DIM, fontsize=9)
        self.sim_canvas.draw()

    def _sim_reset(self):
        if messagebox.askyesno("Reset", "Reset paper trading account to $100,000?"):
            self.simulator = SimulatorState()
            self._sim_value_history = [self.simulator.cash]
            self._sim_time_history  = [datetime.now()]
            self.sim_cash_lbl.config(text=f"Current Cash Balance:  ${self.simulator.cash:,.2f}")
            self.sim_pnl_lbl.config(text="P&L:  $0.00")
            self.sim_port_lbl.config(text="Total Value of Assets:  —")
            self.sim_log.config(state="normal")
            self.sim_log.delete("1.0", "end")
            self.sim_log.config(state="disabled")
            self._sim_update_positions()
            self._sim_update_chart()

    def _sim_clear_log(self):
        self.sim_log.config(state="normal")
        self.sim_log.delete("1.0", "end")
        self.sim_log.config(state="disabled")

    # ═══════════════════════════════════════════════
    # TAB 8 — DIVIDENDS
    # ═══════════════════════════════════════════════
    def _build_dividends_tab(self, tab):
        ctrl = tk.Frame(tab, bg=BG, padx=14, pady=10)
        ctrl.pack(fill="x")
        tk.Label(ctrl, text="DIVIDEND TRACKER", fg=ACCENT, bg=BG, font=FONT_TITLE).pack(side="left")
        self._btn(ctrl, "↻ REFRESH", self._refresh_dividends, ACCENT, BG).pack(side="right")
        tk.Label(tab, text="Track projected dividend income from your portfolio holdings.",
                 fg=FG_DIM, bg=BG, font=("Consolas", 9), padx=14).pack(anchor="w", pady=(0, 6))

        self.div_summary = tk.Frame(tab, bg=BG, padx=14)
        self.div_summary.pack(fill="x", pady=(0, 8))

        cols = ("Ticker","Shares","Div/Share","Annual $","Yield%","Ex-Div Date","Frequency")
        self.div_tree = ttk.Treeview(tab, columns=cols, show="headings")
        for c, w in zip(cols, [90,80,110,120,90,120,100]):
            self.div_tree.heading(c, text=c)
            self.div_tree.column(c, width=w, anchor="center")
        self.div_tree.pack(fill="both", expand=True, padx=14, pady=(0, 6))

        self.div_fig = Figure(figsize=(14, 2.5), facecolor=BG)
        self.div_ax  = self.div_fig.add_subplot(111)
        self.div_canvas = FigureCanvasTkAgg(self.div_fig, master=tab)
        self.div_canvas.get_tk_widget().pack(fill="x", padx=14, pady=(0, 6))
        self._refresh_dividends()

    def _refresh_dividends(self):
        self.status_var.set("Fetching dividend data…")
        threading.Thread(target=self._fetch_dividends, daemon=True).start()

    def _fetch_dividends(self):
        rows, total, monthly = [], 0.0, {}
        for ticker, h in self.portfolio.holdings.items():
            try:
                info = yf.Ticker(ticker).info
                rate  = info.get("dividendRate") or 0
                yld   = info.get("dividendYield") or 0
                ex_dt = info.get("exDividendDate","")
                if ex_dt and isinstance(ex_dt, (int,float)):
                    ex_dt = datetime.fromtimestamp(ex_dt).strftime("%Y-%m-%d")
                annual = rate * h.shares
                total += annual
                freq = "Quarterly" if rate > 0 else "N/A"
                if annual > 0:
                    for mo in [0,3,6,9]:
                        m = (datetime.now().month + mo - 1) % 12 + 1
                        monthly[m] = monthly.get(m, 0) + annual/4
                rows.append((ticker, f"{h.shares:.4g}",
                             f"${rate:.4f}" if rate else "N/A",
                             f"${annual:.2f}" if annual>0 else "N/A",
                             f"{yld*100:.2f}%" if yld else "N/A",
                             str(ex_dt)[:10] if ex_dt else "N/A", freq))
            except:
                pass
        self.after(0, lambda: self._populate_dividends(rows, total, monthly))

    def _populate_dividends(self, rows, total, monthly):
        for i in self.div_tree.get_children():
            self.div_tree.delete(i)
        for r in rows:
            self.div_tree.insert("", "end", values=r)
        for w in self.div_summary.winfo_children():
            w.destroy()
        for lbl, val, col in [("Annual Income", f"${total:,.2f}", POS),
                               ("Monthly Income", f"${total/12:,.2f}", POS),
                               ("Weekly Income",  f"${total/52:,.2f}", FG)]:
            stat_card(self.div_summary, lbl, val, col, 13).pack(side="left", padx=(0, 6))
        self.div_ax.clear()
        self.div_ax.set_facecolor(BG)
        if monthly:
            mnames = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            ms = sorted(monthly.keys())
            self.div_ax.bar([mnames[m-1] for m in ms], [monthly[m] for m in ms],
                             color=POS, alpha=0.85, edgecolor=BG)
            self.div_ax.set_title("Projected Monthly Dividend Income", color=FG_DIM, fontsize=9)
            self.div_ax.tick_params(colors=FG_DIM, labelsize=8)
            for sp in self.div_ax.spines.values(): sp.set_color(BORDER)
            self.div_ax.grid(True, color=BORDER, linewidth=0.4, alpha=0.5)
            self.div_ax.set_ylabel("$", color=FG_DIM, fontsize=8)
        self.div_fig.patch.set_facecolor(BG)
        self.div_fig.subplots_adjust(left=0.05, right=0.98, top=0.9, bottom=0.2)
        self.div_canvas.draw()
        self.status_var.set("Dividend data loaded.")

    # ═══════════════════════════════════════════════
    # TAB 9 — SCREENER
    # ═══════════════════════════════════════════════
    def _build_screener_tab(self, tab):
        ctrl = tk.Frame(tab, bg=BG, padx=14, pady=10)
        ctrl.pack(fill="x")
        tk.Label(ctrl, text="STOCK SCREENER", fg=ACCENT, bg=BG, font=FONT_TITLE).pack(side="left")
        self._btn(ctrl, "▶ RUN SCREENER", self._run_screener, ACCENT, BG).pack(side="right")

        ff = tk.Frame(tab, bg=PANEL, padx=18, pady=12)
        ff.pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(ff, text="FILTERS", fg=FG_DIM, bg=PANEL, font=FONT_SMALL).grid(
            row=0, column=0, sticky="w", columnspan=12, pady=(0, 8))

        self._screen_filters = {}
        fdefs = [("Min P/E","pe_min","0"), ("Max P/E","pe_max","50"),
                 ("Min Div%","div_min","0"), ("Max Beta","beta_max","2"),
                 ("Min Mkt Cap","cap_min","1B")]
        for i, (lbl, key, default) in enumerate(fdefs):
            tk.Label(ff, text=lbl+":", fg=FG_DIM, bg=PANEL,
                     font=("Consolas",9)).grid(row=1, column=i*2, padx=(8,2), sticky="w")
            e = styled_entry(ff, font=("Consolas",9), bg=CARD, fg=FG,
                              insertbackground=ACCENT, borderwidth=0, width=8)
            e.insert(0, default)
            e.grid(row=1, column=i*2+1, padx=(0,10))
            self._screen_filters[key] = e

        tk.Label(ff, text="Universe:", fg=FG_DIM, bg=PANEL, font=("Consolas",9)).grid(row=1, column=10, padx=(8,2))
        self._screen_universe = tk.StringVar(value="S&P 100")
        ttk.Combobox(ff, textvariable=self._screen_universe,
                     values=["S&P 100","My Portfolio","Watchlist","Tech Giants","Crypto"],
                     font=("Consolas",9), width=14, state="readonly").grid(row=1, column=11, padx=4)

        cols = ("Ticker","Name","Price","P/E","EPS","Div%","Beta","Mkt Cap","Sector")
        self.screen_tree = ttk.Treeview(tab, columns=cols, show="headings")
        for c, w in zip(cols, [90,180,100,80,90,80,70,120,140]):
            self.screen_tree.heading(c, text=c,
                                      command=lambda col=c: self._sort_screener(col))
            self.screen_tree.column(c, width=w, anchor="center")
        self.screen_tree.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        self.screen_tree.bind("<Double-1>", lambda e: self._screener_dbl())
        tk.Label(tab, text="Double-click any result to load it in the Analysis tab.",
                 fg=FG_DIM, bg=BG, font=("Consolas",8), padx=14).pack(anchor="w", pady=(0, 4))

    SP100 = ["AAPL","MSFT","AMZN","NVDA","GOOGL","META","TSLA","UNH","XOM",
             "JPM","JNJ","V","PG","HD","MA","CVX","ABBV","MRK","PEP","AVGO",
             "KO","COST","WMT","MCD","CSCO","ABT","DHR","TMO","ACN","NEE",
             "DIS","NFLX","ADBE","CRM","ORCL","INTC","AMD","IBM","TXN","QCOM"]

    def _run_screener(self):
        self.status_var.set("Running screener…")
        threading.Thread(target=self._fetch_screener, daemon=True).start()

    def _fetch_screener(self):
        uv = self._screen_universe.get()
        if uv == "S&P 100": syms = self.SP100
        elif uv == "My Portfolio": syms = list(self.portfolio.holdings.keys())
        elif uv == "Watchlist": syms = self.watchlist.symbols[:]
        elif uv == "Tech Giants": syms = ["AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","NFLX","ADBE"]
        else: syms = ["BTC-USD","ETH-USD","SOL-USD","DOGE-USD","XRP-USD","ADA-USD"]
        if not syms:
            self.after(0, lambda: self.status_var.set("No symbols in selected universe."))
            return
        try:
            pe_min = float(self._screen_filters["pe_min"].get() or 0)
            pe_max = float(self._screen_filters["pe_max"].get() or 999)
            div_min = float(self._screen_filters["div_min"].get() or 0)
            beta_max = float(self._screen_filters["beta_max"].get() or 10)
            cap_min_s = (self._screen_filters["cap_min"].get() or "0").upper()
            cap_mult = 1e9 if "B" in cap_min_s else (1e6 if "M" in cap_min_s else 1)
            cap_min = float(re.sub(r"[^\d.]","", cap_min_s) or "0") * cap_mult
        except ValueError:
            self.after(0, lambda: self.status_var.set("Invalid filter values."))
            return
        is_crypto = uv == "Crypto"
        rows = []
        for sym in syms:
            try:
                t = yf.Ticker(sym)
                info = t.info
                d = t.history(period="5d")
                if d.empty:
                    continue
                price = float(d["Close"].iloc[-1])
                pe = info.get("trailingPE")
                if not is_crypto and pe is not None and (pe < pe_min or pe > pe_max):
                    continue
                eps = info.get("epsTrailingTwelveMonths") or 0
                div_y = (info.get("dividendYield") or 0) * 100
                if not is_crypto and div_y < div_min:
                    continue
                beta = info.get("beta") or 0
                if beta > beta_max:
                    continue
                mcap = info.get("marketCap") or 0
                if mcap < cap_min:
                    continue
                name = info.get("shortName") or info.get("longName") or sym
                mcap_fmt = fmt_big(mcap)
                rows.append((sym, name[:25], f"${price:.2f}", f"{pe:.1f}" if pe else "N/A",
                             f"${eps:.2f}" if eps else "N/A", f"{div_y:.2f}%",
                             f"{beta:.2f}" if beta else "N/A", mcap_fmt,
                             info.get("sector","N/A")[:20]))
            except:
                pass
        self._screener_data = rows
        self.after(0, lambda: self._populate_screener(rows))

    def _populate_screener(self, rows):
        for i in self.screen_tree.get_children():
            self.screen_tree.delete(i)
        for r in rows:
            self.screen_tree.insert("", "end", values=r)
        self.status_var.set(f"Screener: {len(rows)} results.")

    def _sort_screener(self, col):
        if not hasattr(self, "_screener_data") or not self._screener_data:
            return
        cols = ("Ticker","Name","Price","P/E","EPS","Div%","Beta","Mkt Cap","Sector")
        idx = cols.index(col) if col in cols else 0
        numeric_cols = ("Price","P/E","EPS","Div%","Beta")
        def _key(r):
            v = r[idx]
            if v == "N/A":
                return (0, 0) if col in numeric_cols else ""
            if col in numeric_cols:
                try:
                    return (1, float(re.sub(r"[^\d.-]", "", str(v).replace("%", "")) or 0))
                except (ValueError, TypeError):
                    return (0, 0)
            return (1, str(v))
        reverse = col in ("Price","P/E","EPS","Div%","Mkt Cap","Beta")
        self._screener_data.sort(key=_key, reverse=reverse)
        self._populate_screener(self._screener_data)

    def _screener_dbl(self):
        sel = self.screen_tree.selection()
        if sel:
            self._load_symbol(self.screen_tree.item(sel[0])["values"][0])

def main():
    import sys
    try:
        app = InvestaurPro()
        
        app.update()  # Process pending events so window is fully drawn
        app.mainloop()
    except Exception as e:
        if "display" in str(e).lower() or "DISPLAY" in str(e):
            print("Display error: Cannot open GUI.", file=sys.stderr)
            print("  - On Linux/WSL: ensure DISPLAY is set (e.g. export DISPLAY=:0)", file=sys.stderr)
            print("  - On WSL2: use WSLg or install an X server.", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()