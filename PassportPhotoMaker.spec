# PassportPhotoMaker.spec
# PyInstaller spec — mirrors your original command exactly:
#   pyinstaller --onedir --windowed --icon=icon.ico
#               --copy-metadata pymatting --copy-metadata rembg
#               --name "Ravi Instant Photo" bg_remover.py

block_cipher = None

from PyInstaller.utils.hooks import copy_metadata

a = Analysis(
    ['bg_remover.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # CRITICAL: same as --copy-metadata in your original command
        # Without these, rembg fails with importlib.metadata errors at runtime
        *copy_metadata('rembg'),
        *copy_metadata('pymatting'),
        # Bundle rembg model if already cached (optional, speeds up first run)
        ('C:/Users/ravic/.u2net/u2net.onnx', 'u2net'),
      (r'C:\RAVI\My App\greenbg\.venv\Lib\site-packages\tkinterdnd2', 'tkinterdnd2'),

    ],
    hiddenimports=[
        'pikepdf',
        'pypdf',
        'tkinterdnd2', 
        'rembg',
        'rembg.sessions',
        'rembg.sessions.u2net',
        'onnxruntime',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'cv2',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Ravi Instant Photo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Ravi Instant Photo',
)
