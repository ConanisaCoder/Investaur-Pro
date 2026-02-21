"""
INVESTAUR PRO — UI helper utilities
"""

import tkinter as tk
from tkinter import ttk

from config import BG, CARD, BORDER, FONT_SMALL, FG, FG_DIM


def styled_entry(parent, **kwargs):
    """Create a tk.Entry without the unsupported padx/pady options."""
    bad = {"padx", "pady"}
    safe = {k: v for k, v in kwargs.items() if k not in bad}
    return tk.Entry(parent, **safe)


def stat_card(parent, label, value, color=FG, font_size=11):
    f = tk.Frame(parent, bg=CARD, relief="flat")
    inner = tk.Frame(f, bg=CARD, padx=14, pady=10)
    inner.pack(fill="both", expand=True)
    tk.Label(inner, text=label.upper(), fg=FG_DIM, bg=CARD, font=FONT_SMALL).pack(anchor="w")
    tk.Label(inner, text=value, fg=color, bg=CARD,
             font=("Consolas", font_size, "bold")).pack(anchor="w", pady=(3, 0))
    return f


def divider(parent, color=BORDER):
    tk.Frame(parent, bg=color, height=1).pack(fill="x", pady=8)


def scrollable(parent, bg=BG):
    outer = tk.Frame(parent, bg=bg)
    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0)
    sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=bg)
    win = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _resize(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(win, width=canvas.winfo_width())

    inner.bind("<Configure>", _resize)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

    def _wheel(e):
        canvas.yview_scroll(-1 * (e.delta // 120 or (1 if e.num == 4 else -1)), "units")

    canvas.bind_all("<MouseWheel>", _wheel)
    canvas.bind_all("<Button-4>", _wheel)
    canvas.bind_all("<Button-5>", _wheel)
    return outer, inner, canvas


def fmt_big(v):
    try:
        v = float(v)
        if v >= 1e12:
            return f"${v/1e12:.2f}T"
        if v >= 1e9:
            return f"${v/1e9:.2f}B"
        if v >= 1e6:
            return f"${v/1e6:.2f}M"
        return f"${v:,.0f}"
    except (TypeError, ValueError):
        return str(v) if v else "N/A"
