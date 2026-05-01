"""
file_compressor.py
File Size Manager — compress or resize images and PDFs
Linked to bg_remover.py via: from file_compressor import open_compressor
Works fully offline when bundled with PyInstaller.

Libraries used (all offline):
  - Pillow   : image compress/resize/convert
  - pypdf    : PDF compress (remove duplication, rewrite)
  - pikepdf  : better PDF compression (optional fallback to pypdf)
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import threading
import os

# ── same palette as bg_remover.py ────────────────────────────
C_BG     = "#eae8e1"
C_WHITE  = "#ffffff"
C_CARD   = "#ffffff"
C_DARK   = "#1a1a1a"
C_MUTED  = "#9a9890"
C_ACCENT = "#2a7a5a"
C_BORDER = "#d0cdc5"
C_TEXT   = "#1a1a1a"
C_ERR    = "#cc3333"
C_GREEN  = "#2a7a5a"

SUPPORTED_IMAGE = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]
SUPPORTED_PDF   = [".pdf"]
SUPPORTED_ALL   = SUPPORTED_IMAGE + SUPPORTED_PDF


# ─────────────────────────────────────────────────────────────
def open_compressor(parent=None):
    """Call this from bg_remover.py to open the compressor window."""
    win = FileCompressorWindow(parent)
    return win


# ─────────────────────────────────────────────────────────────
class FileCompressorWindow:
    def __init__(self, parent=None):
        self.win = tk.Toplevel(parent) if parent else tk.Tk()
        self.win.title("File Size Manager")
        self.win.geometry("640x700")
        self.win.minsize(560, 600)
        self.win.resizable(True, True)
        self.win.configure(bg=C_BG)

        self.input_path  = tk.StringVar()
        self.output_path = tk.StringVar()
        self.mode        = tk.StringVar(value="compress")   # compress / resize
        self.quality     = tk.IntVar(value=75)
        self.out_format  = tk.StringVar(value="Same as input")
        self.resize_pct  = tk.IntVar(value=70)
        self.resize_w    = tk.StringVar(value="")
        self.resize_h    = tk.StringVar(value="")
        self.resize_mode = tk.StringVar(value="percentage") # percentage / pixels
        self.status_text = tk.StringVar(value="Select a file to get started.")
        self.file_type   = None   # "image" or "pdf"

        self._build_ui()

    # ── UI ────────────────────────────────────────────────────
    def _build_ui(self):
        # title bar
        hdr = tk.Frame(self.win, bg=C_DARK, height=52)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="File Size Manager",
                 bg=C_DARK, fg=C_WHITE,
                 font=("Georgia", 14, "bold")).pack(side=tk.LEFT, padx=20, pady=14)
        tk.Label(hdr, text="compress · resize · convert",
                 bg=C_DARK, fg=C_MUTED,
                 font=("Courier New", 9)).pack(side=tk.RIGHT, padx=20)

        scroll_canvas = tk.Canvas(self.win, bg=C_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.win, orient="vertical",
                                  command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.pack(fill=tk.BOTH, expand=True)

        self.body = tk.Frame(scroll_canvas, bg=C_BG)
        self.body_id = scroll_canvas.create_window((0, 0), window=self.body,
                                                   anchor="nw")

        def _on_configure(e):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
            scroll_canvas.itemconfig(self.body_id, width=scroll_canvas.winfo_width())

        self.body.bind("<Configure>", _on_configure)
        scroll_canvas.bind("<Configure>", _on_configure)
        scroll_canvas.bind_all("<MouseWheel>",
            lambda e: scroll_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._build_input_section()
        self._build_mode_section()
        self._build_quality_section()
        self._build_resize_section()
        self._build_format_section()
        self._build_output_section()
        self._build_action_section()

    def _card(self, title):
        """Returns a card frame with a label."""
        outer = tk.Frame(self.body, bg=C_BG)
        outer.pack(fill=tk.X, padx=20, pady=(10, 0))
        tk.Label(outer, text=title.upper(),
                 bg=C_BG, fg=C_MUTED,
                 font=("Courier New", 8, "bold")).pack(anchor="w", pady=(0, 4))
        card = tk.Frame(outer, bg=C_WHITE,
                        highlightbackground=C_BORDER,
                        highlightthickness=1)
        card.pack(fill=tk.X)
        return card

    # ── Input file ────────────────────────────────────────────
    def _build_input_section(self):
        card = self._card("Input File")
        row = tk.Frame(card, bg=C_WHITE)
        row.pack(fill=tk.X, padx=14, pady=14)

        entry = tk.Entry(row, textvariable=self.input_path,
                         bg=C_BG, fg=C_TEXT,
                         font=("Courier New", 9),
                         relief="solid", bd=1)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)

        tk.Button(row, text="  Browse  ",
                  command=self._browse_input,
                  bg=C_WHITE, fg=C_DARK,
                  font=("Courier New", 9),
                  relief="solid", bd=1,
                  padx=10, pady=4, cursor="hand2",
                  activebackground=C_BG
                  ).pack(side=tk.LEFT, padx=(8, 0))

        self.file_info_label = tk.Label(card,
                                        text="Supported: JPG, PNG, WEBP, BMP, TIFF, PDF",
                                        bg=C_WHITE, fg=C_MUTED,
                                        font=("Courier New", 8))
        self.file_info_label.pack(anchor="w", padx=14, pady=(0, 10))

    # ── Mode ─────────────────────────────────────────────────
    def _build_mode_section(self):
        card = self._card("Mode")
        row = tk.Frame(card, bg=C_WHITE)
        row.pack(fill=tk.X, padx=14, pady=12)

        for text, val in [("Compress (reduce quality)", "compress"),
                          ("Resize (change dimensions)", "resize"),
                          ("Both (resize then compress)", "both")]:
            tk.Radiobutton(row, text=text, variable=self.mode, value=val,
                           bg=C_WHITE, fg=C_TEXT,
                           font=("Courier New", 9),
                           activebackground=C_WHITE,
                           selectcolor=C_WHITE,
                           command=self._on_mode_change
                           ).pack(anchor="w", pady=2)

    # ── Quality slider ────────────────────────────────────────
    def _build_quality_section(self):
        self.quality_card_outer = tk.Frame(self.body, bg=C_BG)
        self.quality_card_outer.pack(fill=tk.X, padx=20, pady=(10, 0))
        tk.Label(self.quality_card_outer, text="QUALITY / COMPRESSION",
                 bg=C_BG, fg=C_MUTED,
                 font=("Courier New", 8, "bold")).pack(anchor="w", pady=(0, 4))
        card = tk.Frame(self.quality_card_outer, bg=C_WHITE,
                        highlightbackground=C_BORDER,
                        highlightthickness=1)
        card.pack(fill=tk.X)

        top = tk.Frame(card, bg=C_WHITE)
        top.pack(fill=tk.X, padx=14, pady=(12, 4))

        tk.Label(top, text="Lower = smaller file, less quality",
                 bg=C_WHITE, fg=C_MUTED,
                 font=("Courier New", 8)).pack(side=tk.LEFT)

        self.quality_val_label = tk.Label(top, text="75%",
                                          bg=C_WHITE, fg=C_ACCENT,
                                          font=("Courier New", 10, "bold"))
        self.quality_val_label.pack(side=tk.RIGHT)

        self.quality_slider = tk.Scale(card, from_=5, to=99,
                                       orient=tk.HORIZONTAL,
                                       variable=self.quality,
                                       bg=C_WHITE, fg=C_TEXT,
                                       troughcolor=C_BG,
                                       highlightthickness=0,
                                       showvalue=False,
                                       command=self._on_quality_change)
        self.quality_slider.pack(fill=tk.X, padx=14, pady=(0, 6))

        hint = tk.Frame(card, bg=C_WHITE)
        hint.pack(fill=tk.X, padx=14, pady=(0, 12))
        for txt, anchor in [("← Smallest", "w"), ("Best →", "e")]:
            tk.Label(hint, text=txt, bg=C_WHITE, fg=C_MUTED,
                     font=("Courier New", 8)).pack(side=tk.LEFT if "w" in anchor else tk.RIGHT)

    # ── Resize options ────────────────────────────────────────
    def _build_resize_section(self):
        self.resize_card_outer = tk.Frame(self.body, bg=C_BG)
        self.resize_card_outer.pack(fill=tk.X, padx=20, pady=(10, 0))
        tk.Label(self.resize_card_outer, text="RESIZE OPTIONS",
                 bg=C_BG, fg=C_MUTED,
                 font=("Courier New", 8, "bold")).pack(anchor="w", pady=(0, 4))
        card = tk.Frame(self.resize_card_outer, bg=C_WHITE,
                        highlightbackground=C_BORDER,
                        highlightthickness=1)
        card.pack(fill=tk.X)

        # percentage / pixels toggle
        mode_row = tk.Frame(card, bg=C_WHITE)
        mode_row.pack(fill=tk.X, padx=14, pady=(12, 6))
        tk.Label(mode_row, text="Resize by:",
                 bg=C_WHITE, fg=C_TEXT,
                 font=("Courier New", 9)).pack(side=tk.LEFT)
        for txt, val in [("  Percentage", "percentage"), ("  Pixels", "pixels")]:
            tk.Radiobutton(mode_row, text=txt,
                           variable=self.resize_mode, value=val,
                           bg=C_WHITE, fg=C_TEXT,
                           font=("Courier New", 9),
                           activebackground=C_WHITE,
                           selectcolor=C_WHITE,
                           command=self._on_resize_mode_change
                           ).pack(side=tk.LEFT)

        # percentage slider
        self.pct_frame = tk.Frame(card, bg=C_WHITE)
        self.pct_frame.pack(fill=tk.X, padx=14, pady=(0, 4))
        pct_top = tk.Frame(self.pct_frame, bg=C_WHITE)
        pct_top.pack(fill=tk.X)
        tk.Label(pct_top, text="Scale to % of original:",
                 bg=C_WHITE, fg=C_MUTED,
                 font=("Courier New", 8)).pack(side=tk.LEFT)
        self.pct_val_label = tk.Label(pct_top, text="70%",
                                      bg=C_WHITE, fg=C_ACCENT,
                                      font=("Courier New", 10, "bold"))
        self.pct_val_label.pack(side=tk.RIGHT)
        tk.Scale(self.pct_frame, from_=5, to=200,
                 orient=tk.HORIZONTAL,
                 variable=self.resize_pct,
                 bg=C_WHITE, fg=C_TEXT,
                 troughcolor=C_BG,
                 highlightthickness=0,
                 showvalue=False,
                 command=self._on_pct_change
                 ).pack(fill=tk.X)

        # pixel inputs
        self.px_frame = tk.Frame(card, bg=C_WHITE)
        self.px_frame.pack(fill=tk.X, padx=14, pady=(0, 12))
        tk.Label(self.px_frame, text="Width (px):",
                 bg=C_WHITE, fg=C_TEXT,
                 font=("Courier New", 9)).pack(side=tk.LEFT)
        tk.Entry(self.px_frame, textvariable=self.resize_w,
                 width=7, font=("Courier New", 9),
                 bg=C_BG, relief="solid", bd=1
                 ).pack(side=tk.LEFT, padx=(4, 16), ipady=4)
        tk.Label(self.px_frame, text="Height (px):",
                 bg=C_WHITE, fg=C_TEXT,
                 font=("Courier New", 9)).pack(side=tk.LEFT)
        tk.Entry(self.px_frame, textvariable=self.resize_h,
                 width=7, font=("Courier New", 9),
                 bg=C_BG, relief="solid", bd=1
                 ).pack(side=tk.LEFT, padx=4, ipady=4)
        tk.Label(self.px_frame,
                 text="(leave one blank to keep aspect ratio)",
                 bg=C_WHITE, fg=C_MUTED,
                 font=("Courier New", 8)).pack(side=tk.LEFT, padx=8)

        self.px_frame.pack_forget()   # hidden by default (percentage mode)
        self._update_resize_section_visibility()

    # ── Output format ─────────────────────────────────────────
    def _build_format_section(self):
        self.format_card_outer = tk.Frame(self.body, bg=C_BG)
        self.format_card_outer.pack(fill=tk.X, padx=20, pady=(10, 0))
        tk.Label(self.format_card_outer, text="OUTPUT FORMAT",
                 bg=C_BG, fg=C_MUTED,
                 font=("Courier New", 8, "bold")).pack(anchor="w", pady=(0, 4))
        card = tk.Frame(self.format_card_outer, bg=C_WHITE,
                        highlightbackground=C_BORDER,
                        highlightthickness=1)
        card.pack(fill=tk.X)

        row = tk.Frame(card, bg=C_WHITE)
        row.pack(fill=tk.X, padx=14, pady=12)
        tk.Label(row, text="Save as:",
                 bg=C_WHITE, fg=C_TEXT,
                 font=("Courier New", 9)).pack(side=tk.LEFT)

        self.format_menu = ttk.Combobox(row,
                                        textvariable=self.out_format,
                                        state="readonly",
                                        font=("Courier New", 9),
                                        width=18)
        self.format_menu['values'] = ["Same as input",
                                      "JPG", "PNG", "WEBP", "PDF"]
        self.format_menu.pack(side=tk.LEFT, padx=10)

    # ── Output path ───────────────────────────────────────────
    def _build_output_section(self):
        card = self._card("Output File")
        row = tk.Frame(card, bg=C_WHITE)
        row.pack(fill=tk.X, padx=14, pady=14)

        entry = tk.Entry(row, textvariable=self.output_path,
                         bg=C_BG, fg=C_TEXT,
                         font=("Courier New", 9),
                         relief="solid", bd=1)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)

        tk.Button(row, text="  Choose  ",
                  command=self._browse_output,
                  bg=C_WHITE, fg=C_DARK,
                  font=("Courier New", 9),
                  relief="solid", bd=1,
                  padx=10, pady=4, cursor="hand2",
                  activebackground=C_BG
                  ).pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(card,
                 text="Leave blank to auto-name (saves next to input file)",
                 bg=C_WHITE, fg=C_MUTED,
                 font=("Courier New", 8)).pack(anchor="w", padx=14, pady=(0, 10))

    # ── Action button + status ────────────────────────────────
    def _build_action_section(self):
        outer = tk.Frame(self.body, bg=C_BG)
        outer.pack(fill=tk.X, padx=20, pady=16)

        self.run_btn = tk.Button(outer,
                                 text="  ▶  Process File  ",
                                 command=self._run,
                                 bg=C_ACCENT, fg=C_WHITE,
                                 font=("Georgia", 11, "bold"),
                                 relief="flat", bd=0,
                                 padx=22, pady=10,
                                 cursor="hand2",
                                 activebackground="#1f5e44",
                                 activeforeground=C_WHITE)
        self.run_btn.pack(fill=tk.X)

        self.status_label = tk.Label(outer,
                                     textvariable=self.status_text,
                                     bg=C_BG, fg=C_MUTED,
                                     font=("Courier New", 9),
                                     wraplength=560)
        self.status_label.pack(pady=(10, 4))

        self.progress = ttk.Progressbar(outer, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(4, 0))
        self.progress.pack_forget()

    # ── Callbacks ─────────────────────────────────────────────
    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Select a file",
            filetypes=[
                ("All supported", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.pdf"),
                ("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff"),
                ("PDF", "*.pdf"),
            ])
        if not path:
            return
        self.input_path.set(path)
        self.output_path.set("")  # clear old output

        ext = os.path.splitext(path)[1].lower()
        if ext in SUPPORTED_IMAGE:
            self.file_type = "image"
            try:
                img = Image.open(path)
                size_kb = os.path.getsize(path) / 1024
                self.file_info_label.config(
                    text=f"{img.width}×{img.height}px  ·  "
                         f"{size_kb:.1f} KB  ·  {ext.upper().strip('.')}",
                    fg=C_TEXT)
            except Exception:
                self.file_info_label.config(text="Image file selected.", fg=C_TEXT)
            self.format_menu['values'] = ["Same as input", "JPG", "PNG", "WEBP"]
            self.out_format.set("Same as input")
            self._update_resize_section_visibility()

        elif ext == ".pdf":
            self.file_type = "pdf"
            size_kb = os.path.getsize(path) / 1024
            self.file_info_label.config(
                text=f"PDF  ·  {size_kb:.1f} KB", fg=C_TEXT)
            self.format_menu['values'] = ["Same as input (PDF)"]
            self.out_format.set("Same as input (PDF)")
            # PDF: only compress makes sense
            self.mode.set("compress")
            self._on_mode_change()
        else:
            self.file_type = None
            self.file_info_label.config(
                text="Unsupported file type.", fg=C_ERR)

        self.status_text.set("File loaded. Choose options and click Process.")

    def _browse_output(self):
        ext = self._get_output_ext()
        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(ext.upper().strip(".") + " file", f"*{ext}")])
        if path:
            self.output_path.set(path)

    def _on_quality_change(self, val):
        self.quality_val_label.config(text=f"{val}%")

    def _on_pct_change(self, val):
        self.pct_val_label.config(text=f"{val}%")

    def _on_mode_change(self):
        self._update_resize_section_visibility()

    def _on_resize_mode_change(self):
        if self.resize_mode.get() == "percentage":
            self.px_frame.pack_forget()
            self.pct_frame.pack(fill=tk.X, padx=14, pady=(0, 12))
        else:
            self.pct_frame.pack_forget()
            self.px_frame.pack(fill=tk.X, padx=14, pady=(0, 12))

    def _update_resize_section_visibility(self):
        mode = self.mode.get()
        show_quality = mode in ("compress", "both")
        show_resize  = mode in ("resize", "both")

        if self.file_type == "pdf":
            show_quality = True
            show_resize  = False

        if show_quality:
            self.quality_card_outer.pack(fill=tk.X, padx=20, pady=(10, 0))
        else:
            self.quality_card_outer.pack_forget()

        if show_resize:
            self.resize_card_outer.pack(fill=tk.X, padx=20, pady=(10, 0))
        else:
            self.resize_card_outer.pack_forget()

    # ── Processing ────────────────────────────────────────────
    def _get_output_ext(self):
        fmt = self.out_format.get()
        mapping = {"JPG": ".jpg", "PNG": ".png",
                   "WEBP": ".webp", "PDF": ".pdf"}
        if fmt in mapping:
            return mapping[fmt]
        # same as input
        if self.input_path.get():
            return os.path.splitext(self.input_path.get())[1].lower()
        return ".jpg"

    def _get_output_path(self):
        if self.output_path.get().strip():
            return self.output_path.get().strip()
        inp = self.input_path.get()
        base, ext = os.path.splitext(inp)
        out_ext = self._get_output_ext()
        return base + "_compressed" + out_ext

    def _run(self):
        if not self.input_path.get():
            messagebox.showwarning("No file", "Please select an input file first.")
            return
        if self.file_type is None:
            messagebox.showwarning("Unsupported", "Please select a supported file.")
            return
        self.run_btn.config(state=tk.DISABLED)
        self.progress.pack(fill=tk.X, pady=(4, 0))
        self.progress.start(10)
        self.status_text.set("Processing…")
        self.status_label.config(fg=C_MUTED)
        threading.Thread(target=self._process, daemon=True).start()

    def _process(self):
        try:
            if self.file_type == "image":
                result = self._process_image()
            else:
                result = self._process_pdf()
            self.win.after(0, self._done, result)
        except Exception as e:
            self.win.after(0, self._error, str(e))

    def _process_image(self):
        inp  = self.input_path.get()
        out  = self._get_output_path()
        mode = self.mode.get()
        img  = Image.open(inp)

        # ── Resize ─────────────────────────────────────────────
        if mode in ("resize", "both"):
            if self.resize_mode.get() == "percentage":
                pct = self.resize_pct.get() / 100
                new_w = max(1, int(img.width * pct))
                new_h = max(1, int(img.height * pct))
            else:
                w_str = self.resize_w.get().strip()
                h_str = self.resize_h.get().strip()
                if w_str and h_str:
                    new_w, new_h = int(w_str), int(h_str)
                elif w_str:
                    new_w = int(w_str)
                    new_h = int(img.height * (new_w / img.width))
                elif h_str:
                    new_h = int(h_str)
                    new_w = int(img.width * (new_h / img.height))
                else:
                    new_w, new_h = img.width, img.height
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # ── Format conversion ──────────────────────────────────
        out_ext = self._get_output_ext()
        if out_ext in (".jpg", ".jpeg"):
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(out, "JPEG", quality=self.quality.get(),
                     optimize=True, progressive=True)
        elif out_ext == ".png":
            # PNG compression: quality mapped to compress_level 0-9
            level = max(0, min(9, 9 - int(self.quality.get() / 11)))
            img.save(out, "PNG", optimize=True, compress_level=level)
        elif out_ext == ".webp":
            img.save(out, "WEBP", quality=self.quality.get(),
                     method=6)
        else:
            img.save(out, optimize=True)

        in_kb  = os.path.getsize(inp) / 1024
        out_kb = os.path.getsize(out) / 1024
        saved  = in_kb - out_kb
        pct    = (saved / in_kb * 100) if in_kb > 0 else 0
        return (out, in_kb, out_kb, saved, pct)

    def _process_pdf(self):
        inp = self.input_path.get()
        out = self._get_output_path()

        # Try pikepdf first (better compression), fall back to pypdf
        try:
            import pikepdf
            pdf = pikepdf.open(inp)
            pdf.save(out,
                     compress_streams=True,
                     recompress_flate=True,
                     object_stream_mode=pikepdf.ObjectStreamMode.generate)
            pdf.close()
        except ImportError:
            try:
                from pypdf import PdfWriter, PdfReader
                reader = PdfReader(inp)
                writer = PdfWriter()
                for page in reader.pages:
                    page.compress_content_streams()
                    writer.add_page(page)
                with open(out, "wb") as f:
                    writer.write(f)
            except ImportError:
                raise RuntimeError(
                    "No PDF library found.\n"
                    "Run: pip install pikepdf\n"
                    "or:  pip install pypdf")

        in_kb  = os.path.getsize(inp) / 1024
        out_kb = os.path.getsize(out) / 1024
        saved  = in_kb - out_kb
        pct    = (saved / in_kb * 100) if in_kb > 0 else 0
        return (out, in_kb, out_kb, saved, pct)

    def _done(self, result):
        out, in_kb, out_kb, saved, pct = result
        self.progress.stop()
        self.progress.pack_forget()
        self.run_btn.config(state=tk.NORMAL)

        if saved > 0:
            msg = (f"✔  Done!  {in_kb:.1f} KB  →  {out_kb:.1f} KB  "
                   f"(saved {saved:.1f} KB, {pct:.1f}% smaller)")
            color = C_GREEN
        else:
            msg = (f"✔  Done!  {in_kb:.1f} KB  →  {out_kb:.1f} KB  "
                   f"(file is {abs(saved):.1f} KB larger — "
                   f"try lower quality or smaller size)")
            color = C_MUTED

        self.status_text.set(msg)
        self.status_label.config(fg=color)

        answer = messagebox.askyesno("Done!",
                                     f"File saved:\n{out}\n\n"
                                     f"Open containing folder?")
        if answer:
            folder = os.path.dirname(os.path.abspath(out))
            os.startfile(folder)

    def _error(self, msg):
        self.progress.stop()
        self.progress.pack_forget()
        self.run_btn.config(state=tk.NORMAL)
        self.status_text.set(f"Error: {msg}")
        self.status_label.config(fg=C_ERR)
        messagebox.showerror("Error", msg)


# ── Standalone run (for testing) ─────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_compressor()
    root.mainloop()
