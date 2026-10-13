"""
Μετατρέπει το Gemini icon (JPG 1408x768 με το squircle στο κέντρο) σε
multi-size .ico για Windows. Κόβει ΜΟΝΟ το squircle (όχι το γκρι/λευκό περιθώριο).
"""
from PIL import Image
import os

SRC = r"C:/Users/andys/Pictures/My Avatars/Gemini_Generated_Image_4hbxev4hbxev4hbx.jpg"
DST = r"C:/Users/andys/privacy-yt/assets/PrivacyYouTuber.ico"

img = Image.open(SRC).convert("RGBA")
W, H = img.size
px = img.load()

def is_purple(rgb):
    r, g, b = rgb[0], rgb[1], rgb[2]
    return r < 120 and g < 60 and b > 80

# Bounding box μωβ (από πριν: x[404..1004] y[78..690])
minx, miny, maxx, maxy = 404, 78, 1004, 690

# crop με λίγο padding για να μη χάσουμε τα στρογγυλεμένα άκρα, μετά τετράγωνο
pad = 6
box = (minx - pad, miny - pad, maxx + pad, maxy + pad)
box = (max(0, box[0]), max(0, box[1]), min(W, box[2]), min(H, box[3]))
cropped = img.crop(box)

# τετράγωνο (ύψος == πλάτος, cropped στο μεγαλύτερο πλευρό)
cw, ch = cropped.size
side = min(cw, ch)
left = (cw - side) // 2
top = (ch - side) // 2
square = cropped.crop((left, top, left + side, top + side))

# multi-size .ico
sizes = [256, 128, 64, 48, 32, 16]
square.save(DST, format="ICO", sizes=[(s, s) for s in sizes])

print(f"✅ Έγινε .ico: {DST}")
print(f"   Squircle cropped: {side}x{side}")
print(f"   Μεγέθη: {sizes}")
print(f"   Μέγεθος αρχείου: {os.path.getsize(DST)} bytes")
