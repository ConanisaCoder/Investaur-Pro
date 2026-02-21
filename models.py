"""
INVESTAUR PRO — Data models and company info
"""

from dataclasses import dataclass, field
from datetime import datetime

import yfinance as yf

# Company descriptions (offline fallback)
COMPANY_INFO = {
    "AAPL": {"mission": "To bring the best user experience to its customers through innovative hardware, software, and services.",
              "summary": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. Its flagship products include the iPhone, Mac, iPad, Apple Watch, and services like the App Store, Apple Music, and iCloud.",
              "founded": "1976", "employees": "161,000", "hq": "Cupertino, CA"},
    "NVDA": {"mission": "To advance human progress through AI and accelerated computing.",
              "summary": "NVIDIA Corporation designs and manufactures GPUs, SoCs, and AI computing hardware. It dominates the AI training chip market with its H100/A100 data-center GPUs and serves gaming, automotive, and professional visualization markets.",
              "founded": "1993", "employees": "29,600", "hq": "Santa Clara, CA"},
    "MSFT": {"mission": "To empower every person and every organization on the planet to achieve more.",
              "summary": "Microsoft Corporation develops and licenses software, hardware, and cloud services. Segments include Productivity (Office, LinkedIn), Intelligent Cloud (Azure), and More Personal Computing (Windows, Xbox, Surface).",
              "founded": "1975", "employees": "221,000", "hq": "Redmond, WA"},
    "GOOGL": {"mission": "To organize the world's information and make it universally accessible and useful.",
               "summary": "Alphabet Inc. is the parent of Google, operating the world's most-used search engine, YouTube, Android, Chrome, and Google Cloud. Moonshot bets include Waymo and DeepMind.",
               "founded": "1998", "employees": "182,000", "hq": "Mountain View, CA"},
    "AMZN": {"mission": "To be Earth's most customer-centric company.",
              "summary": "Amazon.com operates the world's largest e-commerce platform, the dominant cloud provider (AWS), Prime Video, Alexa, Whole Foods, and a massive advertising business.",
              "founded": "1994", "employees": "1,541,000", "hq": "Seattle, WA"},
    "TSLA": {"mission": "To accelerate the world's transition to sustainable energy.",
              "summary": "Tesla designs, develops, and sells electric vehicles, energy generation and storage systems. Products: Model S/3/X/Y/Cybertruck, Megapack batteries, solar panels, and the Supercharger network.",
              "founded": "2003", "employees": "140,000", "hq": "Austin, TX"},
    "META": {"mission": "To give people the power to build community and bring the world closer together.",
              "summary": "Meta Platforms develops social media technologies including Facebook, Instagram, WhatsApp, and Messenger — connecting over 3 billion people. Investing heavily in the metaverse via Reality Labs.",
              "founded": "2004", "employees": "67,300", "hq": "Menlo Park, CA"},
    "BTC-USD": {"mission": "A peer-to-peer electronic cash system without a trusted third party.",
                 "summary": "Bitcoin is the world's first and largest cryptocurrency by market cap. It operates on a decentralized blockchain with a hard cap of 21 million coins. Used as a store of value and inflation hedge.",
                 "founded": "2009", "employees": "Decentralized", "hq": "Decentralized"},
    "ETH-USD": {"mission": "A decentralized platform for smart contracts and applications.",
                 "summary": "Ethereum is the second-largest cryptocurrency and the leading smart-contract platform, enabling DeFi, NFTs, DAOs, and Web3 apps. The 2022 Merge moved it to proof-of-stake.",
                 "founded": "2015", "employees": "Decentralized", "hq": "Decentralized"},
    "SPY":  {"mission": "Track the S&P 500 Index.", "summary": "SPDR S&P 500 ETF Trust tracks the S&P 500 Index of 500 large-cap U.S. equities. The largest and most liquid ETF in the world. Managed by State Street Global Advisors.", "founded": "1993", "employees": "N/A", "hq": "Boston, MA"},
    "QQQ":  {"mission": "Track the Nasdaq-100 Index.", "summary": "Invesco QQQ ETF tracks the Nasdaq-100, which includes 100 of the largest non-financial Nasdaq companies, heavily weighted toward technology.", "founded": "1999", "employees": "N/A", "hq": "Atlanta, GA"},
}


