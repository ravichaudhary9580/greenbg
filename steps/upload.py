"""
steps/upload.py
Step 1 — Upload
Handles the drag-and-drop zone, file browse, camera capture,
and background-removal thread kickoff.
"""
import tkinter as tk
from tkinter import filedialog, messagebox
import typing
from PIL import Image, ImageTk
import cv2

from constants import (
    C_BG, C_WHITE, C_DARK, C_MUTED, C_BORDER, C_TEXT, C_ACCENT
)


class UploadStep:
    """Mixin — mixed into PassportApp. Uses self.* state from the app."""

    if typing.TYPE_CHECKING:
        content: tk.Frame
        root: tk.Tk
        STEP_CROP: int
        cx1: int
        cy1: int
        cx2: int
        cy2: int
        orig_image: typing.Any
        removed_image: typing.Any
        removal_done: bool
        cropped_image: typing.Any
        final_image: typing.Any
        def _set_footer(self, btns: list) -> None: ...
        def _set_status(self, msg: str) -> None: ...
        def _show_step(self, step: int) -> None: ...
        def _start_bg_removal(self) -> None: ...

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_upload(self):
        self._set_footer([])  # no footer buttons on upload step

        # drop zone
        zone = tk.Frame(self.content, bg=C_WHITE,
                        highlightbackground=C_BORDER,
                        highlightthickness=2, relief="flat")
        zone.pack(fill=tk.X, padx=28, pady=(16, 10))
        inner = tk.Frame(zone, bg=C_WHITE)
        inner.pack(pady=52)

        tk.Label(inner, text="Drop your photo here",
                 bg=C_WHITE, fg=C_TEXT,
                 font=("Georgia", 15, "bold")).pack()
        tk.Label(inner, text="or click to browse",
                 bg=C_WHITE, fg=C_MUTED,
                 font=("Courier New", 10)).pack(pady=4)
        tk.Label(inner, text="PNG  ·  JPG  ·  WEBP  ·  up to 10MB",
                 bg=C_WHITE, fg=C_MUTED,
                 font=("Courier New", 9)).pack()
        tk.Button(inner, text="  Browse File  ",
                  command=self._upload_image,
                  bg=C_WHITE, fg=C_DARK,
                  font=("Courier New", 10),
                  relief="solid", bd=1, padx=14, pady=6,
                  cursor="hand2", activebackground=C_BG
                  ).pack(pady=(18, 0))

        for w in [zone, inner]:
            w.bind("<Button-1>", lambda e: self._upload_image())

        zone.drop_target_register('DND_Files')   # type: ignore
        zone.dnd_bind('<<Drop>>', self._on_drop)  # type: ignore

        # camera / tools row
        brow = tk.Frame(self.content, bg=C_BG)
        brow.pack(pady=6)
        from file_compressor import open_compressor
        for label, cmd in [
            ("◆  Web Camera",        self._open_camera),
            ("⧉  File Size Manager", lambda: open_compressor(self.root)),
        ]:
            tk.Button(brow, text=label, command=cmd,
                      bg=C_WHITE, fg=C_DARK,
                      font=("Courier New", 9),
                      relief="solid", bd=1,
                      padx=14, pady=7, cursor="hand2",
                      activebackground=C_BG
                      ).pack(side=tk.LEFT, padx=6)

    # ── File load helpers ─────────────────────────────────────────────────────
    def _upload_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files",
                        "*.png *.jpg *.jpeg *.bmp *.webp *.tiff")])
        if not path:
            return
        self._load_image_from_path(path)

    def _on_drop(self, event):
        path = event.data.strip()
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        valid = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff")
        if not path.lower().endswith(valid):
            messagebox.showwarning(
                "Invalid File",
                "Please drop an image file (PNG, JPG, WEBP, etc.)")
            return
        self._load_image_from_path(path)

    def _load_image_from_path(self, path):
        try:
            self.orig_image = Image.open(path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open image:\n{e}")
            return
        self.removed_image = None
        self.removal_done  = False
        self.cropped_image = None
        self.final_image   = None
        self._set_status("Photo loaded — removing background…")
        self._show_step(self.STEP_CROP)
        self._start_bg_removal()

    # ── Camera ────────────────────────────────────────────────────────────────
    def _open_camera(self):
        cam_win = tk.Toplevel(self.root)
        cam_win.title("Take Photo")
        cam_win.geometry("700x580")
        cam_win.configure(bg=C_BG)
        cam_win.resizable(False, False)

        tk.Label(cam_win, text="CAMERA",
                 bg=C_BG, fg=C_MUTED,
                 font=("Courier New", 8, "bold")).pack(pady=(14, 4))

        canvas = tk.Canvas(cam_win, width=640, height=480,
                           bg=C_DARK, highlightthickness=0)
        canvas.pack()

        btn_row = tk.Frame(cam_win, bg=C_BG)
        btn_row.pack(pady=12)

        captured: typing.Dict[str, typing.Any] = {"img": None}
        running       = {"on": True}
        tk_frame_ref: typing.Dict[str, typing.Any] = {"ref": None}

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Camera Error",
                                 "No camera found.\n"
                                 "Please check your camera connection.")
            cam_win.destroy()
            return

        def update_frame():
            if not running["on"]:
                return
            ret, frame = cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img.thumbnail((640, 480))
                tk_img = ImageTk.PhotoImage(img)
                canvas.create_image(320, 240, anchor="center", image=tk_img)
                tk_frame_ref["ref"] = tk_img
                captured["img"]     = frame_rgb
            cam_win.after(30, update_frame)

        def take_photo():
            if captured["img"] is None:
                return
            running["on"] = False
            cap.release()
            self.orig_image    = Image.fromarray(captured["img"]).convert("RGBA")
            self.removed_image = None
            self.removal_done  = False
            self.cropped_image = None
            self.final_image   = None
            self.cx1 = self.cy1 = self.cx2 = self.cy2 = 0
            cam_win.destroy()
            self._set_status("Photo captured — removing background…")
            self._show_step(self.STEP_CROP)
            self._start_bg_removal()

        def on_close():
            running["on"] = False
            cap.release()
            cam_win.destroy()

        cam_win.protocol("WM_DELETE_WINDOW", on_close)

        tk.Button(btn_row, text="📷  Take Photo",
                  command=take_photo,
                  bg=C_DARK, fg=C_WHITE,
                  font=("Courier New", 10, "bold"),
                  relief="flat", padx=18, pady=8,
                  cursor="hand2", activebackground="#333"
                  ).pack(side=tk.LEFT, padx=8)

        tk.Button(btn_row, text="✕  Cancel",
                  command=on_close,
                  bg=C_WHITE, fg=C_DARK,
                  font=("Courier New", 10),
                  relief="solid", bd=1,
                  padx=14, pady=7,
                  cursor="hand2", activebackground=C_BG
                  ).pack(side=tk.LEFT, padx=8)

        update_frame()
