"""
steps/customize.py
Step 3 — Customize
Side-by-side layout: preview (left) | controls panel (right)
Matches wireframe: steps bar → [preview | controls] → footer buttons
"""
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import typing

from constants import (
    C_BG, C_WHITE, C_CARD, C_DARK, C_MUTED, C_ACCENT, C_BORDER, C_TEXT,
    BG_COLORS, TEXT_COLORS, TEXT_BG_COLORS, PASSPORT_SIZES,
)


class CustomizeStep:
    """Mixin — mixed into PassportApp."""

    if typing.TYPE_CHECKING:
        STEP_CROP: int
        STEP_PRINT: int
        content: tk.Frame
        orig_image: typing.Any
        removed_image: typing.Any
        cropped_image: typing.Any
        final_image: typing.Any
        root: tk.Tk
        var_bg_color: tk.StringVar
        var_text_color: tk.StringVar
        var_text_bg_color: tk.StringVar
        var_photo_size: tk.StringVar
        var_text1: tk.StringVar
        var_text2: tk.StringVar
        preview_canvas: tk.Canvas
        def _set_footer(self, btns: list) -> None: ...
        def _show_step(self, step: int) -> None: ...
        def _card(self, pady: tuple = (0, 12)) -> tk.Frame: ...
        def _set_status(self, msg: str) -> None: ...

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_customize(self):
        self._set_footer([
            ("print sheet →",
             lambda: self._show_step(self.STEP_PRINT), "dark"),
            ("↓  download photo",
             self._save_single_photo, "outline"),
            ("← back to crop",
             lambda: self._show_step(self.STEP_CROP), "outline"),
        ])

        # ── Outer container ───────────────────────────────────────────────────
        outer = tk.Frame(self.content, bg=C_BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=28, pady=12)

        # ── Main card border ──────────────────────────────────────────────────
        main_card_border = tk.Frame(outer, bg=C_BORDER)
        main_card_border.pack(fill=tk.BOTH, expand=True)
        main_card = tk.Frame(main_card_border, bg=C_CARD)
        main_card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # ── Side-by-side body ─────────────────────────────────────────────────
        body = tk.Frame(main_card, bg=C_CARD, height=700)
        body.pack(fill=tk.BOTH, expand=True)
        body.pack_propagate(False)
        body.columnconfigure(0, weight=3)   # preview — wider
        body.columnconfigure(1, weight=0)   # separator
        body.columnconfigure(2, weight=2)   # controls
        body.rowconfigure(0, weight=1)

        # ── LEFT: Preview ─────────────────────────────────────────────────────
        left = tk.Frame(body, bg=C_CARD)
        left.grid(row=0, column=0, sticky="nsew")

        tk.Label(left, text="PREVIEW",
                 bg=C_CARD, fg=C_MUTED,
                 font=("Courier New", 8, "bold")
                 ).pack(anchor="w", padx=16, pady=(12, 4))

        self.preview_canvas = tk.Canvas(left, bg="#c0c0c0",
                                        highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True,
                                 padx=12, pady=(0, 12))
        self.preview_canvas.bind(
            "<Configure>", lambda e: self._render_preview())

        # ── Divider ───────────────────────────────────────────────────────────
        tk.Frame(body, bg=C_BORDER, width=1).grid(
            row=0, column=1, sticky="ns")

        # ── RIGHT: Controls ───────────────────────────────────────────────────
        right = tk.Frame(body, bg=C_CARD)
        right.grid(row=0, column=2, sticky="nsew")

        tk.Label(right, text="CUSTOMIZE",
                 bg=C_CARD, fg=C_MUTED,
                 font=("Courier New", 8, "bold")
                 ).pack(anchor="w", padx=16, pady=(12, 8))

        # helper — labeled dropdown
        def make_dd(parent, label, var, options):
            f = tk.Frame(parent, bg=C_CARD)
            f.pack(fill=tk.X, padx=16, pady=(0, 12))
            tk.Label(f, text=label.upper(),
                     bg=C_CARD, fg=C_MUTED,
                     font=("Courier New", 7, "bold")).pack(anchor="w")
            om = tk.OptionMenu(f, var, *options)
            om.configure(bg=C_WHITE, fg=C_DARK,
                         font=("Courier New", 9),
                         relief="solid", bd=1,
                         highlightthickness=0,
                         activebackground=C_BG, width=20)
            om["menu"].configure(bg=C_WHITE, fg=C_DARK,
                                 font=("Courier New", 9))
            om.pack(fill=tk.X, pady=(4, 0))
            var.trace_add("write", lambda *a: self._apply_customize())

        make_dd(right, "Background Color",
                self.var_bg_color, list(BG_COLORS.keys()))
        make_dd(right, "Text Color",
                self.var_text_color, list(TEXT_COLORS.keys()))
        make_dd(right, "Text BG Color",
                self.var_text_bg_color, list(TEXT_BG_COLORS.keys()))
        make_dd(right, "Photo Size",
                self.var_photo_size, list(PASSPORT_SIZES.keys()))

        # ── Divider ───────────────────────────────────────────────────────────
        tk.Frame(right, bg=C_BORDER, height=1).pack(
            fill=tk.X, padx=16, pady=(0, 12))

        # helper — labeled text entry
        def make_entry(parent, label, var, placeholder):
            f = tk.Frame(parent, bg=C_CARD)
            f.pack(fill=tk.X, padx=16, pady=(0, 12))
            tk.Label(f, text=label.upper(),
                     bg=C_CARD, fg=C_MUTED,
                     font=("Courier New", 7, "bold")).pack(anchor="w")
            e = tk.Entry(f, textvariable=var,
                         bg="#f0ede6", fg=C_DARK,
                         font=("Courier New", 10),
                         relief="solid", bd=1,
                         insertbackground=C_DARK)
            e.pack(fill=tk.X, ipady=7, pady=(4, 0))
            if not var.get():
                e.insert(0, placeholder)
                e.configure(fg=C_MUTED)

                def on_focus_in(ev, entry=e, ph=placeholder):
                    if entry.get() == ph:
                        entry.delete(0, tk.END)
                        entry.configure(fg=C_DARK)

                def on_focus_out(ev, entry=e, ph=placeholder):
                    if not entry.get():
                        entry.insert(0, ph)
                        entry.configure(fg=C_MUTED)

                e.bind("<FocusIn>",  on_focus_in)
                e.bind("<FocusOut>", on_focus_out)
            var.trace_add("write", lambda *a: self._apply_customize())

        make_entry(right, "Text Overlay (Line 1)",
                   self.var_text1, "e.g. Name (leave blank to skip)")
        make_entry(right, "Text Overlay (Line 2)",
                   self.var_text2, "")

        self._apply_customize()

    # ── Image processing ──────────────────────────────────────────────────────
    def _apply_customize(self):
        src = self.cropped_image or self.removed_image or self.orig_image
        if not src:
            return

        # 1. Resize to target passport size
        tw, th = PASSPORT_SIZES.get(self.var_photo_size.get(), (413, 531))
        sw, sh = src.size
        sc     = max(tw / sw, th / sh)
        scaled = src.resize((int(sw * sc), int(sh * sc)),
                            Image.Resampling.LANCZOS)
        nw, nh = scaled.size
        img = scaled.crop(((nw - tw) // 2, (nh - th) // 2,
                           (nw - tw) // 2 + tw, (nh - th) // 2 + th))

        # 2. Background color
        bg_hex = BG_COLORS.get(self.var_bg_color.get())
        if bg_hex:
            bg = Image.new("RGBA", img.size, bg_hex)
            bg.paste(img, mask=img)
            img = bg.convert("RGBA")

        # 3. Text overlay
        draw    = ImageDraw.Draw(img)
        txt_hex = TEXT_COLORS.get(self.var_text_color.get(), "#000000")
        tbg_hex = TEXT_BG_COLORS.get(self.var_text_bg_color.get())
        fsz     = max(12, tw // 18)
        fnt     = None
        for fn in ["arial.ttf", "Arial.ttf",
                   "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]:
            try:
                fnt = ImageFont.truetype(fn, fsz)
                break
            except Exception:
                pass
        if not fnt:
            fnt = ImageFont.load_default()

        lines = [self.var_text1.get(), self.var_text2.get()]
        lines = [l for l in lines
                 if l.strip() and l != "e.g. Name (leave blank to skip)"]
        y_cur = th - 6
        for line in reversed(lines):
            bbox = draw.textbbox((0, 0), line, font=fnt)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            tx = (tw - lw) // 2
            y_cur -= (lh + 4)
            if tbg_hex:
                draw.rectangle([tx-4, y_cur-2, tx+lw+4, y_cur+lh+2],
                               fill=tbg_hex)
            draw.text((tx+1, y_cur+1), line, font=fnt, fill="#00000055")
            draw.text((tx,   y_cur),   line, font=fnt, fill=txt_hex)

        self.final_image = img
        self.root.after(0, self._render_preview)

    def _render_preview(self):
        if not hasattr(self, "preview_canvas"):
            return
        c = self.preview_canvas
        if not c.winfo_exists():
            return
        try:
            cw = c.winfo_width()  or 600
            ch = c.winfo_height() or 500
            c.delete("all")
        except tk.TclError:
            return

        # Checkerboard background
        sq = 14
        for row in range(0, ch, sq):
            for col in range(0, cw, sq):
                f = "#c8c8c8" if (row // sq + col // sq) % 2 else "#b8b8b8"
                c.create_rectangle(col, row, col+sq, row+sq,
                                   fill=f, outline="")

        img = self.final_image
        if not img:
            c.create_text(cw // 2, ch // 2, text="Processing…",
                          fill="#888", font=("Courier New", 12))
            return

        iw, ih = img.size
        scale  = min(cw / iw, ch / ih, 1.0)
        dw, dh = max(1, int(iw * scale)), max(1, int(ih * scale))
        ox, oy = (cw - dw) // 2, (ch - dh) // 2

        method = (Image.Resampling.LANCZOS
                  if scale < 0.95 else Image.Resampling.NEAREST)
        disp = img.resize((dw, dh), method)
        self._prev_tk = ImageTk.PhotoImage(disp)
        c.create_image(ox, oy, anchor="nw", image=self._prev_tk)

    # ── Save single photo ─────────────────────────────────────────────────────
    def _save_single_photo(self):
        from tkinter import filedialog, messagebox
        import os
        if not self.final_image:
            messagebox.showwarning("No Photo", "Apply customization first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG file", "*.png"), ("JPEG file", "*.jpg")])
        if not path:
            return
        fmt = "JPEG" if path.lower().endswith(".jpg") else "PNG"
        img = self.final_image.convert("RGB") if fmt == "JPEG" else self.final_image
        img.save(path, fmt, dpi=(300, 300))
        messagebox.showinfo("Saved", f"Photo saved:\n{path}")
        self._set_status(f"💾 Saved: {os.path.basename(path)}")