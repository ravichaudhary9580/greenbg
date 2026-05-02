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



## How to build

### click
Double-click **`BUILD.bat`**. It will:
1. Install PyInstaller via pip
2. Bundle your Python app into `dist\PassportPhotoMaker\`
3. Run NSIS to produce `PassportPhotoMaker_Setup.exe`


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
