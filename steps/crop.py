"""
steps/crop.py  –  Step 2: Crop & Edit
=======================================
Layout matches the wireframe exactly:
  ┌─────────────────────────────────────────────────────────────────┐
  │  [steps header]                                                 │
  ├──────────────────────────────┬──────────────────────────────────┤
  │  status badge                │  ✨ AI Enhance button            │
  ├──────────────────────────────┴──────────────────────────────────┤
  │                              │  TOOLS PANEL                     │
  │       preview canvas         │  • Mode: Crop / Erase            │
  │  (drag-pan, wheel-zoom)      │  • Aspect ratio presets          │
  │                              │  • Brush size (erase)            │
  │                              │  • Brightness / Sharpness        │
  │                              │  • Contrast / Saturation         │
  │                              │  • Zoom  +  –  1:1               │
  ├──────────────────────────────┴──────────────────────────────────┤
  │  [Confirm Crop →]   [↺ Re-upload]                               │
  └─────────────────────────────────────────────────────────────────┘

Libraries used
──────────────
• Pillow  (ImageStat, ImageEnhance, ImageFilter) – image analysis + adjustments
• numpy   – fast alpha-channel erase via boolean mask
• rembg   – background removal (existing)
• tkinter – UI (existing)
"""

import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageStat
from io import BytesIO
import threading
import typing
import math

if typing.TYPE_CHECKING:
    import numpy as np          # only for Pylance – never executed at runtime
try:
    import numpy as np          # type: ignore[assignment]
    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    _HAS_NUMPY = False

from constants import C_BG, C_WHITE, C_CARD, C_DARK, C_MUTED, C_ACCENT, C_BORDER

# ── palette additions ──────────────────────────────────────────────────────────
C_ERASE   = "#e05555"   # active erase colour
C_CROP_C  = "#4fc3f7"   # crop-box colour
C_HILIGHT = "#ffe082"   # corner handle colour
C_PANEL   = "#2c2f33"   # tools panel bg  (slightly lighter, easier to read)
C_SEP     = "#3d4147"   # separator
C_PANEL_LBL  = "#a8b0bb"  # section label text
C_PANEL_VAL  = "#7ecfff"  # value/accent text on panel
C_BTN_IDLE   = "#3a3f45"  # inactive button bg
C_BTN_TEXT   = "#d0d6de"  # inactive button text

# Aspect-ratio presets (label → (w, h) or None for free)
RATIO_PRESETS = [
    ("Free",   None),
    ("2×2 in", (2, 2)),
    ("35×45",  (35, 45)),
    ("4×6",    (4, 6)),
    ("3×4",    (3, 4)),
    ("1:1",    (1, 1)),
]


