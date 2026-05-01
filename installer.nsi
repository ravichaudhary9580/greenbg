; ============================================================
;  Ravi Instant Photo — NSIS Installer Script
;  Requires: NSIS 3.x  (https://nsis.sourceforge.io/)
;  Build:    makensis installer.nsi
; ============================================================

!define APP_NAME        "Ravi Instant Photo"
!define APP_VERSION     "1.0.0"
!define APP_PUBLISHER   "Ravi Chaudhary"
!define APP_URL         "https://ravichaudhary9580.github.io/Portfolio-New/"
!define APP_EXE         "Ravi Instant Photo.exe"
!define INSTALL_DIR     "$PROGRAMFILES64\RaviInstantPhoto"
!define UNINSTALL_KEY   "Software\Microsoft\Windows\CurrentVersion\Uninstall\RaviInstantPhoto"

; ── Modern UI ────────────────────────────────────────────────
!include "MUI2.nsh"
!include "LogicLib.nsh"

Name            "${APP_NAME}"
OutFile         "RaviInstantPhoto_Setup.exe"
InstallDir      "${INSTALL_DIR}"
InstallDirRegKey HKLM "${UNINSTALL_KEY}" "InstallLocation"
RequestExecutionLevel admin
BrandingText    "${APP_NAME} v${APP_VERSION}"

; ── MUI Settings ─────────────────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_ICON                    "icon.ico"
!define MUI_UNICON                  "icon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "wizard_banner.bmp"   ; 164x314 px BMP (optional)

; Header colours (hex, no #)
!define MUI_BGCOLOR                 "FFFFFF"
!define MUI_HEADERTEXTCOLOR         "1a1a1a"

; Welcome page text
!define MUI_WELCOMEPAGE_TITLE       "Welcome to ${APP_NAME} Setup"
!define MUI_WELCOMEPAGE_TEXT        "This wizard will install ${APP_NAME} ${APP_VERSION} on your computer.$\r$\n$\r$\nThe app lets you remove backgrounds, crop, customise and print passport photos at 300 DPI — right from your desktop.$\r$\n$\r$\nClick Next to continue."

; Finish page — launch app checkbox
!define MUI_FINISHPAGE_RUN          "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT     "Launch Ravi Instant Photo now"
!define MUI_FINISHPAGE_LINK         "Visit our website"
!define MUI_FINISHPAGE_LINK_LOCATION "${APP_URL}"

; ── Pages ────────────────────────────────────────────────────
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE        "LICENSE.txt"      ; remove line if no license file
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES      ; <-- the progress bar page
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Language (must come after pages)
!insertmacro MUI_LANGUAGE "English"

; ── Version info shown in Properties dialog ───────────────────
VIProductVersion                    "${APP_VERSION}.0"
VIAddVersionKey "ProductName"       "${APP_NAME}"
VIAddVersionKey "CompanyName"       "${APP_PUBLISHER}"
VIAddVersionKey "FileDescription"   "${APP_NAME} Installer"
VIAddVersionKey "FileVersion"       "${APP_VERSION}"
VIAddVersionKey "ProductVersion"    "${APP_VERSION}"
VIAddVersionKey "LegalCopyright"    "© 2025 ${APP_PUBLISHER}"

; ============================================================
;  INSTALLER SECTIONS
; ============================================================

Section "Main Application" SecMain
    SectionIn RO   ; required — cannot be deselected

    SetOutPath "$INSTDIR"
    SetOverwrite on

    ; ── Copy all files from the PyInstaller dist folder ──────
    ; The dist\RaviInstantPhoto\ folder is produced by PyInstaller
    File /r "dist\Ravi Instant Photo\*.*"

    ; ── Write uninstall registry keys ────────────────────────
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayName"      "${APP_NAME}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayVersion"   "${APP_VERSION}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "Publisher"        "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "URLInfoAbout"     "${APP_URL}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "InstallLocation"  "$INSTDIR"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "UninstallString"  '"$INSTDIR\Uninstall.exe"'
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify"         1
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair"         1

    ; Estimate installed size for Add/Remove Programs (KB)
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "EstimatedSize"    102400

    ; ── Create uninstaller ───────────────────────────────────
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; ── Copy icon separately so shortcut can reference it ────────
    File "icon.ico"

    ; ── Desktop shortcut ─────────────────────────────────────────
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\icon.ico" 0 SW_SHOWNORMAL "" "${APP_NAME}"

  ; ── Start Menu shortcuts ─────────────────────────────────────
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\icon.ico" 0 SW_SHOWNORMAL "" "${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

SectionEnd

; NOTE: AI model (~170 MB) is downloaded automatically by the app on first launch.
; No extra plugin needed — rembg handles this itself.

; ============================================================
;  UNINSTALLER
; ============================================================

Section "Uninstall"
    ; Remove all installed files
    RMDir /r "$INSTDIR"

    ; Remove shortcuts
    Delete "$DESKTOP\${APP_NAME}.lnk"
    RMDir /r "$SMPROGRAMS\${APP_NAME}"

    ; Remove registry keys
    DeleteRegKey HKLM "${UNINSTALL_KEY}"

    MessageBox MB_ICONINFORMATION|MB_OK \
        "${APP_NAME} has been uninstalled.$\nYour saved photos are not affected."
SectionEnd

; ============================================================
;  HELPER: show detailed file-copy progress in the log
; ============================================================
!macro DetailFile SRC DEST
    DetailPrint "Installing: ${DEST}"
    File "${SRC}"
!macroend
