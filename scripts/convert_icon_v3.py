"""
Καθαρό crop του squircle (μωβ) → τετράγωνο → multi-size .ico.
ΔΕΝ αλλάζει τίποτα στα χρώματα — μόνο κόβει το λευκό/γκρι περιθώριο.
"""
from PIL import Image
import os

SRC = r"C:/Users/andys/Pictures/My Avatars/Gemini_Generated_Image_4hbxev4hbxev4hbx.jpg"
DST = r"C:/Users/andys/privacy-yt/assets/PrivacyYouTuber.ico"
PREVIEW = r"C:/Users/andys/privacy-yt/_icon_preview.png"

img = Image.open(SRC).convert("RGBA")

# Ακριβές μωβ bounding box (μετρημένο)
minx, miny, maxx, maxy = 403, 77, 1004, 690

cropped = img.crop((minx, miny, maxx + 1, maxy + 1))
cw, ch = cropped.size  # 602 x 614

# τετράγωνο: πάρε το μεγαλύτερο, κέντραρε
side = max(cw, ch)  # 614
canvas = Image.new("RGBA", (side, side), (69, 3, 103, 255))  # μωβ γέμισμα
left = (side - cw) // 2
top = (side - ch) // 2
canvas.paste(cropped, (left, top))

sizes = [256, 128, 64, 48, 32, 16]
canvas.save(DST, format="ICO", sizes=[(s, s) for s in sizes])
canvas.resize((256, 256), Image.LANCZOS).save(PREVIEW)

print(f"✅ Done: {DST}")
print(f"   squircle: {cw}x{ch} → canvas {side}x{side}")
print(f"   bytes: {os.path.getsize(DST)}")
