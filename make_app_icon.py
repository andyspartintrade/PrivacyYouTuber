"""Φτιάχνει το icon της εφαρμογής (.ico) για το exe — ασπίδα + play.

Παίρνει το ΙΔΙΟ σχέδιο με το make_icons.py (ασπίδα + play, σκούρο φόντο) και το
γράφει ως .ico με πολλαπλά μεγέθη, ώστε να φαίνεται καθαρά παντού:
taskbar, Explorer, Alt+Tab, μικρά εικονίδια.

Χρήση:
    python make_app_icon.py
Παράγει:
    assets/PrivacyYouTuber.ico
"""

import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "assets")
OUT_ICO = os.path.join(OUT_DIR, "PrivacyYouTuber.ico")

DARK = (13, 16, 23, 255)       # #0d1017
BORDER = (36, 43, 56, 255)     # #242b38
BLUE = (108, 140, 255, 255)    # #6c8cff
GREEN = (34, 211, 165, 255)    # #22d3a5

# Μεγέθη που ζητάει τα Windows: 16 (taskbar μικρό), 32, 48, 64, 128, 256 (Alt+Tab / μεγάλα).
SIZES = [16, 24, 32, 48, 64, 128, 256]


def draw_master(size=512):
    """Το ίδιο σχέδιο με το extension icon: στρογγυλεμένο τετράγωνο, ασπίδα, play."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 512.0
    S = lambda v: int(v * s)  # noqa: E731

    d.rounded_rectangle(
        [S(8), S(8), S(504), S(504)], radius=S(96), fill=DARK,
        outline=BORDER, width=S(6),
    )

    shield = [
        (S(180), S(168)), (S(332), S(168)),
        (S(332), S(296)),
        (S(256), S(396)),
        (S(180), S(296)),
    ]
    d.polygon(shield, fill=BLUE)

    play = [(S(222), S(238)), (S(222), S(330)), (S(308), S(284))]
    d.polygon(play, fill=GREEN)

    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    master = draw_master(512)
    # Το Pillow γράφει .ico με πολλά μεγέθη σε ένα αρχείο.
    master.save(OUT_ICO, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"✅ {OUT_ICO}")
    print(f"   Μεγέθη: {', '.join(f'{s}x{s}' for s in SIZES)}")
    print(f"   Μέγεθος αρχείου: {os.path.getsize(OUT_ICO) / 1024:.1f} KB")


if __name__ == "__main__":
    try:
        main()
    except ImportError:
        sys.exit("Χρειάζεται το Pillow (pip install pillow).")
