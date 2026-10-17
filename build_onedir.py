"""Χτίζει το Privacy-YouTuber σε ΦΑΚΕΛΟ (onedir) με PyInstaller.

Χρήση:
    python build_onedir.py

Γιατί onedir αντί onefile:
    • onefile  → 1 αρχείο, αλλά ξεζιπάρεται (98MB) σε temp ΚΑΘΕ εκκίνηση → 7-20s
    • onedir   → φάκελος, τα αρχεία είναι ΕΤΟΙΜΑ στη θέση τους → ~1s εκκίνηση

Και τα δύο είναι portable: καμία εγκατάσταση, κανένα μητρώο, σβήνεις τον φάκελο = τέλος.
Το αποτέλεσμα μπαίνει στο dist_onedir/PrivacyYouTuber/ και αντιγράφεται στο Desktop.
"""

import os
import shutil
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

    sep = os.pathsep
    out_dir = "dist_onedir"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",             # 📁 ΦΑΚΕΛΟΣ (όχι ένα αρχείο) → γρήγορη εκκίνηση
        "--noconsole",          # χωρίς μαύρο console παράθυρο (GUI app)
        "--name", "PrivacyYouTuber",
        "--add-data", f"web{sep}web",   # κουβαλάει το dashboard μέσα
        "--hidden-import", "webview",
        "--hidden-import", "webview.platforms.winforms",
        "--hidden-import", "clr_loader",
        "--hidden-import", "pythonnet",
        "--collect-all", "webview",
        "--optimize", "2",
        # ⚠️ ΜΗΝ βάλεις το tkinter στα --exclude-module!
        #    Ο server το χρησιμοποιεί για τα NATIVE dialogs του /export και /import
        #    (filedialog.asksaveasfilename / askopenfilename). Αν το εξαιρέσεις,
        #    τα κουμπιά «Εξαγωγή»/«Εισαγωγή» αποτυγχάνουν ΣΙΩΠΗΛΑ (το _tk_dialog
        #    έχει try/except που καταπίνει το ImportError) — και δεν ανοίγει τίποτα.
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.filedialog",
        "--hidden-import", "tkinter.constants",
        "--exclude-module", "unittest",
        "--exclude-module", "pydoc",
        "--exclude-module", "doctest",
        "--exclude-module", "test",
        "--exclude-module", "lib2to3",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PySide2",
        "--distpath", out_dir,  # χωριστός φάκελος, να μη σβήσει το onefile dist/
        "--workpath", "build_onedir_work",
        "--noconfirm",          # ⚠️ χωρίς αυτό σκάει αν ο dist_onedir/ δεν είναι άδειος
        # ⚠️ ΟΧΙ --specpath: το spec πρέπει να μείνει στο root, αλλιώς το
        #    --add-data web;web ψάχνει το «web» μέσα στον φάκελο του spec και αποτυγχάνει.
        "--clean",
    ]

    icon = ensure_icon()
    if icon and os.name == "nt":
        cmd += ["--icon", icon]
        print(f"🎨 Icon: {icon}")

    # 🏷️ Version info στα properties του exe (FileVersion/ProductVersion).
    #    Χωρίς αυτό, δεξί κλικ → Properties → Details είναι ΚΕΝΟ.
    vi = os.path.join("version_info.txt")
    if os.path.exists(vi) and os.name == "nt":
        cmd += ["--version-file", vi]
        print(f"🏷️  Version info: {vi}")

    cmd.append("cli.py")
    print("🔨 Χτίζω (onedir):", " ".join(cmd))
    subprocess.check_call(cmd)

    app_dir = os.path.join(out_dir, "PrivacyYouTuber")
    exe = os.path.join(app_dir, "PrivacyYouTuber.exe")
    if not os.path.exists(exe) and os.name != "nt":
        exe = os.path.join(app_dir, "PrivacyYouTuber")

    print()
    print("✅ Έτοιμο!")
    print(f"   📁 Φάκελος: {app_dir}")
    print(f"   🚀 Εκτελέσιμο: {exe}")

    # Μέτρησε το μέγεθος του φακέλου
    try:
        total = sum(
            os.path.getsize(os.path.join(r, f))
            for r, _d, fs in os.walk(app_dir) for f in fs
        )
        print(f"   📦 Μέγεθος φακέλου: {total / 1024 / 1024:.1f} MB")
    except Exception:
        pass

    # Αντέγραψε ΟΛΟΚΛΗΡΟ τον φάκελο στο Desktop (Windows).
    if os.name == "nt":
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        dest = os.path.join(desktop, "PrivacyYouTuber")
        try:
            if os.path.exists(dest):
                shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(app_dir, dest)
            print(f"   ✅ Αντιγράφηκε στην επιφάνεια εργασίας: {dest}")
            # 🔐 DEV .env: ΔΕΝ το αντιγράφουμε ΠΛΕΟΝ αυτόματα.
            #    Από την 1.4.1 το license verify δουλεύει με hardcoded product_id
            #    (GUMROAD_PRODUCT_ID_DEFAULT στο server/app.py) — ο πελάτης ΔΕΝ
            #    χρειάζεται .env και το app ζητάει κανονικά serial.
            #    Για τοπικές δοκιμές χωρίς serial: βάλε .env ΧΕΙΡΟΚΙΝΗΤΑ με
            #    LICENSE_CHECK=off δίπλα στο exe (δεν πρέπει να μπει σε installer).
            env_dst = os.path.join(dest, ".env")
            if os.path.isfile(env_dst):
                print(f"   ℹ️  Υπάρχει ήδη .env στο {dest} (dev) — το αφήνω ως έχει.")
            print("      (Άνοιξέ το από εκεί — όχι από το dist_onedir/)")
        except Exception as e:
            print(f"   ⚠️  Δεν αντιγράφηκε στο Desktop: {e}")
            print(f"      Τρέξ' το από: {exe}")


if __name__ == "__main__":
    main()
