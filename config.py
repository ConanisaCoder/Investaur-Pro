"""
INVESTAUR PRO — Theme and configuration constants
"""

# Theme colors
BG      = "#070710"  # Background color of the application
PANEL   = "#0f0f1c"  # Color of the main application panel
CARD    = "#13131f"  # Color of the application cards
BORDER  = "#1e1e30"  # Color of the application borders
ACCENT  = "#f0c040"  # Accent color used throughout the application
ACCENT2 = "#c084fc"  # Second accent color used throughout the application
FG      = "#e8e8f0"  # Foreground color used for text
FG_DIM  = "#888899"  # Foreground color used for dimmed text
POS     = "#22d67e"  # Positive color used for green text
NEG     = "#ff4d6d"  # Negative color used for red text
BLUE    = "#38bdf8"  # Blue color used throughout the application
ORANGE  = "#fb923c"  # Orange color used throughout the application

# Fonts
FONT_TITLE = ("Courier",  14, "bold")  # Font used for titles
FONT_MONO  = ("Consolas", 10)  # Font used for monospaced text
FONT_SMALL = ("Consolas",  8, "bold")  # Font used for small text
FONT_NUM   = ("Consolas", 13, "bold")  # Font used for numbers

# Real-time update intervals (milliseconds)
REFRESH_PULSE_MS       = 60_000   # Interval for updating the market pulse sidebar
REFRESH_PORTFOLIO_MS   = 60_000   # Interval for updating the portfolio P&L sidebar
REFRESH_ANALYSIS_MS    = 30_000   # Interval for updating the current symbol price in the analysis tab
REFRESH_MARKETS_MS     = 300_000  # Interval for updating the markets tab when visible