class CropStep:
    """Mixin – mixed into PassportApp."""

    if typing.TYPE_CHECKING:
        STEP_UPLOAD: int
        STEP_CROP: int
        STEP_CUSTOMIZE: int
        step: int
        content: tk.Frame
        orig_image: typing.Any
        removed_image: typing.Any
        removal_done: bool
        cropped_image: typing.Any
        bg_ready: threading.Event
        session: typing.Any
        root: tk.Tk
        drag_data: dict
        cx1: int; cy1: int; cx2: int; cy2: int
        _cs: float
        _co: typing.Tuple[int, int]
        crop_canvas: tk.Canvas
        def _set_footer(self, btns: list) -> None: ...
        def _show_step(self, step: int) -> None: ...
        def _card(self, pady: tuple = (0, 12)) -> tk.Frame: ...
        def _set_status(self, msg: str) -> None: ...
        def _apply_customize(self) -> None: ...
        # slider DoubleVars – set dynamically via slider_row()
        _bright_var:   tk.DoubleVar
        _sharp_var:    tk.DoubleVar
        _contrast_var: tk.DoubleVar
        _sat_var:      tk.DoubleVar

    # ══════════════════════════════════════════════════════════════════════════
    #  BUILD UI
    # ══════════════════════════════════════════════════════════════════════════
    def _build_crop(self):
        # ── state ────────────────────────────────────────────────────────────
        self._zoom_level     = 1.0
        self._pan_offset     = [0, 0]          # canvas-pixel pan (x, y)
        self._pan_drag       = {}              # pan drag state

        self._tool_mode      = "crop"          # "crop" | "erase"
        self._erase_radius   = 18
        self._aspect_ratio   = None            # None = free, else (w, h)

        self._brightness_val = 1.0
        self._sharpness_val  = 1.0
        self._contrast_val   = 1.0
        self._saturation_val = 1.0

        self._enhanced_image = None            # result of AI enhance
        self._undo_stack     = []              # list of PIL images (erase undo)
        self._erase_cursor   = None            # canvas oval id

        # crop-box canvas coords (initialised on first render)
        self.cx1 = self.cy1 = self.cx2 = self.cy2 = 0
        self.drag_data = {}

        # ── footer ────────────────────────────────────────────────────────────
        self._set_footer([
            ("confirm crop →", self._confirm_crop, "dark"),
            ("↺  re-upload", lambda: self._show_step(self.STEP_UPLOAD), "outline"),
        ])

        # ── outer frame ───────────────────────────────────────────────────────
        outer = tk.Frame(self.content, bg=C_BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # ── top bar ───────────────────────────────────────────────────────────
        top_border = tk.Frame(outer, bg=C_BORDER)
        top_border.pack(fill=tk.X)
        top_bar = tk.Frame(top_border, bg=C_CARD)
        top_bar.pack(fill=tk.X, padx=1, pady=1)

        self.removal_badge_var = tk.StringVar(
            value="⏳ Removing background…" if not self.removal_done
            else "✓ Background removed")
        badge_col = C_ACCENT if self.removal_done else "#cc8800"
        self.removal_badge = tk.Label(
            top_bar, textvariable=self.removal_badge_var,
            bg=C_CARD, fg=badge_col, font=("Courier New", 8, "bold"))
        self.removal_badge.pack(side=tk.LEFT, padx=16, pady=8)

        self._ai_btn = tk.Button(
            top_bar,
            text="✨  AI Enhance  (smart auto-levels)",
            command=self._ai_enhance,
            bg=C_DARK, fg=C_WHITE,
            font=("Courier New", 9, "bold"),
            relief="flat", bd=0, padx=16, pady=6,
            cursor="hand2", activebackground="#333")
        self._ai_btn.pack(side=tk.RIGHT, padx=16, pady=6)

        # ── main card ─────────────────────────────────────────────────────────
        card_border = tk.Frame(outer, bg=C_BORDER)
        card_border.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        card = tk.Frame(card_border, bg=C_CARD)
        card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        body = tk.Frame(card, bg=C_CARD)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=0)   # divider
        body.columnconfigure(2, weight=0)   # tools – fixed width
        body.rowconfigure(0, weight=1)

        # ── LEFT: canvas ──────────────────────────────────────────────────────
        left = tk.Frame(body, bg=C_CARD)
        left.grid(row=0, column=0, sticky="nsew")

        self._hint_var = tk.StringVar(
            value="CROP: drag to draw · corners to resize · body to move  |  "
                  "scroll = zoom  |  middle-drag = pan")
        tk.Label(left, textvariable=self._hint_var,
                 bg=C_CARD, fg=C_MUTED, font=("Courier New", 7, "bold")
                 ).pack(anchor="w", padx=12, pady=(8, 4))

        self.crop_canvas = tk.Canvas(left, bg="#6a6a6a", highlightthickness=0)
        self.crop_canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=(0, 8))
        self.crop_canvas.bind("<Configure>", lambda e: self._render_crop_canvas())
        self._bind_all_canvas_events()

        # ── divider ───────────────────────────────────────────────────────────
        tk.Frame(body, bg=C_BORDER, width=1).grid(row=0, column=1, sticky="ns")

        # ── RIGHT: tools panel – fixed width, no scroll, fits in window ──────
        right = tk.Frame(body, bg=C_PANEL, width=240)
        right.grid(row=0, column=2, sticky="nsew")
        right.pack_propagate(False)
        right.grid_propagate(False)

        self._build_tools_panel(right)

    # ══════════════════════════════════════════════════════════════════════════
    #  TOOLS PANEL  – compact, no scrolling
    # ══════════════════════════════════════════════════════════════════════════
    def _build_tools_panel(self, parent):
        PX     = 10
        FONT   = ("Courier New", 7, "bold")
        FONT_N = ("Courier New", 7)

        def sep():
            tk.Frame(parent, bg=C_SEP, height=1).pack(
                fill=tk.X, padx=PX, pady=4)

        def lbl(text):
            tk.Label(parent, text=text, bg=C_PANEL, fg=C_PANEL_LBL,
                     font=FONT).pack(anchor="w", padx=PX, pady=(6, 2))

        # ── SELECT TOOL ───────────────────────────────────────────────────────
        lbl("SELECT TOOL")
        mode_row = tk.Frame(parent, bg=C_PANEL)
        mode_row.pack(fill=tk.X, padx=PX, pady=(0, 4))

        self._crop_btn = tk.Button(
            mode_row, text="✂  Crop",
            command=lambda: self._set_mode("crop"),
            bg=C_ACCENT, fg=C_WHITE, font=("Courier New", 8, "bold"),
            relief="flat", bd=0, padx=6, pady=5,
            cursor="hand2", activebackground="#3a9a6a")
        self._crop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        self._erase_btn = tk.Button(
            mode_row, text="⊘  Erase",
            command=lambda: self._set_mode("erase"),
            bg=C_BTN_IDLE, fg=C_BTN_TEXT, font=("Courier New", 8),
            relief="flat", bd=0, padx=6, pady=5,
            cursor="hand2", activebackground="#555")
        self._erase_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        sep()

        # ── AI ANALYSIS ───────────────────────────────────────────────────────
        lbl("AI ANALYSIS")

        # Status badge row
        badge_row = tk.Frame(parent, bg=C_PANEL)
        badge_row.pack(fill=tk.X, padx=PX, pady=(0, 4))

        self._ai_dot = tk.Canvas(badge_row, width=10, height=10,
                                 bg=C_PANEL, highlightthickness=0)
        self._ai_dot.pack(side=tk.LEFT, padx=(0, 5), pady=2)
        self._ai_dot.create_oval(1, 1, 9, 9, fill="#555", outline="", tags="dot")

        self._ai_badge_var = tk.StringVar(value="not yet run")
        tk.Label(badge_row, textvariable=self._ai_badge_var,
                 bg=C_PANEL, fg=C_PANEL_LBL,
                 font=("Courier New", 7, "italic")).pack(side=tk.LEFT)

        # Report box — shown after enhance runs (frame never packed until needed)
        self._ai_report_frame = tk.Frame(parent, bg=C_PANEL)

        self._ai_status_var = tk.StringVar(value="")
        self._ai_report_lbl = tk.Label(
            self._ai_report_frame,
            textvariable=self._ai_status_var,
            bg="#1a1d20", fg=C_PANEL_VAL,
            font=("Courier New", 6),
            wraplength=200, justify=tk.LEFT,
            anchor="nw", padx=6, pady=5)
        self._ai_report_lbl.pack(fill=tk.X)

        sep()

        # ── ERASE BRUSH + UNDO ────────────────────────────────────────────────
        lbl("ERASE BRUSH SIZE")
        brush_row = tk.Frame(parent, bg=C_PANEL)
        brush_row.pack(fill=tk.X, padx=PX, pady=(0, 2))
        self._brush_var = tk.IntVar(value=self._erase_radius)
        self._brush_label = tk.Label(brush_row, text=f"{self._erase_radius}px",
                                     bg=C_PANEL, fg=C_PANEL_VAL,
                                     font=FONT_N, width=4)
        self._brush_label.pack(side=tk.RIGHT)
        tk.Scale(brush_row, from_=3, to=80, orient=tk.HORIZONTAL,
                 variable=self._brush_var, command=self._on_brush_change,
                 bg=C_PANEL, fg=C_PANEL_LBL, troughcolor="#1a1d20",
                 highlightthickness=0, showvalue=False
                 ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(parent, text="↩  Undo Erase", command=self._undo_erase,
                  bg=C_BTN_IDLE, fg=C_BTN_TEXT, font=FONT_N,
                  relief="flat", bd=0, padx=6, pady=4,
                  cursor="hand2", activebackground="#555"
                  ).pack(fill=tk.X, padx=PX, pady=(2, 4))

        sep()

        # ── ADJUSTMENTS ───────────────────────────────────────────────────────
        lbl("ADJUSTMENTS")
        grid_frame = tk.Frame(parent, bg=C_PANEL)
        grid_frame.pack(fill=tk.X, padx=PX, pady=(0, 2))
        grid_frame.columnconfigure(1, weight=1)

        def slider_row(row, label, var_attr, from_, to_, res, init):
            setattr(self, var_attr, tk.DoubleVar(value=init))
            tk.Label(grid_frame, text=label, bg=C_PANEL, fg=C_PANEL_LBL,
                     font=("Courier New", 6), anchor="w", width=7
                     ).grid(row=row, column=0, sticky="w", pady=2)
            val_lbl = tk.Label(grid_frame, text=f"{init:.1f}", bg=C_PANEL,
                               fg=C_PANEL_VAL, font=("Courier New", 6), width=3)
            val_lbl.grid(row=row, column=2, sticky="e", padx=(2, 0))
            def _cmd(v, vl=val_lbl):
                vl.config(text=f"{float(v):.1f}")
                self._on_slider_change()
            tk.Scale(grid_frame, from_=from_, to=to_, resolution=res,
                     orient=tk.HORIZONTAL,
                     variable=getattr(self, var_attr),
                     command=_cmd,
                     bg=C_PANEL, fg=C_PANEL_LBL, troughcolor="#1a1d20",
                     highlightthickness=0, showvalue=False
                     ).grid(row=row, column=1, sticky="ew", pady=1)

        slider_row(0, "BRIGHT",   "_bright_var",   0.2, 2.5, 0.05, 1.0)
        slider_row(1, "SHARP",    "_sharp_var",    0.0, 4.0, 0.10, 1.0)
        slider_row(2, "CONTRAST", "_contrast_var", 0.3, 2.5, 0.05, 1.0)
        slider_row(3, "SAT",      "_sat_var",      0.0, 2.5, 0.05, 1.0)

        tk.Button(parent, text="↺  Reset All", command=self._reset_adjustments,
                  bg=C_BTN_IDLE, fg=C_BTN_TEXT, font=FONT_N,
                  relief="flat", bd=0, padx=6, pady=4,
                  cursor="hand2", activebackground="#555"
                  ).pack(fill=tk.X, padx=PX, pady=(4, 4))

        sep()

        # ── ZOOM ──────────────────────────────────────────────────────────────
        lbl("ZOOM")
        zoom_row = tk.Frame(parent, bg=C_PANEL)
        zoom_row.pack(fill=tk.X, padx=PX, pady=(0, 6))

        for txt, cmd in [(" + ", self._zoom_in),
                          (" − ", self._zoom_out),
                          ("1:1", self._zoom_reset)]:
            tk.Button(zoom_row, text=txt, command=cmd,
                      bg=C_BTN_IDLE, fg=C_WHITE,
                      font=("Courier New", 9, "bold"),
                      relief="flat", bd=0, padx=8, pady=4,
                      cursor="hand2", activebackground="#555"
                      ).pack(side=tk.LEFT, padx=(0, 3))

        self._zoom_label = tk.Label(zoom_row, text="100%",
                                    bg=C_PANEL, fg=C_PANEL_VAL,
                                    font=("Courier New", 8, "bold"))
        self._zoom_label.pack(side=tk.LEFT, padx=(4, 0))

        # AI status var kept for _ai_enhance() compatibility – not shown in panel
        self._ai_status_var = tk.StringVar(value="—  not yet run")

    # ══════════════════════════════════════════════════════════════════════════
    #  EVENT BINDING
    # ══════════════════════════════════════════════════════════════════════════
    def _bind_all_canvas_events(self):
        c = self.crop_canvas
        # Crop / erase primary
        c.bind("<ButtonPress-1>",   self._on_press)
        c.bind("<B1-Motion>",       self._on_drag)
        c.bind("<ButtonRelease-1>", self._on_release)
        # Middle-button pan
        c.bind("<ButtonPress-2>",   self._pan_start)
        c.bind("<B2-Motion>",       self._pan_move)
        c.bind("<ButtonRelease-2>", self._pan_end)
        # Right-button pan (for laptop users)
        c.bind("<ButtonPress-3>",   self._pan_start)
        c.bind("<B3-Motion>",       self._pan_move)
        c.bind("<ButtonRelease-3>", self._pan_end)
        # Mouse-wheel zoom
        c.bind("<MouseWheel>",      self._on_wheel)          # Windows/macOS
        c.bind("<Button-4>",        self._on_wheel)          # Linux scroll up
        c.bind("<Button-5>",        self._on_wheel)          # Linux scroll down
        # Erase cursor ghost
        c.bind("<Motion>",          self._on_motion)
        c.bind("<Leave>",           self._erase_cursor_hide)

    # ══════════════════════════════════════════════════════════════════════════
    #  MODE
    # ══════════════════════════════════════════════════════════════════════════
    def _set_mode(self, mode: str):
        self._tool_mode = mode
        if mode == "crop":
            self._crop_btn.config(bg=C_ACCENT,    fg=C_WHITE,     font=("Courier New", 8, "bold"))
            self._erase_btn.config(bg=C_BTN_IDLE, fg=C_BTN_TEXT,  font=("Courier New", 8))
            self._hint_var.set(
                "CROP: drag empty = new box · body = move · corners = resize  "
                "|  scroll = zoom  |  mid-drag = pan")
            self.crop_canvas.config(cursor="crosshair")
            self._erase_cursor_hide()
        else:
            self._erase_btn.config(bg=C_ERASE,   fg=C_WHITE,     font=("Courier New", 8, "bold"))
            self._crop_btn.config(bg=C_BTN_IDLE, fg=C_BTN_TEXT,  font=("Courier New", 8))
            self._hint_var.set(
                "ERASE: paint to erase bg pixels  |  scroll = zoom  |  mid-drag = pan")
            self.crop_canvas.config(cursor="none")
        self._render_crop_canvas()

    # ══════════════════════════════════════════════════════════════════════════
    #  ASPECT RATIO
    # ══════════════════════════════════════════════════════════════════════════
    def _set_ratio(self, label: str, ratio):
        self._aspect_ratio = ratio
        # Re-fit existing crop box to new ratio
        if ratio and self.cx2 > self.cx1 and self.cy2 > self.cy1:
            w = self.cx2 - self.cx1
            h = int(w * ratio[1] / ratio[0])
            self.cy2 = self.cy1 + h
            self._render_crop_canvas()

    def _enforce_ratio(self):
        """Called after resize drag – clamp cy2 to match aspect ratio."""
        if not self._aspect_ratio:
            return
        rw, rh = self._aspect_ratio
        w = self.cx2 - self.cx1
        if w < 20:
            w = 20
        h = int(w * rh / rw)
        self.cy2 = self.cy1 + h

    # ══════════════════════════════════════════════════════════════════════════
    #  CANVAS EVENT DISPATCH
    # ══════════════════════════════════════════════════════════════════════════
    def _on_press(self, e):
        if self._tool_mode == "erase":
            self._push_undo()
            self._erase_at(e.x, e.y)
        else:
            self._cp_press(e)

    def _on_drag(self, e):
        if self._tool_mode == "erase":
            # Throttle: only redraw every ~30ms during drag for responsiveness
            now = getattr(self, "_last_erase_draw", 0)
            import time
            t = time.monotonic()
            self._erase_at(e.x, e.y, redraw=(t - now >= 0.03))
            if t - now >= 0.03:
                self._last_erase_draw = t
        else:
            self._cp_move(e)

    def _on_release(self, e):
        if self._tool_mode == "erase":
            self._render_crop_canvas()   # final redraw after stroke
        elif self._tool_mode == "crop":
            self._cp_release(e)

    def _on_motion(self, e):
        if self._tool_mode == "erase":
            self._draw_erase_cursor(e.x, e.y)

    def _on_wheel(self, e):
        # delta: positive = zoom in, negative = zoom out
        if hasattr(e, "delta") and e.delta != 0:
            direction = 1 if e.delta > 0 else -1
        elif e.num == 4:
            direction = 1
        elif e.num == 5:
            direction = -1
        else:
            direction = 0
        self._zoom_at(e.x, e.y, direction * 0.15)

    # ══════════════════════════════════════════════════════════════════════════
    #  PAN (middle-mouse / right-mouse drag)
    # ══════════════════════════════════════════════════════════════════════════
    def _pan_start(self, e):
        self._pan_drag = {"sx": e.x, "sy": e.y,
                          "ox": self._pan_offset[0], "oy": self._pan_offset[1]}
        self.crop_canvas.config(cursor="fleur")

    def _pan_move(self, e):
        if not self._pan_drag:
            return
        self._pan_offset[0] = self._pan_drag["ox"] + (e.x - self._pan_drag["sx"])
        self._pan_offset[1] = self._pan_drag["oy"] + (e.y - self._pan_drag["sy"])
        # Also shift crop box with pan
        dx = e.x - self._pan_drag["sx"]
        dy = e.y - self._pan_drag["sy"]
        self._render_crop_canvas()

    def _pan_end(self, e):
        self._pan_drag = {}
        self.crop_canvas.config(
            cursor="none" if self._tool_mode == "erase" else "crosshair")

    # ══════════════════════════════════════════════════════════════════════════
    #  ZOOM
    # ══════════════════════════════════════════════════════════════════════════
    def _zoom_at(self, cx: float, cy: float, delta: float):
        """Zoom by `delta` keeping the canvas point (cx, cy) fixed under cursor."""
        old_zoom = self._zoom_level
        new_zoom = max(0.1, min(8.0, round(old_zoom + delta, 3)))
        if new_zoom == old_zoom:
            return
        # Current total image origin on canvas:
        #   ox_total = (cw - dw) // 2 + pan_x
        # We need the image-space coordinate under the cursor:
        #   image_x = (cx - ox_total) / old_zoom
        # After zoom, keep that point pinned to cursor:
        #   new_ox_total = cx - image_x * new_zoom
        #   new_pan_x    = new_ox_total - (cw - new_dw) // 2
        try:
            cw = self.crop_canvas.winfo_width()  or 700
            ch = self.crop_canvas.winfo_height() or 500
        except Exception:
            cw, ch = 700, 500

        base = self._get_working_image()
        if not base:
            self._zoom_level = new_zoom
            self._update_zoom_label()
            self._render_crop_canvas()
            return
        iw, ih = base.size
        base_scale = min(cw / iw, ch / ih)

        old_scale = base_scale * old_zoom
        new_scale = base_scale * new_zoom
        old_dw = int(iw * old_scale)
        old_dh = int(ih * old_scale)
        new_dw = int(iw * new_scale)
        new_dh = int(ih * new_scale)

        ox_total = (cw - old_dw) // 2 + self._pan_offset[0]
        oy_total = (ch - old_dh) // 2 + self._pan_offset[1]

        img_x = (cx - ox_total) / old_scale
        img_y = (cy - oy_total) / old_scale

        new_ox_total = cx - img_x * new_scale
        new_oy_total = cy - img_y * new_scale

        self._pan_offset[0] = new_ox_total - (cw - new_dw) // 2
        self._pan_offset[1] = new_oy_total - (ch - new_dh) // 2
        self._zoom_level = new_zoom
        self._update_zoom_label()
        self._render_crop_canvas()

    def _zoom_in(self):
        cw = self.crop_canvas.winfo_width()  or 700
        ch = self.crop_canvas.winfo_height() or 500
        self._zoom_at(cw / 2, ch / 2, 0.25)

    def _zoom_out(self):
        cw = self.crop_canvas.winfo_width()  or 700
        ch = self.crop_canvas.winfo_height() or 500
        self._zoom_at(cw / 2, ch / 2, -0.25)

    def _zoom_reset(self):
        self._zoom_level = 1.0; self._pan_offset = [0, 0]
        self._update_zoom_label(); self._render_crop_canvas()

    def _update_zoom_label(self):
        if hasattr(self, "_zoom_label"):
            self._zoom_label.config(text=f"{int(self._zoom_level * 100)}%")

    # ══════════════════════════════════════════════════════════════════════════
    #  ERASE TOOL  (numpy fast path)
    # ══════════════════════════════════════════════════════════════════════════
    def _push_undo(self):
        img = self._get_working_image()
        if img:
            self._undo_stack.append(img.copy())
            if len(self._undo_stack) > 30:
                self._undo_stack.pop(0)

    def _undo_erase(self):
        if not self._undo_stack:
            return
        img = self._undo_stack.pop()
        if self.removal_done:
            self.removed_image = img
        else:
            self.orig_image = img
        self._enhanced_image = None
        self._render_crop_canvas()

    def _canvas_to_image(self, cx, cy):
        """Convert canvas pixel → image pixel accounting for zoom+pan+offset.
        self._co is already (center_offset + pan_offset) set during render.
        self._cs is the full scale (base_scale * zoom_level).
        """
        ox, oy = self._co          # correct total origin – do NOT add pan again
        ix = int((cx - ox) / self._cs)
        iy = int((cy - oy) / self._cs)
        return ix, iy

    def _erase_at(self, cx, cy, redraw: bool = True):
        """Erase a circular region around the canvas point (cx, cy).
        Pass redraw=False during fast drag — caller will redraw on release.
        """
        img = self._get_working_image()
        if not img:
            return

        ix, iy = self._canvas_to_image(cx, cy)
        # Brush radius in IMAGE pixels (independent of zoom)
        r = max(1, self._erase_radius)

        rgba = img.convert("RGBA")
        iw, ih = rgba.size

        # Guard: cursor fully outside image
        if ix + r < 0 or ix - r >= iw or iy + r < 0 or iy - r >= ih:
            return

        if _HAS_NUMPY:
            # ── fast numpy path ───────────────────────────────────────────────
            arr = np.array(rgba, dtype=np.uint8)
            x0 = max(0, ix - r); x1 = min(iw, ix + r + 1)
            y0 = max(0, iy - r); y1 = min(ih, iy + r + 1)
            if x0 >= x1 or y0 >= y1:
                return
            # vectorised circular mask
            yy, xx = np.ogrid[y0:y1, x0:x1]
            mask = (xx - ix) ** 2 + (yy - iy) ** 2 <= r * r
            arr[y0:y1, x0:x1][mask, 3] = 0
            rgba = Image.fromarray(arr, "RGBA")
        else:
            pixels = rgba.load()
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx*dx + dy*dy <= r*r:
                        px, py = ix + dx, iy + dy
                        if 0 <= px < iw and 0 <= py < ih:
                            pr, pg, pb, _ = pixels[px, py]
                            pixels[px, py] = (pr, pg, pb, 0)

        if self.removal_done:
            self.removed_image = rgba
        else:
            self.orig_image = rgba

        self._enhanced_image = None
        if redraw:
            self._render_crop_canvas()

    def _draw_erase_cursor(self, cx, cy):
        c = self.crop_canvas
        if self._erase_cursor:
            c.delete(self._erase_cursor)
        r = self._erase_radius   # display in screen pixels (not image pixels)
        self._erase_cursor = c.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline=C_ERASE, width=2, dash=(4, 3))

    def _erase_cursor_hide(self, _=None):
        if self._erase_cursor and hasattr(self, "crop_canvas"):
            try:
                self.crop_canvas.delete(self._erase_cursor)
            except Exception:
                pass
        self._erase_cursor = None

    def _on_brush_change(self, v):
        self._erase_radius = int(v)
        if hasattr(self, "_brush_label"):
            self._brush_label.config(text=f"{self._erase_radius}px")

    # ══════════════════════════════════════════════════════════════════════════
    #  AI ENHANCE  – analysis-first, targeted adjustments
    # ══════════════════════════════════════════════════════════════════════════
    def _ai_enhance(self):
        src = self._get_working_image()
        if not src:
            messagebox.showwarning("No Image", "Upload a photo first.")
            return

        self._ai_btn.config(state=tk.DISABLED, text="⏳ Analysing…")
        if hasattr(self, "_ai_badge_var"):
            self._ai_badge_var.set("analysing…")
            self._ai_dot.itemconfig("dot", fill="#cc8800")

        def run():
            try:
                result, report = self._smart_enhance(src)
                self._enhanced_image = result
                def _update():
                    self._bright_var.set(1.0)
                    self._sharp_var.set(1.0)
                    self._contrast_var.set(1.0)
                    self._sat_var.set(1.0)
                    self._on_slider_change()
                    self._render_crop_canvas()
                    self._ai_status_var.set(report)
                    self._ai_btn.config(state=tk.NORMAL,
                                        text="✨  AI Enhance  (smart auto-levels)")
                    self._set_status("✨ AI enhancement applied — see analysis panel.")
                    # Update dot → green, badge text, show report box
                    if hasattr(self, "_ai_badge_var"):
                        self._ai_badge_var.set("done ✓")
                        self._ai_dot.itemconfig("dot", fill=C_ACCENT)
                        self._ai_report_frame.pack(fill=tk.X, padx=10, pady=(0, 4))
                self.root.after(0, _update)
            except Exception as ex:
                def _err(e=ex):
                    self._ai_btn.config(state=tk.NORMAL,
                                        text="✨  AI Enhance  (smart auto-levels)")
                    self._set_status(f"Enhance failed: {e}")
                    self._ai_status_var.set(f"Error: {e}")
                    if hasattr(self, "_ai_badge_var"):
                        self._ai_badge_var.set("error")
                        self._ai_dot.itemconfig("dot", fill="#cc3333")
                        self._ai_report_frame.pack(fill=tk.X, padx=10, pady=(0, 4))
                self.root.after(0, _err)

        threading.Thread(target=run, daemon=True).start()

    def _smart_enhance(self, src: Image.Image):
        """
        High-accuracy passport photo enhancement using numpy:
          1. Per-channel histogram stretch (auto-levels) on foreground pixels only
          2. White-balance correction via grey-world on foreground
          3. Luminance CLAHE-style contrast boost (histogram equalization on L)
          4. Unsharp mask sharpening (amount tuned to blur score)
          5. Mild saturation boost
        Returns (enhanced_RGBA, report_string).
        """
        rgba = src.convert("RGBA")
        arr  = np.array(rgba, dtype=np.float32)   # H×W×4, 0-255

        alpha_mask = arr[:, :, 3] > 10            # foreground pixels

        report_lines = []

        # ── 1. PER-CHANNEL AUTO-LEVELS (stretch to 1–99 percentile) ──────────
        rgb_arr = arr[:, :, :3]
        fg      = rgb_arr[alpha_mask]             # foreground pixels only

        if fg.size > 0:
            lo  = np.percentile(fg, 1,  axis=0)  # shape (3,)
            hi  = np.percentile(fg, 99, axis=0)
            rng = np.where(hi - lo > 1, hi - lo, 1.0)
            stretched = np.clip((rgb_arr - lo) / rng * 255.0, 0, 255)
            arr[:, :, :3] = stretched
            report_lines.append(
                f"Auto-levels  R:{lo[0]:.0f}–{hi[0]:.0f}  "
                f"G:{lo[1]:.0f}–{hi[1]:.0f}  B:{lo[2]:.0f}–{hi[2]:.0f}")
        else:
            report_lines.append("Auto-levels: no foreground")

        # ── 2. WHITE-BALANCE (grey-world on foreground after stretch) ─────────
        fg2       = arr[:, :, :3][alpha_mask].astype(np.float32)
        if fg2.size > 0:
            mean_rgb  = fg2.mean(axis=0)                   # (R, G, B) means
            grey_mean = mean_rgb.mean()                    # target luminance
            gains     = np.clip(grey_mean / np.maximum(mean_rgb, 1), 0.75, 1.40)
            arr[:, :, :3] = np.clip(arr[:, :, :3] * gains, 0, 255)
            cast = mean_rgb.max() - mean_rgb.min()
            if cast > 8:
                report_lines.append(
                    f"WB corrected  gains R×{gains[0]:.2f} G×{gains[1]:.2f} B×{gains[2]:.2f}")
            else:
                report_lines.append("White balance OK")
        else:
            report_lines.append("WB: skip")

        # ── 3. LUMINANCE CONTRAST (histogram equalisation on Y, gentle blend) ─
        rgb_u8 = np.clip(arr[:, :, :3], 0, 255).astype(np.uint8)
        pil_rgb = Image.fromarray(rgb_u8, "RGB")

        # Convert to YCbCr, equalise Y only
        ycbcr = np.array(pil_rgb.convert("YCbCr"), dtype=np.float32)
        Y = ycbcr[:, :, 0]

        # Build histogram LUT only from foreground
        Y_fg = Y[alpha_mask].astype(np.uint8) if alpha_mask.any() else Y.ravel().astype(np.uint8)
        hist, _ = np.histogram(Y_fg, bins=256, range=(0, 255))
        cdf = hist.cumsum()
        cdf_min = int(cdf[cdf > 0][0]) if (cdf > 0).any() else 0
        total   = int(Y_fg.size)
        lut = np.clip(
            np.round((cdf - cdf_min) / max(total - cdf_min, 1) * 255), 0, 255
        ).astype(np.uint8)

        Y_eq = lut[Y.astype(np.uint8)].astype(np.float32)
        # Blend: 40% equalised + 60% original → gentle, not flat
        Y_blended = Y * 0.6 + Y_eq * 0.4
        # Shift toward passport target luminance (220 = bright neutral bg)
        fg_Y_mean = float(Y[alpha_mask].mean()) if alpha_mask.any() else 128.0
        target_Y  = 210.0
        if fg_Y_mean < 150:
            Y_blended = np.clip(Y_blended + (target_Y - fg_Y_mean) * 0.3, 0, 255)
            report_lines.append(f"Brightness↑ (Y {fg_Y_mean:.0f}→~{target_Y:.0f})")
        elif fg_Y_mean > 235:
            Y_blended = np.clip(Y_blended * 0.92, 0, 255)
            report_lines.append(f"Brightness↓ (over-exposed Y {fg_Y_mean:.0f})")
        else:
            report_lines.append(f"Brightness OK (Y {fg_Y_mean:.0f})")

        ycbcr[:, :, 0] = Y_blended
        pil_rgb = Image.fromarray(np.clip(ycbcr, 0, 255).astype(np.uint8), "YCbCr").convert("RGB")
        arr[:, :, :3] = np.array(pil_rgb, dtype=np.float32)

        # ── 4. UNSHARP MASK — amount driven by Laplacian variance ────────────
        gray = pil_rgb.convert("L")
        gray_arr = np.array(gray, dtype=np.float32)
        lap_var  = float(np.var(
            np.array(gray.filter(ImageFilter.FIND_EDGES), dtype=np.float32)))
        # lap_var ~0 = very blurry, >500 = sharp
        if lap_var < 80:
            usm_amount, usm_radius, usm_threshold = 2.0, 1.5, 2
            report_lines.append(f"Sharp↑↑ (blur score {lap_var:.0f})")
        elif lap_var < 300:
            usm_amount, usm_radius, usm_threshold = 1.2, 1.0, 3
            report_lines.append(f"Sharp↑ (soft score {lap_var:.0f})")
        else:
            usm_amount, usm_radius, usm_threshold = 0.5, 0.8, 5
            report_lines.append(f"Sharpness OK (score {lap_var:.0f})")

        pil_rgb = pil_rgb.filter(
            ImageFilter.UnsharpMask(
                radius=usm_radius, percent=int(usm_amount * 100),
                threshold=usm_threshold))
        arr[:, :, :3] = np.array(pil_rgb, dtype=np.float32)

        # ── 5. MILD SATURATION BOOST ──────────────────────────────────────────
        pil_rgb = Image.fromarray(np.clip(arr[:, :, :3], 0, 255).astype(np.uint8))
        pil_rgb = ImageEnhance.Color(pil_rgb).enhance(1.10)
        arr[:, :, :3] = np.array(pil_rgb, dtype=np.float32)
        report_lines.append("Saturation ×1.10")

        # ── Reassemble RGBA ───────────────────────────────────────────────────
        out = np.clip(arr, 0, 255).astype(np.uint8)
        result = Image.fromarray(out, "RGBA")

        report = "\n".join(report_lines)
        return result, report

    # ══════════════════════════════════════════════════════════════════════════
    #  MANUAL SLIDERS
    # ══════════════════════════════════════════════════════════════════════════
    def _on_slider_change(self, _=None):
        self._brightness_val = self._bright_var.get()
        self._sharpness_val  = self._sharp_var.get()
        self._contrast_val   = self._contrast_var.get()
        self._saturation_val = self._sat_var.get()
        self._render_crop_canvas()

    def _reset_adjustments(self):
        for var_attr, val in [("_bright_var", 1.0), ("_sharp_var", 1.0),
                              ("_contrast_var", 1.0), ("_sat_var", 1.0)]:
            getattr(self, var_attr).set(val)
        self._brightness_val = self._sharpness_val = 1.0
        self._contrast_val   = self._saturation_val = 1.0
        self._enhanced_image = None
        self._render_crop_canvas()

    def _apply_adjustments(self, img: Image.Image) -> Image.Image:
        """Apply brightness / sharpness / contrast / saturation (preserves alpha)."""
        rgba = img.convert("RGBA")
        rgb  = rgba.convert("RGB")
        if self._brightness_val != 1.0:
            rgb = ImageEnhance.Brightness(rgb).enhance(self._brightness_val)
        if self._contrast_val != 1.0:
            rgb = ImageEnhance.Contrast(rgb).enhance(self._contrast_val)
        if self._sharpness_val != 1.0:
            rgb = ImageEnhance.Sharpness(rgb).enhance(self._sharpness_val)
        if self._saturation_val != 1.0:
            rgb = ImageEnhance.Color(rgb).enhance(self._saturation_val)
        r, g, b = rgb.split()
        _, _, _, a = rgba.split()
        return Image.merge("RGBA", (r, g, b, a))

    # ══════════════════════════════════════════════════════════════════════════
    #  CANVAS RENDERING
    # ══════════════════════════════════════════════════════════════════════════
    def _render_crop_canvas(self):
        base = self._enhanced_image or (
            self.removed_image if self.removal_done else self.orig_image)
        if not base:
            return

        img = self._apply_adjustments(base)

        c = self.crop_canvas
        try:
            cw = c.winfo_width()  or 700
            ch = c.winfo_height() or 500
            c.delete("all")
        except tk.TclError:
            return

        iw, ih = img.size
        base_scale = min(cw / iw, ch / ih)
        scale      = base_scale * self._zoom_level
        dw = max(1, int(iw * scale))
        dh = max(1, int(ih * scale))

        self._cs = scale
        # Centre + pan offset
        ox = (cw - dw) // 2 + self._pan_offset[0]
        oy = (ch - dh) // 2 + self._pan_offset[1]
        self._co = (ox, oy)

        # ── checkerboard background ───────────────────────────────────────────
        sq = 12
        for row in range(0, ch, sq):
            for col in range(0, cw, sq):
                f = "#787878" if (row // sq + col // sq) % 2 else "#606060"
                c.create_rectangle(col, row, col+sq, row+sq, fill=f, outline="")

        # ── draw image ────────────────────────────────────────────────────────
        method = Image.Resampling.LANCZOS if scale <= 1.0 else Image.Resampling.NEAREST
        disp = img.resize((dw, dh), method)
        self._tk_img = ImageTk.PhotoImage(disp)
        c.create_image(ox, oy, anchor="nw", image=self._tk_img)

        # ── init crop box on first render ─────────────────────────────────────
        if self.cx2 == 0:
            self._init_crop_coords(ox, oy, dw, dh)

        # ── dim overlay + crop box — only in crop mode ───────────────────────
        if self._tool_mode == "crop":
            x1, y1, x2, y2 = self.cx1, self.cy1, self.cx2, self.cy2
            if x2 > x1 and y2 > y1:
                stipple = "gray50"
                for rect in [(0, 0, cw, y1), (0, y2, cw, ch),
                             (0, y1, x1, y2), (x2, y1, cw, y2)]:
                    c.create_rectangle(*rect, fill="#000", stipple=stipple, outline="")
            self._draw_crop_box(c)

        # ── erase cursor ─────────────────────────────────────────────────────
        # (redrawn on motion; keep id valid)
        self._erase_cursor = None

        # ── badge update ──────────────────────────────────────────────────────
        if self.removal_done:
            self.removal_badge_var.set("✓ Background removed")
            self.removal_badge.configure(fg=C_ACCENT)

    def _init_crop_coords(self, ox, oy, dw, dh):
        """Set default crop box to 70% of image area, centred."""
        margin_x = int(dw * 0.15)
        margin_y = int(dh * 0.15)
        self.cx1 = ox + margin_x
        self.cy1 = oy + margin_y
        self.cx2 = ox + dw - margin_x
        self.cy2 = oy + dh - margin_y

    def _draw_crop_box(self, c):
        x1, y1, x2, y2 = self.cx1, self.cy1, self.cx2, self.cy2
        if x2 <= x1 or y2 <= y1:
            return

        # Rule-of-thirds guides
        for i in (1, 2):
            xg = x1 + (x2 - x1) * i // 3
            yg = y1 + (y2 - y1) * i // 3
            c.create_line(xg, y1, xg, y2, fill="white", width=1,
                          dash=(4, 4), stipple="gray50")
            c.create_line(x1, yg, x2, yg, fill="white", width=1,
                          dash=(4, 4), stipple="gray50")

        # Border
        c.create_rectangle(x1, y1, x2, y2,
                           outline=C_CROP_C, width=2, tags="crop")

        # Corner handles
        hs = 10
        for (cx, cy) in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]:
            c.create_rectangle(cx-hs, cy-hs, cx+hs, cy+hs,
                               fill=C_HILIGHT, outline=C_DARK,
                               width=1, tags="crop")

        # Edge mid-point handles
        mx, my = (x1+x2)//2, (y1+y2)//2
        hse = 6
        for (hx, hy) in [(mx, y1), (mx, y2), (x1, my), (x2, my)]:
            c.create_rectangle(hx-hse, hy-hse, hx+hse, hy+hse,
                               fill=C_WHITE, outline=C_DARK,
                               width=1, tags="crop")

        # Size label
        iw_crop, ih_crop = self._crop_box_image_size()
        if iw_crop and ih_crop:
            c.create_text(x1+4, y2-4, anchor="sw",
                          text=f"{iw_crop}×{ih_crop}px",
                          fill="white", font=("Courier New", 7))

    def _crop_box_image_size(self):
        try:
            ox, oy = self._co
            iw = int((self.cx2 - self.cx1) / self._cs)
            ih = int((self.cy2 - self.cy1) / self._cs)
            return iw, ih
        except Exception:
            return None, None

    # ══════════════════════════════════════════════════════════════════════════
    #  CROP BOX DRAG
    # ══════════════════════════════════════════════════════════════════════════
    def _cp_hit(self, x, y):
        x1, y1, x2, y2 = self.cx1, self.cy1, self.cx2, self.cy2
        mx, my = (x1+x2)//2, (y1+y2)//2
        hs = 14

        # Corners
        for tag, (cx, cy) in [("TL",(x1,y1)),("TR",(x2,y1)),
                               ("BL",(x1,y2)),("BR",(x2,y2))]:
            if abs(x-cx) <= hs and abs(y-cy) <= hs:
                return tag
        # Mid edges
        for tag, (cx, cy) in [("MT",(mx,y1)),("MB",(mx,y2)),
                               ("ML",(x1,my)),("MR",(x2,my))]:
            if abs(x-cx) <= hs and abs(y-cy) <= hs:
                return tag
        if x1 <= x <= x2 and y1 <= y <= y2:
            return "body"
        return None

    def _cp_press(self, e):
        if self.cx2 == 0:
            cw = self.crop_canvas.winfo_width()
            ch = self.crop_canvas.winfo_height()
        hit = self._cp_hit(e.x, e.y)
        if not hit:
            self.cx1, self.cy1 = e.x, e.y
            self.cx2, self.cy2 = e.x, e.y
            hit = "BR"
        self.drag_data = dict(hit=hit, sx=e.x, sy=e.y,
                              ox1=self.cx1, oy1=self.cy1,
                              ox2=self.cx2, oy2=self.cy2)

    def _cp_move(self, e):
        d = self.drag_data
        if not d:
            return
        dx = e.x - d["sx"]
        dy = e.y - d["sy"]
        try:
            cw = self.crop_canvas.winfo_width()
            ch = self.crop_canvas.winfo_height()
        except tk.TclError:
            return
        hit = d["hit"]
        mn  = 20

        if hit == "body":
            w = d["ox2"] - d["ox1"]
            h = d["oy2"] - d["oy1"]
            self.cx1 = max(0, min(cw-w, d["ox1"]+dx))
            self.cy1 = max(0, min(ch-h, d["oy1"]+dy))
            self.cx2 = self.cx1 + w
            self.cy2 = self.cy1 + h
        elif hit == "TL":
            self.cx1 = max(0,            min(d["ox2"]-mn, d["ox1"]+dx))
            self.cy1 = max(0,            min(d["oy2"]-mn, d["oy1"]+dy))
        elif hit == "TR":
            self.cx2 = max(d["ox1"]+mn, min(cw, d["ox2"]+dx))
            self.cy1 = max(0,            min(d["oy2"]-mn, d["oy1"]+dy))
        elif hit == "BL":
            self.cx1 = max(0,            min(d["ox2"]-mn, d["ox1"]+dx))
            self.cy2 = max(d["oy1"]+mn, min(ch, d["oy2"]+dy))
        elif hit == "BR":
            self.cx2 = max(d["ox1"]+mn, min(cw, d["ox2"]+dx))
            self.cy2 = max(d["oy1"]+mn, min(ch, d["oy2"]+dy))
        elif hit == "MT":
            self.cy1 = max(0, min(d["oy2"]-mn, d["oy1"]+dy))
        elif hit == "MB":
            self.cy2 = max(d["oy1"]+mn, min(ch, d["oy2"]+dy))
        elif hit == "ML":
            self.cx1 = max(0, min(d["ox2"]-mn, d["ox1"]+dx))
        elif hit == "MR":
            self.cx2 = max(d["ox1"]+mn, min(cw, d["ox2"]+dx))

        self._enforce_ratio()
        self._render_crop_canvas()

    def _cp_release(self, e):
        self.drag_data = {}

    # ══════════════════════════════════════════════════════════════════════════
    #  CONFIRM CROP
    # ══════════════════════════════════════════════════════════════════════════
    def _confirm_crop(self):
        src = self._enhanced_image or (
            self.removed_image if self.removal_done else self.orig_image)
        if not src:
            return

        src = self._apply_adjustments(src)
        iw, ih = src.size
        ox, oy = self._co

        x1 = int((self.cx1 - ox) / self._cs)
        y1 = int((self.cy1 - oy) / self._cs)
        x2 = int((self.cx2 - ox) / self._cs)
        y2 = int((self.cy2 - oy) / self._cs)
        x1, x2 = max(0, x1), min(iw, x2)
        y1, y2 = max(0, y1), min(ih, y2)

        if x2 - x1 < 10 or y2 - y1 < 10:
            messagebox.showwarning("Bad Crop",
                                   "Selection too small. Try again.")
            return
        self.cropped_image = src.crop((x1, y1, x2, y2))
        self._show_step(self.STEP_CUSTOMIZE)

    # ══════════════════════════════════════════════════════════════════════════
    #  BACKGROUND REMOVAL  (unchanged logic, thread-safe)
    # ══════════════════════════════════════════════════════════════════════════
    def _start_bg_removal(self):
        threading.Thread(target=self._do_removal_wait, daemon=True).start()

    def _do_removal_wait(self):
        from rembg import remove
        self.bg_ready.wait()
        if not self.orig_image:
            return
        try:
            buf = BytesIO()
            self.orig_image.save(buf, format="PNG")
            result = remove(buf.getvalue(), session=self.session)
            if isinstance(result, bytes):
                self.removed_image = Image.open(BytesIO(result)).convert("RGBA")
            else:
                self.removed_image = result.convert("RGBA")   # type: ignore
            self.removal_done    = True
            self._enhanced_image = None
            self.root.after(0, self._on_removal_done)
        except Exception as e:
            self.root.after(0, self._set_status, f"BG removal failed: {e}")

    def _on_removal_done(self):
        self._set_status("Background removed ✓  Adjust crop and confirm.")
        if self.step == self.STEP_CROP and hasattr(self, "crop_canvas"):
            self._render_crop_canvas()
        if self.step == self.STEP_CUSTOMIZE:
            self._apply_customize()

    # ══════════════════════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    def _get_working_image(self):
        return self.removed_image if self.removal_done else self.orig_image