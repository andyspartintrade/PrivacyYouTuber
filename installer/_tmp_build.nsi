; Privacy YouTuber — NSIS installer (open source, zlib license).
;
; ΠΩΣ ΧΡΗΣΙΜΟΠΟΙΕΙΤΑΙ (αυτόματο — μην το τρέχεις χειροκίνητα):
;   1. Κάνε build το onedir:  python build_onedir.py
;   2. Τρέξε:                 build_installer.bat
;      → διαβάζει το VERSION από server/app.py, το περνάει εδώ ως /DVERSION=<version>,
;        και καλεί τον makensis.exe να κάνει compile το PrivacyYouTuber-Setup-<version>.exe.
;
; ΑΠΑΙΤΕΙ: NSIS 3.x στο C:\Program Files (x86)\NSIS\makensis.exe
;          + dist_onedir/PrivacyYouTuber/ ήδη χτισμένο.
;
; ΓΙΑΤΙ recursive onedir: ο εγκατεστημένος φάκελος ξεδιπλώνεται ΜΙΑ φορά και μένει
; → γρήγορη εκκίνηση (~1s). Το onefile ξεζιπάρεται 98MB σε temp ΚΑΘΕ εκκίνηση.

; ── Version: default fallback, το .bat το περνάει ως /DVERSION=… ──
!ifndef VERSION
  !define VERSION "1.4.1"
!endif
!define APP_NAME "Privacy YouTuber"
!define APP_EXE "PrivacyYouTuber.exe"
!define OUTPUT_NAME "PrivacyYouTuber-Setup-${VERSION}"

; ── Defaults (ΓΙΑΤΙ τώρα) ──
Name "${APP_NAME}"
OutFile "..\dist_onedir\${OUTPUT_NAME}.exe"
InstallDir "$LOCALAPPDATA\Programs\PrivacyYouTuber"
RequestExecutionLevel user      ; χωρίς admin — privacy-first, στο προφίλ του χρήστη
Unicode True
SetCompressor /SOLID lzma

; ── Modern UI 2 ──
!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "..\assets\PrivacyYouTuber.ico"
!define MUI_UNICON "..\assets\PrivacyYouTuber.ico"

; Σελίδες installer
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Σελίδες uninstaller
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ── Languages ──
!insertmacro MUI_LANGUAGE "English"

; Σιωπηλό σφάλμα: αν τρέχει η εφαρμογή, κλείσ' την πριν αντικαταστήσεις αρχεία
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Privacy YouTuber now"

; ── Ενότητες (sections) ──
Section "Privacy YouTuber" SEC_CORE
  SectionIn RO
  SetOutPath "$INSTDIR"

  ; 📁 Τυλίγει ΟΛΟΚΛΗΡΟ τον onedir φάκελο (και _internal/ DLLs + web/) recursive.
  File /r "..\dist_onedir\PrivacyYouTuber\*"

  ; ── Uninstaller ──
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; ── Registry (για να φαίνεται στο «Προσθήκη/Αφαίρεση προγραμμάτων») ──
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PrivacyYouTuber" \
                   "DisplayName" "Privacy YouTuber"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PrivacyYouTuber" \
                   "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PrivacyYouTuber" \
                   "Publisher" "Andreas Antoniadis"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PrivacyYouTuber" \
                   "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PrivacyYouTuber" \
                   "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PrivacyYouTuber" \
                   "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PrivacyYouTuber" \
                   "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PrivacyYouTuber" \
                   "NoRepair" 1
SectionEnd

; ── Desktop shortcut (προαιρετικό) ──
Section "Desktop shortcut" SEC_DESKTOP
  CreateShortcut "$DESKTOP\Privacy YouTuber.lnk" "$INSTDIR\${APP_EXE}"
SectionEnd

; ── Start Menu ──
Section "" SEC_STARTMENU
  SectionIn RO
  CreateDirectory "$SMPROGRAMS\Privacy YouTuber"
  CreateShortcut "$SMPROGRAMS\Privacy YouTuber\Privacy YouTuber.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortcut "$SMPROGRAMS\Privacy YouTuber\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd
; ⚠️ ΟΧΙ autostart με τα Windows — το privacy-first προϊόν δεν φυτεύει τίποτα
;    που ξεκινά μόνο του. Αν ο χρήστης το θέλει, το βάζει χειροκίνητα.

; ── /COMPONENTS: default μόνο τα core + startmenu ελέγχονται εξαρχής ──
LangString DESC_SEC_CORE ${LANG_ENGLISH} "The application itself (required)."
LangString DESC_SEC_DESKTOP ${LANG_ENGLISH} "Add a shortcut to your desktop."

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_CORE} $(DESC_SEC_CORE)
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_DESKTOP} $(DESC_SEC_DESKTOP)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ── Uninstaller ──
Section "Uninstall"
  ; Σκότωσε την εφαρμογή αν τρέχει (privacy-first: κλείνει καθαρά)
  nsExec::ExecToLog 'taskkill /IM "${APP_EXE}" /F'

  ; Σβήσε shortcuts
  Delete "$DESKTOP\Privacy YouTuber.lnk"
  RMDir /r "$SMPROGRAMS\Privacy YouTuber"

  ; Σβήσε τη registry εγγραφή
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PrivacyYouTuber"

  ; Σβήσε ΟΛΟ τον φάκελο εγκατάστασης (και τα _internal/)
  RMDir /r "$INSTDIR"
SectionEnd
