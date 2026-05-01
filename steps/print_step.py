"""
steps/print_step.py
Step 4 — Print
Side-by-side layout: sheet preview (left) | controls panel (right)
Matches wireframe: steps bar → [preview | controls] → footer buttons
"""
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import typing

from constants import (
    C_BG, C_WHITE, C_CARD, C_DARK, C_MUTED, C_ACCENT, C_BORDER, C_TEXT,
    PASSPORT_SIZES, PAPER_SIZES, SHEET_MARGIN, SHEET_GAP
)


class PrintStep:
    """Mixin — mixed into PassportApp."""

    if typing.TYPE_CHECKING:
        STEP_CUSTOMIZE: int
        final_image: typing.Any
        sheet_image: typing.Any
        root: tk.Tk
        content: tk.Frame
        var_photo_size: tk.StringVar
        var_paper_size: tk.StringVar
        var_num_photos: tk.StringVar
        sheet_dot: tk.Canvas
        sheet_status_var: tk.StringVar
        sheet_canvas: tk.Canvas
        def _set_footer(self, btns: list) -> None: ...
        def _show_step(self, step: int) -> None: ...
        def _card(self, pady: tuple = (0, 12)) -> tk.Frame: ...
        def _apply_customize(self) -> None: ...
        def _start_over(self) -> None: ...
        def _set_status(self, msg: str) -> None: ...

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_print(self):
        self._set_footer([
            ("↓  download sheet", self._save_sheet,   "dark"),
            ("🖨  print sheet",    self._print_sheet,  "dark"),
            ("↺  start over",     self._start_over,   "outline"),
            ("← back",
             lambda: self._show_step(self.STEP_CUSTOMIZE), "outline"),
        ])

        # ── Outer container: fills the scrollable content area ────────────────
        outer = tk.Frame(self.content, bg=C_BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=28, pady=12)

        # ── Top border card (mimics the wireframe outer box) ──────────────────
        main_card_border = tk.Frame(outer, bg=C_BORDER)
        main_card_border.pack(fill=tk.BOTH, expand=True)
        main_card = tk.Frame(main_card_border, bg=C_CARD)
        main_card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # ── Side-by-side row ──────────────────────────────────────────────────
        body = tk.Frame(main_card, bg=C_CARD, height=550)
        body.pack(fill=tk.BOTH, expand=True)
        body.pack_propagate(False)
        body.columnconfigure(0, weight=3)   # preview — wider
        body.columnconfigure(1, weight=0)   # separator
        body.columnconfigure(2, weight=2)   # controls
        body.rowconfigure(0, weight=1)

        # ── LEFT: Sheet Preview ───────────────────────────────────────────────
        left = tk.Frame(body, bg=C_CARD)
        left.grid(row=0, column=0, sticky="nsew")

        tk.Label(left, text="SHEET PREVIEW",
                 bg=C_CARD, fg=C_MUTED,
                 font=("Courier New", 8, "bold")
                 ).pack(anchor="w", padx=16, pady=(12, 4))

        self.sheet_canvas = tk.Canvas(left, bg="#d8d8d8",
                                      highlightthickness=0, height=450)
        self.sheet_canvas.pack(fill=tk.BOTH, expand=True,
                               padx=12, pady=(0, 12))
        self.sheet_canvas.bind(
            "<Configure>", lambda e: self._render_sheet_canvas())

        # Status dot + label under preview
        dot_row = tk.Frame(left, bg=C_CARD)
        dot_row.pack(anchor="w", padx=14, pady=(0, 10))
        self.sheet_dot = tk.Canvas(dot_row, width=12, height=12,
                                   bg=C_CARD, highlightthickness=0)
        self.sheet_dot.pack(side=tk.LEFT, padx=(0, 6))
        self.sheet_dot.create_oval(2, 2, 10, 10, fill="#aaa", outline="")
        self.sheet_status_var = tk.StringVar(value="No sheet generated yet.")
        tk.Label(dot_row, textvariable=self.sheet_status_var,
                 bg=C_CARD, fg=C_MUTED,
                 font=("Courier New", 8)).pack(side=tk.LEFT)

        # ── Divider ───────────────────────────────────────────────────────────
        tk.Frame(body, bg=C_BORDER, width=1).grid(
            row=0, column=1, sticky="ns")

        # ── RIGHT: Controls Panel ─────────────────────────────────────────────
        right = tk.Frame(body, bg=C_CARD)
        right.grid(row=0, column=2, sticky="nsew")

        tk.Label(right, text="FUNCTIONALITY",
                 bg=C_CARD, fg=C_MUTED,
                 font=("Courier New", 8, "bold")
                 ).pack(anchor="w", padx=16, pady=(12, 8))

        # ── Paper size dropdown ───────────────────────────────────────────────
        paper_frame = tk.Frame(right, bg=C_CARD)
        paper_frame.pack(fill=tk.X, padx=16, pady=(0, 12))

        tk.Label(paper_frame, text="PAPER SIZE",
                 bg=C_CARD, fg=C_MUTED,
                 font=("Courier New", 7, "bold")).pack(anchor="w")

        paper_dd = tk.OptionMenu(paper_frame, self.var_paper_size,
                                 *list(PAPER_SIZES.keys()))
        paper_dd.configure(bg=C_WHITE, fg=C_DARK,
                           font=("Courier New", 9),
                           relief="solid", bd=1,
                           highlightthickness=0,
                           activebackground=C_BG,
                           width=20)
        paper_dd["menu"].configure(bg=C_WHITE, fg=C_DARK,
                                   font=("Courier New", 9))
        paper_dd.pack(fill=tk.X, pady=(4, 0))

        # ── Photo size dropdown ───────────────────────────────────────────────
        ps_frame = tk.Frame(right, bg=C_CARD)
        ps_frame.pack(fill=tk.X, padx=16, pady=(0, 12))

        tk.Label(ps_frame, text="PHOTO SIZE",
                 bg=C_CARD, fg=C_MUTED,
                 font=("Courier New", 7, "bold")).pack(anchor="w")

        photo_dd = tk.OptionMenu(ps_frame, self.var_photo_size,
                                 *list(PASSPORT_SIZES.keys()))
        photo_dd.configure(bg=C_WHITE, fg=C_DARK,
                           font=("Courier New", 9),
                           relief="solid", bd=1,
                           highlightthickness=0,
                           activebackground=C_BG,
                           width=20)
        photo_dd["menu"].configure(bg=C_WHITE, fg=C_DARK,
                                   font=("Courier New", 9))
        photo_dd.pack(fill=tk.X, pady=(4, 0))
        self.var_photo_size.trace_add(
            "write", lambda *a: self._apply_customize())

        # ── Number of photos + generate button ────────────────────────────────
        num_label_row = tk.Frame(right, bg=C_CARD)
        num_label_row.pack(fill=tk.X, padx=16, pady=(0, 4))
        tk.Label(num_label_row, text="NO. OF PHOTOS",
                 bg=C_CARD, fg=C_MUTED,
                 font=("Courier New", 7, "bold")).pack(side=tk.LEFT)

        num_gen_row = tk.Frame(right, bg=C_CARD)
        num_gen_row.pack(fill=tk.X, padx=16, pady=(0, 14))

        self.num_entry = tk.Entry(
            num_gen_row, textvariable=self.var_num_photos,
            bg="#f0ede6", fg=C_DARK,
            font=("Courier New", 10),
            relief="solid", bd=1,
            insertbackground=C_DARK,
            width=8)
        self.num_entry.pack(side=tk.LEFT, ipady=6, padx=(0, 8))

        if not self.var_num_photos.get():
            self.num_entry.insert(0, "e.g. 6")
            self.num_entry.configure(fg=C_MUTED)
        self.num_entry.bind("<FocusIn>", lambda e: (
            (self.num_entry.delete(0, tk.END),
             self.num_entry.configure(fg=C_DARK))
            if self.num_entry.get() == "e.g. 6" else None))
        self.num_entry.bind("<FocusOut>", lambda e: (
            (self.num_entry.insert(0, "e.g. 6"),
             self.num_entry.configure(fg=C_MUTED))
            if not self.num_entry.get() else None))

        tk.Button(num_gen_row, text="generate sheet",
                  command=self._generate_sheet_manual,
                  bg=C_DARK, fg=C_WHITE,
                  font=("Courier New", 9, "bold"),
                  relief="flat", bd=0,
                  padx=12, pady=6,
                  cursor="hand2",
                  activebackground="#333"
                  ).pack(side=tk.LEFT)

        # ── Divider ───────────────────────────────────────────────────────────
        tk.Frame(right, bg=C_BORDER, height=1).pack(
            fill=tk.X, padx=16, pady=(0, 12))

        # ── Quick-generate hint ───────────────────────────────────────────────
        tk.Label(right,
                 text="Leave blank to auto-fill\nthe sheet with one row.",
                 bg=C_CARD, fg=C_MUTED,
                 font=("Courier New", 8),
                 justify="left"
                 ).pack(anchor="w", padx=16)

        # ── Auto-generate sheet on step entry ─────────────────────────────────
        if self.final_image:
            self._build_sheet(None)

        if self.sheet_image:
            self._mark_sheet_ready()

    # ── Sheet generation ──────────────────────────────────────────────────────
    def _generate_sheet_manual(self):
        raw = self.var_num_photos.get().strip()
        if raw in ("", "e.g. 6", "Enter the value"):
            n = None
        else:
            try:
                n = int(raw)
                if not (1 <= n <= 50):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Invalid", "Enter a number 1–50.")
                return
        self._build_sheet(n)

    def _build_sheet(self, count):
        if not self.final_image:
            messagebox.showwarning("No Image", "Complete Customize first.")
            return

        paper_key = self.var_paper_size.get()
        SW, SH = PAPER_SIZES.get(paper_key, (2480, 3508))
        margin, gap = SHEET_MARGIN, SHEET_GAP
        pw, ph = self.final_image.size

        cols = max(1, (SW - 2*margin + gap) // (pw + gap))
        max_rows = max(1, (SH - 2*margin + gap) // (ph + gap))

        if count is None:
            count = cols
            rows = 1
        else:
            count = min(count, cols * max_rows)
            rows = (count + cols - 1) // cols

        sheet = Image.new("RGB", (SW, SH), "#ffffff")
        placed = 0
        photo_r = self.final_image.convert("RGB")
        for r in range(rows):
            for c in range(cols):
                if placed >= count:
                    break
                sheet.paste(photo_r,
                            (margin + c*(pw+gap), margin + r*(ph+gap)))
                placed += 1

        self.sheet_image = sheet
        self.root.after(0, self._mark_sheet_ready)
        self.root.after(0, self._render_sheet_canvas)

    def _mark_sheet_ready(self):
        if hasattr(self, "sheet_dot"):
            self.sheet_dot.delete("all")
            self.sheet_dot.create_oval(2, 2, 10, 10,
                                       fill=C_ACCENT, outline="")
        if hasattr(self, "sheet_status_var"):
            self.sheet_status_var.set("Sheet ready! Download or print below.")

    def _render_sheet_canvas(self):
        if not hasattr(self, "sheet_canvas") or not self.sheet_image:
            return
        c = self.sheet_canvas
        try:
            cw = c.winfo_width() or 500
            ch = c.winfo_height() or 480
            c.delete("all")
        except tk.TclError:
            return
        c.create_rectangle(0, 0, cw, ch, fill="#d8d8d8", outline="")

        iw, ih = self.sheet_image.size
        scale = min(cw / iw, ch / ih, 1.0)
        dw, dh = max(1, int(iw * scale)), max(1, int(ih * scale))
        ox, oy = (cw - dw) // 2, (ch - dh) // 2

        disp = self.sheet_image.resize((dw, dh), Image.Resampling.LANCZOS)
        self._sheet_tk = ImageTk.PhotoImage(disp)
        c.create_image(ox, oy, anchor="nw", image=self._sheet_tk)

    # ── Save / Print ──────────────────────────────────────────────────────────
    def _save_sheet(self):
        if not self.sheet_image:
            messagebox.showwarning("No Sheet", "Generate a sheet first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG file", "*.png"), ("JPEG file", "*.jpg")])
        if not path:
            return
        fmt = "JPEG" if path.lower().endswith(".jpg") else "PNG"
        img = self.sheet_image.convert("RGB") if fmt == "JPEG" \
            else self.sheet_image
        img.save(path, fmt, dpi=(300, 300))
        messagebox.showinfo("Saved", f"Sheet saved:\n{path}")
        self._set_status(f"💾 Saved: {os.path.basename(path)}")

    def _print_sheet(self):
        if not self.sheet_image:
            messagebox.showwarning("No Sheet", "Generate a sheet first.")
            return
        import tempfile
        import subprocess
        import sys
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            self.sheet_image.save(tmp_path, "PNG", dpi=(300, 300))
        except Exception as e:
            messagebox.showerror("Error", f"Could not prepare file:\n{e}")
            return
        try:
            if sys.platform == "win32":
                os.startfile(tmp_path, "print")
            else:
                subprocess.run(["lpr", tmp_path])
            self._set_status("🖨 Print dialog opened.")
        except Exception as e:
            messagebox.showerror(
                "Print Error",
                f"Could not open print dialog:\n{e}\n\n"
                f"Try downloading and printing manually.")
