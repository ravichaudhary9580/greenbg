"""
constants.py
All shared colors, palettes, and size definitions.
Edit this file to change colors, add passport sizes, or tweak paper sizes.
"""
import datetime

# ── Passport photo sizes (pixels @ 300 DPI) ──────────────────────────────────
PASSPORT_SIZES = {
    "A4 (31×39mm)": (370, 459),
    "Small (29×33mm)":   (343, 399),
}

# ── Paper sizes (pixels @ 300 DPI) ───────────────────────────────────────────
PAPER_SIZES = {
    "A4 (8.27 x 11.69 in)": (2480, 3508),
    "Card (4 x 6 in)":      (1200, 1800),
}
SHEET_MARGIN = 55
SHEET_GAP = 30

# ── Background color options ──────────────────────────────────────────────────
BG_COLORS = {
    "White":        "#ffffff",
    "Light Gray":   "#d0d0d0",
    "Light Blue":   "#a8c8e8",
    "Mint Green":   "#d4edda",
    "Soft Pink":    "#f9dde0",
    "Cream":        "#fdf6e3",
    "Peach":        "#fde8d8",
    "Off-White":    "#f5f5f0",
    "Lavender":     "#e6e0f8",
    "Transparent":  None,
}

# ── Text color options ────────────────────────────────────────────────────────
TEXT_COLORS = {
    "Black":     "#000000",
    "White":     "#ffffff",
    "Dark Gray": "#333333",
    "Navy":      "#1a2a4a",
}

# ── Text background color options ─────────────────────────────────────────────
TEXT_BG_COLORS = {
    "None":       None,
    "White":      "#ffffff",
    "Black":      "#000000",
    "Yellow":     "#ffee00",
    "Light Gray": "#e0e0e0",
}

# ── UI color palette ──────────────────────────────────────────────────────────
C_BG     = "#eae8e1"
C_WHITE  = "#ffffff"
C_CARD   = "#ffffff"
C_DARK   = "#1a1a1a"
C_MUTED  = "#9a9890"
C_ACCENT = "#2a7a5a"
C_BORDER = "#d0cdc5"
C_TEXT   = "#1a1a1a"
C_ERR    = "#cc3333"


def today_str():
    return datetime.date.today().strftime("%m/%d/%Y")
