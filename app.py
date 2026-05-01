"""
app.py
PassportApp — shell, wizard bar, scrollable layout, step navigation.
Inherits UI logic from step mixins via multiple inheritance.
"""
import sys
import os
import tkinter as tk
from tkinter import ttk
import threading

from rembg import new_session

from constants import (
    C_BG, C_WHITE, C_CARD, C_DARK, C_MUTED, C_ACCENT, C_BORDER, C_TEXT,
    today_str,
)
from steps.upload    import UploadStep
from steps.crop      import CropStep
from steps.customize import CustomizeStep
from steps.print_step import PrintStep


class PassportApp(UploadStep, CropStep, CustomizeStep, PrintStep):  # type: ignore
    STEP_UPLOAD    = 0
    STEP_CROP      = 1
    STEP_CUSTOMIZE = 2
    STEP_PRINT     = 3

    def __init__(self, root):
        self.root = root
        self.root.title("passport. photo maker.")
        self.root.minsize(820, 620)
        self.root.resizable(True, True)
        self.root.configure(bg=C_BG)
        # Open maximised; fall back to a large fixed size on non-Windows
        try:
            self.root.state("zoomed")          # Windows / some Linux WMs
        except tk.TclError:
            self.root.geometry("1280x800")     # macOS / other

        # ── Image state ───────────────────────────────────────────────────────
        self.step          = self.STEP_UPLOAD
        self.session       = None
        self.bg_ready      = threading.Event()

        self.orig_image    = None   # original upload
        self.removed_image = None   # after AI bg removal
        self.removal_done  = False
        self.cropped_image = None   # after crop confirm
        self.final_image   = None   # after customize
        self.sheet_image   = None

        # Crop drag state
        self.drag_data = {}
        self.cx1 = self.cy1 = self.cx2 = self.cy2 = 0
        self._cs = 1.0
        self._co = (0, 0)
        self._tk_img = None

        # ── Shared tk variables (used across steps) ───────────────────────────
        self.var_bg_color      = tk.StringVar(value="White")
        self.var_text_color    = tk.StringVar(value="Black")
        self.var_text_bg_color = tk.StringVar(value="None")
        self.var_photo_size    = tk.StringVar(value="A4 (31×39mm)")
        self.var_text1         = tk.StringVar(value="")
        self.var_text2         = tk.StringVar(value=today_str())
        self.var_num_photos    = tk.StringVar(value="")
        self.var_paper_size    = tk.StringVar(value="A4 (8.27 x 11.69 in)")

        self.var_paper_size.trace_add("write", self._on_paper_size_change)

        self._build_shell()
        threading.Thread(target=self._load_session, daemon=True).start()

    def _on_paper_size_change(self, *args):
        val = self.var_paper_size.get()
        if "A4" in val:
            self.var_photo_size.set("A4 (31×39mm)")
        elif "Card" in val:
            self.var_photo_size.set("Small (29×33mm)")

    # ══════════════════════════════════════════════════════════════════════════
    #  Shell — fixed header + scrollable content + fixed footer
    # ══════════════════════════════════════════════════════════════════════════
    def _build_shell(self):
        # Fixed header
        self.header = tk.Frame(self.root, bg=C_BG)
        self.header.pack(fill=tk.X, side=tk.TOP)

        self.title_frame = tk.Frame(self.header, bg=C_BG)
        self.title_frame.pack(pady=(20, 0))
        tk.Label(self.title_frame, text="passport.",
                 bg=C_BG, fg=C_TEXT, font=("Georgia", 22)).pack()
        tk.Label(self.title_frame, text="photo maker.",
                 bg=C_BG, fg=C_TEXT,
                 font=("Georgia", 26, "italic", "bold")).pack()
        tk.Label(self.title_frame,
                 text="REMOVE BG  ·  CROP  ·  CUSTOMIZE  ·  PRINT",
                 bg=C_BG, fg=C_MUTED,
                 font=("Courier New", 8, "bold")).pack(pady=(4, 0))

        self.wizard_frame = tk.Frame(self.header, bg=C_BG)
        self.wizard_frame.pack(pady=(14, 6))
        self._build_wizard_bar()

        tk.Frame(self.root, bg=C_BORDER, height=1).pack(fill=tk.X)

        # Fixed footer — always visible
        self.footer = tk.Frame(self.root, bg=C_BG, height=60)
        self.footer.pack(fill=tk.X, side=tk.BOTTOM)
        self.footer.pack_propagate(False)
        tk.Frame(self.root, bg=C_BORDER, height=1).pack(
            fill=tk.X, side=tk.BOTTOM)

        # Status bar above footer
        self.status_var = tk.StringVar(value="Loading AI model…")
        self.status_lbl = tk.Label(
            self.root, textvariable=self.status_var,
            bg=C_BG, fg=C_MUTED, font=("Courier New", 8))
        self.status_lbl.pack(side=tk.BOTTOM, pady=2)

        tk.Label(self.footer,
                 text="powered by rembg  ·  pillow",
                 bg=C_BG, fg=C_MUTED,
                 font=("Courier New", 8)).pack(side=tk.RIGHT, padx=16)

        self.footer_btns = tk.Frame(self.footer, bg=C_BG)
        self.footer_btns.pack(side=tk.LEFT, padx=16, pady=10)

        # Scrollable content area
        wrap = tk.Frame(self.root, bg=C_BG)
        wrap.pack(fill=tk.BOTH, expand=True)

        self._scroll_canvas = tk.Canvas(wrap, bg=C_BG, highlightthickness=0)
        vbar = ttk.Scrollbar(wrap, orient="vertical",
                             command=self._scroll_canvas.yview)
        self._scroll_canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.content = tk.Frame(self._scroll_canvas, bg=C_BG)
        self._scrollable_inner = self.content   # permanent reference
        self._scroll_win = self._scroll_canvas.create_window(
            (0, 0), window=self.content, anchor="nw")

        # Fixed-height container for steps that must NOT scroll (e.g. Crop).
        # It sits on top of the scroll canvas and is shown/hidden per step.
        self.fixed_content = tk.Frame(wrap, bg=C_BG)
        # (not packed yet — _show_step manages visibility)

        self.content.bind("<Configure>", self._on_content_resize)
        self._scroll_canvas.bind("<Configure>", self._on_canvas_resize)
        self._scroll_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self._scroll_canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units"))

        self._show_step(self.STEP_UPLOAD)

    def _on_content_resize(self, e):
        self._scroll_canvas.configure(
            scrollregion=self._scroll_canvas.bbox("all"))

    def _on_canvas_resize(self, e):
        self._scroll_canvas.itemconfig(self._scroll_win, width=e.width)

    # ── Wizard bar ────────────────────────────────────────────────────────────
    def _build_wizard_bar(self):
        for w in self.wizard_frame.winfo_children():
            w.destroy()
        for i, name in enumerate(["UPLOAD", "CROP", "CUSTOMIZE", "PRINT"]):
            if i > 0:
                tk.Frame(self.wizard_frame, bg=C_BORDER,
                         width=56, height=1).pack(side=tk.LEFT, pady=12)
            done    = i < self.step
            current = i == self.step
            cbg    = C_ACCENT if done else (C_DARK if current else C_WHITE)
            cfg    = C_WHITE  if (done or current) else C_MUTED
            cbord  = C_ACCENT if done else (C_DARK if current else C_BORDER)

            f = tk.Frame(self.wizard_frame, bg=C_BG)
            f.pack(side=tk.LEFT)
            c = tk.Canvas(f, width=26, height=26,
                          bg=C_BG, highlightthickness=0)
            c.pack()
            c.create_oval(1, 1, 25, 25, fill=cbg, outline=cbord, width=2)
            c.create_text(13, 13, text=str(i + 1),
                          fill=cfg, font=("Courier New", 8, "bold"))
            tk.Label(f, text=name, bg=C_BG,
                     fg=C_TEXT if current else C_MUTED,
                     font=("Courier New", 7,
                           "bold" if current else "normal")).pack()

    # ── Footer buttons ────────────────────────────────────────────────────────
    def _set_footer(self, btns):
        """btns = list of (label, command, style) — style: 'dark'|'outline'"""
        for w in self.footer_btns.winfo_children():
            w.destroy()
        for label, cmd, style in btns:
            if style == "dark":
                b = tk.Button(self.footer_btns, text=label, command=cmd,
                              bg=C_DARK, fg=C_WHITE,
                              font=("Courier New", 9, "bold"),
                              relief="flat", bd=0,
                              padx=16, pady=6, cursor="hand2",
                              activebackground="#333")
            else:
                b = tk.Button(self.footer_btns, text=label, command=cmd,
                              bg=C_WHITE, fg=C_DARK,
                              font=("Courier New", 9),
                              relief="solid", bd=1,
                              padx=14, pady=5, cursor="hand2",
                              activebackground=C_BG)
            b.pack(side=tk.LEFT, padx=(0, 8))

    # ── Step navigation ───────────────────────────────────────────────────────
    def _show_step(self, step):
        self.step = step
        self._build_wizard_bar()
        self._scroll_canvas.yview_moveto(0)

        # Steps that need a fixed (non-scrolling) layout use fixed_content;
        # all other steps use the normal scrollable content frame.
        _FIXED_STEPS = {self.STEP_CROP}

        if step in _FIXED_STEPS:
            # Hide scroll canvas, show fixed frame
            self._scroll_canvas.pack_forget()
            for w in self.fixed_content.winfo_children():
                w.destroy()
            self.fixed_content.pack(fill=tk.BOTH, expand=True)
            # Point self.content at fixed_content so mixins write into it
            self.content = self.fixed_content
        else:
            # Hide fixed frame, restore scroll canvas
            self.fixed_content.pack_forget()
            self._scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            # Restore self.content to the scrollable inner frame
            self.content = self._scrollable_inner
            for w in self.content.winfo_children():
                w.destroy()

        if step == self.STEP_UPLOAD:
            self.title_frame.pack(pady=(20, 0))
        else:
            self.title_frame.pack_forget()

        {
            self.STEP_UPLOAD:    self._build_upload,
            self.STEP_CROP:      self._build_crop,
            self.STEP_CUSTOMIZE: self._build_customize,
            self.STEP_PRINT:     self._build_print,
        }[step]()

    # ── Shared helpers ────────────────────────────────────────────────────────
    def _set_status(self, msg):
        if hasattr(self, "status_var"):
            self.root.after(0, self.status_var.set, msg)

    def _card(self, pady=(0, 12)):
        outer = tk.Frame(self.content, bg=C_BORDER)
        outer.pack(fill=tk.X, padx=28, pady=pady)
        inner = tk.Frame(outer, bg=C_CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        return inner

    def _load_session(self):
        try:
            self._set_status("Loading AI model… (first run ~170 MB download)")
            self.session = new_session("u2net")
            self.bg_ready.set()
            self._set_status("Model ready.")
            if self.orig_image and not self.removal_done:
                self._start_bg_removal()
        except Exception as e:
            self._set_status(f"⚠ Model load failed: {e}")

    def _start_over(self):
        self.orig_image    = None
        self.removed_image = None
        self.removal_done  = False
        self.cropped_image = None
        self.final_image   = None
        self.sheet_image   = None
        self.cx1 = self.cy1 = self.cx2 = self.cy2 = 0
        self._show_step(self.STEP_UPLOAD)