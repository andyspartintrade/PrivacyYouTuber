"""
Μετατρέπει το Gemini icon σε καθαρό ΤΕΤΡΑΓΩΝΟ .ico με ΜΩΒ να γεμίζει όλες τις άκρες.
Χωρίς λευκό/γκρι περιθώριο, χωρίς έτοιμο squircle (τα Windows βάζουν το δικό τους mask).
"""
from PIL import Image
import os

SRC = r"C:/Users/andys/Pictures/My Avatars/Gemini_Generated_Image_4hbxev4hbxev4hbx.jpg"
DST = r"C:/Users/andys/privacy-yt/assets/PrivacyYouTuber.ico"
PREVIEW = r"C:/Users/andys/privacy-yt/_icon_preview.png"

img = Image.open(SRC).convert("RGBA")
W, H = img.size

def is_purple(rgb):
    r, g, b = rgb[0], rgb[1], rgb[2]
    return r < 120 and g < 60 and b > 80

def is_red(rgb):
    r, g, b = rgb[0], rgb[1], rgb[2]
    return r > 150 and g < 80 and b < 80

def is_white_play(rgb):
    r, g, b = rgb[0], rgb[1], rgb[2]
    return r > 220 and g > 220 and b > 220

# 1. Bounding box μωβ + padding
minx, miny, maxx, maxy = 404, 78, 1004, 690
pad = 10
minx = max(0, minx - pad); miny = max(0, miny - pad)
maxx = min(W, maxx + pad); maxy = min(H, maxy + pad)
cropped = img.crop((minx, miny, maxx, maxy))

# 2. Τετράγωνος καμβάς γεμάτος μωβ
cw, ch = cropped.size
side = max(cw, ch)
purple = (69, 3, 103, 255)
canvas = Image.new("RGBA", (side, side), purple)
left = (side - cw) // 2
top = (side - ch) // 2
canvas.paste(cropped, (left, top), cropped)

# 3. Κάλυψε ό,τι λευκό/γκρι/στρογγύλεμα έμεινε στις άκρες με μωβ
#    (μέσα στο squircle υπάρχει το λευκό play — το κρατάμε· μακριά από το κέντρο → μωβ)
pixels = canvas.load()
cx, cy = side // 2, side // 2
for y in range(side):
    for x in range(side):
        r, g, b, a = pixels[x, y]
        dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
        # αν δεν είναι μωβ, κόκκινο, ή λευκό-play ΣΤΟ ΚΕΝΤΡΟ → γέμισέ το μωβ
        if is_purple((r, g, b)):
            continue
        if is_red((r, g, b)):
            continue
        if is_white_play((r, g, b)) and dist < side * 0.30:
            continue
        # οτιδήποτε άλλο (γκρι περιθώριο, λευκές γωνίες, στρογγύλεμα) → μωβ
        pixels[x, y] = purple

# 4. multi-size .ico
sizes = [256, 128, 64, 48, 32, 16]
canvas.save(DST, format="ICO", sizes=[(s, s) for s in sizes])
canvas.resize((256, 256), Image.LANCZOS).save(PREVIEW)

print(f"✅ Καθαρό τετράγωνο .ico: {DST}")
print(f"   Διάσταση: {side}x{side}")
print(f"   Μέγεθος: {os.path.getsize(DST)} bytes")
