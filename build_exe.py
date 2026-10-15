"""Χτίζει το Privacy-YouTuber σε ένα μόνο εκτελέσιμο (.exe) με PyInstaller.

Χρήση:
    python build_exe.py

Το αποτέλεσμα μπαίνει στο dist/PrivacyYouTuber.exe (ή PrivacyYouTuber στο Linux/Mac).
Ο χρήστης το κάνει διπλό κλικ → ξεκινά ο server + ανοίγει το dashboard στον browser.

Δεν χρειάζεται Python στον υπολογιστή του τελικού χρήστη.
"""

import os
import subprocess
import sys


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("📦 Εγκαθιστώ το PyInstaller…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def ensure_icon():
    """Βρίσκει (ή φτιάχνει) το .ico. Δεν σκάει ποτέ — το icon είναι προαιρετικό."""
    ico = os.path.join("assets", "PrivacyYouTuber.ico")
    if os.path.exists(ico):
        return ico
    try:
        # Δοκίμασε με ΑΥΤΟ το python· αν το Pillow είναι σπασμένο, δοκίμασε τα επόμενα.
        for py in _python_candidates():
            try:
                subprocess.check_call([py, "make_app_icon.py"])
                if os.path.exists(ico):
                    return ico
            except Exception:
                continue
    except Exception as e:
        print(f"   (δεν φτιάχτηκε το icon: {e})")
    return ico if os.path.exists(ico) else None


def _python_candidates():
    """[τρέχον python] + όποια άλλα βρεθούν (το Pillow μπορεί να λείπει από το venv του build)."""
    out = [sys.executable]
    import glob as _glob
    for pat in (
        os.path.expandvars(r"%LOCALAPPDATA%\hermes\tools\python-3*\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python3*\python.exe"),
    ):
        out += [p for p in _glob.glob(pat) if p not in out]
    import shutil as _sh
    for exe in ("py", "python"):
        p = _sh.which(exe)
        if p and p not in out:
            out.append(p)
    return out


def main():
    ensure_pyinstaller()

    # Στα Windows το --add-data χωρίζει με ';', σε Linux/Mac με ':'.
    sep = os.pathsep
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",            # ένα μόνο εκτελέσιμο
        "--noconsole",          # χωρίς μαύρο console παράθυρο (GUI app)
        "--name", "PrivacyYouTuber",
        "--add-data", f"web{sep}web",   # κουβαλάει το dashboard μέσα
        "--hidden-import", "webview",
        "--hidden-import", "webview.platforms.winforms",
        "--hidden-import", "clr_loader",
        "--hidden-import", "pythonnet",
        "--collect-all", "webview",
        "--clean",
    ]
    # 🎨 Icon εφαρμογής: φαίνεται σε taskbar/Explorer/Alt+Tab. Μόνο για Windows (το .ico).
    icon = ensure_icon()
    if icon and os.name == "nt":
        cmd += ["--icon", icon]
        print(f"🎨 Icon: {icon}")
    cmd.append("cli.py")
    print("🔨 Χτίζω:", " ".join(cmd))
    subprocess.check_call(cmd)
    print()
    print("✅ Έτοιμο!")
    print("   Εκτελέσιμο: dist/PrivacyYouTuber.exe")
    # Αντέγραψε και στο Desktop (Windows) — για να ανοίγεις πάντα το σωστό.
    if os.name == "nt":
        import shutil
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        try:
            shutil.copy("dist/PrivacyYouTuber.exe", os.path.join(desktop, "PrivacyYouTuber.exe"))
            print("   ✅ Αντιγράφηκε και στην επιφάνεια εργασίας.")
        except Exception as e:
            print(f"   (δεν αντιγράφηκε στο Desktop: {e})")


if __name__ == "__main__":
    main()
