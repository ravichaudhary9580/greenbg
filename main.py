"""
main.py
Entry point for Passport Photo Maker.
Run with:  python main.py
"""
import sys
import os

# ── PyInstaller frozen-app model path fix ─────────────────────────────────────
if getattr(sys, 'frozen', False):
    model_dir = os.path.join(getattr(sys, '_MEIPASS', ''), 'u2net')
    os.environ['U2NET_HOME'] = model_dir

from tkinterdnd2 import TkinterDnD
from app import PassportApp

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    PassportApp(root)
    root.mainloop()
