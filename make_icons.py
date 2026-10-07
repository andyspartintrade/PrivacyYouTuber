"""Γεννάει τα icons του extension (16/48/128 PNG) — ασπίδα + play.

Σχέδιο: σκούρο στρογγυλεμένο τετράγωνο, μπλε ασπίδα (privacy), πράσινο play (video).
Τα παράγει σε 512 και τα σμικραίνει με LANCZOS για καθαρό αποτέλεσμα σε κάθε μέγεθος.
"""

import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extension", "icons")

DARK = (13, 16, 23, 255)       # #0d1017
BORDER = (36, 43, 56, 255)     # #242b38
BLUE = (108, 140, 255, 255)    # #6c8cff
GREEN = (34, 211, 165, 255)    # #22d3a5


def draw_master(size=512):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 512.0
    S = lambda v: int(v * s)

    # Φόντο: στρογγυλεμένο τετράγωνο
    d.rounded_rectangle(
        [S(8), S(8), S(504), S(504)], radius=S(96), fill=DARK,
        outline=BORDER, width=S(6),
    )

    # Ασπίδα (privacy)
    shield = [
        (S(180), S(168)), (S(332), S(168)),   # πάνω οριζόντια
        (S(332), S(296)),                     # δεξιά πλευρά κάτω
        (S(256), S(396)),                     # κάτω μύτη
        (S(180), S(296)),                     # αριστερά πλευρά κάτω
    ]
    d.polygon(shield, fill=BLUE)

    # Play τρίγωνο (video) μέσα στην ασπίδα
    play = [(S(222), S(238)), (S(222), S(330)), (S(308), S(284))]
    d.polygon(play, fill=GREEN)

    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    master = draw_master(512)
    for name, px in [("icon16", 16), ("icon48", 48), ("icon128", 128)]:
        icon = master.resize((px, px), Image.LANCZOS)
        path = os.path.join(OUT, f"{name}.png")
        icon.save(path)
        print(f"✅ {name}.png ({px}x{px})")
    print("   Φάκελος:", OUT)


if __name__ == "__main__":
    main()
