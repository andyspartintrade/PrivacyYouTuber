"""
Παίρνει το τετράγωνο PNG (Desktop/privacy youtouber.png) και φτιάχνει
multi-size .ico με ΣΤΡΟΓΓΥΛΕΜΕΝΕΣ ΓΩΝΙΕΣ (squircle), με διαφάνεια έξω από το στρογγύλεμα.
"""
from PIL import Image, ImageDraw
import os

SRC = r"C:/Users/andys/Desktop/privacy youtouber.png"
DST = r"C:/Users/andys/privacy-yt/assets/PrivacyYouTuber.ico"
PREVIEW = r"C:/Users/andys/privacy-yt/_icon_preview.png"

img = Image.open(SRC).convert("RGBA")
W, H = img.size
# τετράγωνο
side = min(W, H)
left = (W - side) // 2
top = (H - side) // 2
img = img.crop((left, top, left + side, top + side))

# Φτιάξε squircle mask: λευκό στρογγυλεμένο τετράγωνο σε μαύρο, με anti-aliasing
# (supersample x4 για λείες άκρες)
SS = 4
big = side * SS
mask = Image.new("L", (big, big), 0)
draw = ImageDraw.Draw(mask)
radius = int(big * 0.22)   # 22% του πλάτους — φυσικό app-icon στρογγύλεμα
draw.rounded_rectangle([0, 0, big - 1, big - 1], radius=radius, fill=255)
mask = mask.resize((side, side), Image.LANCZOS)

# εφάρμοσε τη μάσκα ως alpha
img.putalpha(mask)

sizes = [256, 128, 64, 48, 32, 16]
img.save(DST, format="ICO", sizes=[(s, s) for s in sizes])

# preview σε μωβ φόντο (να φαίνεται το στρογγύλεμα)
prev = Image.new("RGBA", (256, 256), (240, 240, 240, 255))
prev.paste(img.resize((256, 256), Image.LANCZOS), (0, 0), img.resize((256, 256), Image.LANCZOS))
prev.convert("RGB").save(PREVIEW)

print(f"✅ .ico με στρογγυλεμένες γωνίες: {DST}")
print(f"   side: {side}, radius: {radius//SS}px ({22}% )")
print(f"   bytes: {os.path.getsize(DST)}")