def get_company_info(ticker):
    return COMPANY_INFO.get(ticker.upper(), {
        "mission": "Mission statement not available in offline database.",
        "summary": f"Detailed company summary for {ticker} is fetched live from Yahoo Finance. See financial metrics in the Analysis tab.",
        "founded": "N/A", "employees": "N/A", "hq": "N/A"
    })


@dataclass
class Holding:
    ticker: str
    shares: float
    avg_price: float
    purchase_date: str = ""


@dataclass
class PortfolioState:
    holdings: dict = field(default_factory=dict)

    def add(self, t, s, a, date=""):
        self.holdings[t.upper()] = Holding(t.upper(), s, a, date or datetime.now().strftime("%Y-%m-%d"))

    def remove(self, t):
        self.holdings.pop(t.upper(), None)

    def snapshot(self):
        rows, total_v, total_c = [], 0.0, 0.0
        for h in self.holdings.values():
            try:
                d = yf.Ticker(h.ticker).history(period="2d")
                p = float(d["Close"].iloc[-1]) if not d.empty else h.avg_price
            except Exception:
                p = h.avg_price
            v = p * h.shares
            c = h.avg_price * h.shares
            pl = v - c
            pct = (pl / c * 100) if c else 0.0
            total_v += v
            total_c += c
            rows.append((h.ticker, h.shares, h.avg_price, p, v, pl, pct))
        return rows, total_v, (total_v - total_c)

    def historical_values(self, period="1y"):
        if not self.holdings:
            return None, None
        all_dates = None
        total = None
        for h in self.holdings.values():
            try:
                d = yf.Ticker(h.ticker).history(period=period)
                if d.empty:
                    continue
                vals = d["Close"] * h.shares
                if all_dates is None:
                    all_dates = d.index
                    total = vals.values.astype(float)
                else:
                    common = all_dates.intersection(d.index)
                    if len(common) == 0:
                        continue
                    all_dates = common
                    prev = total[:len(common)]
                    total = prev + vals.reindex(common).values.astype(float)
            except Exception:
                pass
        return all_dates, total


@dataclass
class WatchlistState:
    symbols: list = field(default_factory=list)

    def add(self, sym):
        sym = sym.upper()
        if sym not in self.symbols:
            self.symbols.append(sym)

    def remove(self, sym):
        self.symbols = [s for s in self.symbols if s != sym.upper()]


@dataclass
class SimulatorState:
    cash: float = 100_000.0
    positions: dict = field(default_factory=dict)
    history: list = field(default_factory=list)
    start_cash: float = 100_000.0

    def buy(self, t, p, s):
        cost = p * s
        if cost > self.cash:
            return False, f"Insufficient funds. Need ${cost:,.2f}, have ${self.cash:,.2f}."
        self.cash -= cost
        if t not in self.positions:
            self.positions[t] = {"shares": 0.0, "avg": p}
        self.positions[t]["shares"] += s
        self.history.append({"action": "BUY", "ticker": t, "shares": s, "price": p,
                              "total": cost, "time": datetime.now().strftime("%H:%M:%S")})
        return True, f"Purchased {s:.4g} {t} @ ${p:.2f}  (Cost: ${cost:,.2f})"

    def sell(self, t, p, s):
        pos = self.positions.get(t)
        if not pos or s > pos["shares"]:
            held = pos["shares"] if pos else 0
            return False, f"Not enough shares. Holding {held:.4g}, trying to sell {s:.4g}."
        self.cash += p * s
        pos["shares"] -= s
        if pos["shares"] <= 0:
            del self.positions[t]
        self.history.append({"action": "SELL", "ticker": t, "shares": s, "price": p,
                              "total": p*s, "time": datetime.now().strftime("%H:%M:%S")})
        return True, f"Sold {s:.4g} {t} @ ${p:.2f}  (Proceeds: ${p*s:,.2f})"

    def portfolio_value(self):
        total = self.cash
        for t, pos in self.positions.items():
            try:
                d = yf.Ticker(t).history(period="1d")
                price = float(d["Close"].iloc[-1]) if not d.empty else pos["avg"]
                total += price * pos["shares"]
            except Exception:
                pass
        return total
