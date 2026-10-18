@echo off
REM ============================================================
REM  Privacy YouTuber — build installer (one command).
REM
REM  Τι κάνει:
REM    1. Διαβάζει το VERSION από server/app.py (τη μία πηγή αλήθειας).
REM    2. Καλεί το NSIS (makensis.exe) να κάνει compile το .nsi,
REM       περνώντας το version σαν /DVERSION=<version>.
REM    3. Βγάζει PrivacyYouTuber-Setup-<version>.exe στο dist_onedir/.
REM
REM  ΠΡΟΫΠΟΘΕΣΕΙΣ (μία φορά):
REM    - Έχεις εγκαταστήσει NSIS 3.x (nsis.sourceforge.io/Download).
REM    - Έχεις ήδη χτίσει το onedir:  python build_onedir.py
REM
REM  ΧΡΗΣΗ: κάθε φορά που βγαίνει νέα έκδοση:
REM    python build_onedir.py
REM    build_installer.bat
REM  → δεν αγγίζεις ΤΙΠΟΤΑ άλλο, ούτε το version.
REM ============================================================

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ──────────────────────────────────────────────
echo  Privacy YouTuber — build installer (NSIS)
echo ──────────────────────────────────────────────

REM --- 1. Βρες το makensis.exe --------------------------------
set "MAKENSIS="
if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
    set "MAKENSIS=C:\Program Files (x86)\NSIS\makensis.exe"
) else if exist "C:\Program Files\NSIS\makensis.exe" (
    set "MAKENSIS=C:\Program Files\NSIS\makensis.exe"
) else if exist "%LOCALAPPDATA%\Programs\NSIS\makensis.exe" (
    set "MAKENSIS=%LOCALAPPDATA%\Programs\NSIS\makensis.exe"
)
if not defined MAKENSIS (
    echo.
    echo  [ERROR] Δεν βρέθηκε το NSIS (makensis.exe).
    echo          Κατέβασέ το από https://nsis.sourceforge.io/Download
    echo          και εγκατάστησέ το με τις default ρυθμίσεις.
    echo.
    pause
    exit /b 1
)
echo  [OK] NSIS: !MAKENSIS!

REM --- 2. Διάβασε το VERSION από server/app.py ---------------
set "VERSION="
for /f "usebackq tokens=3 delims= " %%v in (`findstr /r /c:"^VERSION = " "%~dp0server\app.py"`) do (
    set "VERSION=%%v"
    set "VERSION=!VERSION:"=!"
)
if not defined VERSION (
    echo  [ERROR] Δεν βρέθηκε VERSION στο server/app.py — ΜΗΝ χτίσεις installer χωρίς version.
    pause
    exit /b 1
)
echo  [OK] Version: !VERSION!

REM --- 3. Έλεγξε ότι υπάρχει το onedir build -----------------
if not exist "%~dp0dist_onedir\PrivacyYouTuber\PrivacyYouTuber.exe" (
    echo.
    echo  [ERROR] Δεν βρέθηκε dist_onedir\PrivacyYouTuber\PrivacyYouTuber.exe
    echo          Τρέξε πρώτα:  python build_onedir.py
    echo.
    pause
    exit /b 1
)
echo  [OK] onedir build βρέθηκε.

REM --- 4. Compile ----------------------------------------------
echo.
echo  Compiling... (μπορεί να πάρει 1-2 λεπτά)
echo ──────────────────────────────────────────────
"!MAKENSIS!" -DVERSION=!VERSION! -INPUTCHARSET UTF8 /V2 "%~dp0installer\PrivacyYouTuber.nsi"

if errorlevel 1 (
    echo.
    echo  [ERROR] Το NSIS compile απέτυχε. Δες τα μηνύματα πιο πάνω.
    pause
    exit /b 1
)

echo.
echo ──────────────────────────────────────────────
echo  [OK] ΕΤΟΙΜΟ: dist_onedir\PrivacyYouTuber-Setup-!VERSION!.exe
echo ──────────────────────────────────────────────
pause
