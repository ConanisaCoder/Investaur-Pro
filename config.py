"""
INVESTAUR PRO — Theme and configuration constants
"""

# Theme colors
BG      = "#070710"
PANEL   = "#0f0f1c"
CARD    = "#13131f"
BORDER  = "#1e1e30"
ACCENT  = "#f0c040"
ACCENT2 = "#c084fc"
FG      = "#e8e8f0"
FG_DIM  = "#888899"
POS     = "#22d67e"
NEG     = "#ff4d6d"
BLUE    = "#38bdf8"
ORANGE  = "#fb923c"

# Fonts
FONT_TITLE = ("Courier",  14, "bold")
FONT_MONO  = ("Consolas", 10)
FONT_SMALL = ("Consolas",  8, "bold")
FONT_NUM   = ("Consolas", 13, "bold")

# Real-time update intervals (milliseconds)
REFRESH_PULSE_MS       = 60_000   # Market pulse sidebar
REFRESH_PORTFOLIO_MS   = 60_000   # Portfolio P&L sidebar
REFRESH_ANALYSIS_MS    = 30_000   # Current symbol price in Analysis tab
REFRESH_MARKETS_MS     = 300_000  # Markets tab when visible
