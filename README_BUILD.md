# Passport Photo Maker — Installer Build Guide

## What you'll get

Running the build produces a **`PassportPhotoMaker_Setup.exe`** that:
- Shows a proper install wizard (Welcome → License → Folder → Progress → Finish)
- Displays a **real-time progress bar** as files are copied
- Creates a **Desktop shortcut** automatically
- Creates a **Start Menu folder** with app + uninstall link
- Appears in **Add / Remove Programs** with version, publisher, size
- Optionally **downloads the AI model** (~170 MB) during install so the app opens instantly

---

## Prerequisites

| Tool | Download | Why needed |
|------|----------|------------|
| Python 3.10+ | https://python.org | Runs your app |
| NSIS 3.x | https://nsis.sourceforge.io/Download | Builds the installer |
| inetc NSIS plugin | https://nsis.sourceforge.io/Inetc_plug-in | Progress bar for model download |

> **NSIS install tip:** During NSIS setup, tick "inetc" under plugins if offered,  
> or download the plugin ZIP and drop `inetc.dll` into `C:\Program Files (x86)\NSIS\Plugins\x86-ansi\`

---

## Project folder layout (before building)

```
your-project/

├── app_icon.ico               ← your app icon (make one at https://convertico.com)

```

---

## How to build

### Option A — One click
Double-click **`BUILD.bat`**. It will:
1. Install PyInstaller via pip
2. Bundle your Python app into `dist\PassportPhotoMaker\`
3. Run NSIS to produce `PassportPhotoMaker_Setup.exe`

### Option B — Manual steps

```bat
:: Step 1: Bundle the Python app
pip install pyinstaller
pyinstaller PassportPhotoMaker.spec --noconfirm --clean

:: Step 2: Build the installer
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
```

---

## Customising the installer

### Change app name / version
Edit the `!define` lines at the top of `installer.nsi`:
```nsis
!define APP_NAME    "Passport Photo Maker"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "Your Name"
```

### Add your own icon
1. Create a `.ico` file (free: https://convertico.com or https://icoconvert.com)
2. Name it `app_icon.ico` and place it in the project folder
3. The spec and NSI files already reference this name

### Add a sidebar banner image
Create a 164×314 px BMP file named `wizard_banner.bmp`.  
It appears on the left side of the Welcome and Finish pages.

### Skip the AI model download step
If you want users to download the model on first launch instead (simpler but slower first run),
comment out the `SecModel` section in `installer.nsi`:
```nsis
; Section "Download AI Model..." SecModel
;     ...
; SectionEnd
```

### Bundle the model into the installer
If you already have the model at `C:\Users\YOU\.u2net\u2net.onnx`, add it to the spec:
```python
datas=[
    (r'C:\Users\YOU\.u2net\u2net.onnx', 'u2net'),
],
```
This makes the installer larger (~170 MB extra) but the app works offline immediately.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `pyinstaller` not found | Run `pip install pyinstaller` first |
| App crashes after install | Run from cmd: `dist\PassportPhotoMaker\PassportPhotoMaker.exe` to see the error |
| Missing DLL errors | Add the DLL name to `hiddenimports` in the `.spec` file |
| NSIS "inetc not found" | Install the inetc plugin (see Prerequisites above) |
| Icon not showing | Make sure `app_icon.ico` is in the same folder as the spec/nsi files |
| Antivirus flags the exe | This is common for PyInstaller apps — submit to VirusTotal and whitelist |

---

## File sizes to expect

| File | Approx size |
|------|-------------|
| `dist\PassportPhotoMaker\` folder | ~80–120 MB |
| `PassportPhotoMaker_Setup.exe` (without model) | ~45–70 MB |
| `PassportPhotoMaker_Setup.exe` (with model bundled) | ~210–240 MB |
