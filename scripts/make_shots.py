"""Παράγει το πακέτο screenshots για το Gumroad.
- Καθαρίζει τα frames (crop στα PENTAPLEX tags)
- Resize σε 1600x900
- Οργανώνει με ονόματα 01-07
"""
import subprocess, os, shutil, sys

SRC = r"C:\Users\andys\Videos\_nf"
OUT = r"C:\Users\andys\privacy-yt\gumroad-shots"
os.makedirs(OUT, exist_ok=True)

# (πηγή, προορισμός, crop, περιγραφή)
# crop = None ή "w:h:x:y"
SHOTS = [
    ("n5.png",   "01-search.png",       None,                 "Search YouTube + tag cloud (EN)"),
    ("n100.png", "02-channels.png",     None,                 "Channels + Tags popup (EN)"),
    ("n200.png", "03-player-notes.png", None,                 "Player + Notes (EN)"),
    ("n300.png", "04-categories.png",   None,                 "Categories (EN)"),
    ("n450.png", "05-settings.png",     None,                 "Settings full (EL)"),
    ("n500.png", "06-categories-el.png",None,                 "Categories EL (Greek UI)"),
]

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("  !!", r.stderr.strip()[:200])
    return r.returncode == 0

print("=== ΠΑΡΑΓΩΓΗ SCREENSHOTS ===")
ok = 0
for src, dst, crop, desc in SHOTS:
    sp = os.path.join(SRC, src)
    dp = os.path.join(OUT, dst)
    if not os.path.exists(sp):
        print(f"[SKIP] {src} — λείπει")
        continue
    vf = "scale=1600:-2"
    if crop:
        vf = f"crop={crop},scale=1600:-2"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", sp, "-vf", vf, dp]
    if run(cmd):
        sz = os.path.getsize(dp) // 1024
        print(f"[OK] {dst:26s} {sz:5d} KB  — {desc}")
        ok += 1

print(f"\n{ok} screenshots έτοιμα στο {OUT}")
print("\n=== ΠΕΡΙΕΧΟΜΕΝΑ ===")
for f in sorted(os.listdir(OUT)):
    if f.endswith(".png"):
        p = os.path.join(OUT, f)
        print(f"  {os.path.getsize(p)//1024:5d} KB  {f}")
