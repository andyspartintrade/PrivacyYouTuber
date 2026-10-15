"""
Φτιάχνει PSD με layers:
  - BACKGROUND (η εικόνα, native 1024x572)
  - 4 TEXT layers (A warm / B pop / C ice / ORIGINAL yellow)
  - SAFE-ZONE guide
Κάθε text layer = transparent PNG πάνω από το background.
"""
import os
from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage

SRC = r"C:\Users\andys\privacy-yt\thumbnails\gemini\G2-POSTER.jpg"
OUT = r"C:\Users\andys\privacy-yt\thumbnails\gemini\POSTER-LAYERS.psd"
FONT = r"C:\Users\andys\privacy-yt\fonts\sfpro\San-Francisco-Pro-Fonts-master\SF-Pro-Display-Black.otf"
WORK = r"C:\Users\andys\privacy-yt\thumbnails\gemini\_layers"
os.makedirs(WORK, exist_ok=True)

# --- BACKGROUND: native διάσταση ---
bg = Image.open(SRC).convert("RGB")
W, H = bg.size
print(f"  Background: {W}x{H}")

def make_text_layer(name, colors, size=54, x_offset=14, y_start=100, leading=62, out_name=None):
    """Φτιάχνει transparent PNG με 4 σειρές κειμένου, δεξιά στοιχισμένο."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, size)
    words = ["THEY", "WANT", "YOUR", "DATA"]
    y = y_start
    for word, col in zip(words, colors):
        # Δεξιά στοίχιση
        bbox = d.textbbox((0, 0), word, font=font)
        tw = bbox[2] - bbox[0]
        x = W - tw - x_offset
        # Shadow (μαύρο, 3px offset)
        for dx, dy in [(3,3), (2,2), (1,1)]:
            d.text((x+dx, y+dy), word, font=font, fill=(0,0,0,230))
        d.text((x, y), word, font=font, fill=col)
        y += leading
    p = os.path.join(WORK, out_name or f"{name}.png")
    img.save(p)
    print(f"  {name}: {p}")
    return p

# Χρώματα
TXT = {
    "TEXT-1-WARM":  [(255,217,160,255),(255,217,160,255),(232,244,248,255),(232,244,248,255)],
    "TEXT-2-POP":   [(255,179,71,255),(255,179,71,255),(79,224,208,255),(79,224,208,255)],
    "TEXT-3-ICE":   [(191,234,245,255),(214,242,250,255),(232,248,252,255),(255,255,255,255)],
    "TEXT-4-ORIG":  [(255,224,0,255),(255,224,0,255),(255,255,255,255),(255,255,255,255)],
}

paths = {}
for name, cols in TXT.items():
    paths[name] = make_text_layer(name, cols)

# --- SAFE ZONE guide ---
sz = Image.new("RGBA", (W, H), (0,0,0,0))
d = ImageDraw.Draw(sz)
# Γραμμή στο 148px (Gumroad safe zone)
d.line([(0,148),(W,148)], fill=(255,0,0,200), width=2)
d.text((10, 152), "GUMROAD SAFE ZONE (below this line)", fill=(255,80,80,255))
sz_path = os.path.join(WORK, "GUIDE-safe-zone.png")
sz.save(sz_path)
print(f"  GUIDE: {sz_path}")

# --- ΦΤΙΑΧΝΩ ΤΟ PSD ---
psd = PSDImage.new(mode="RGB", size=(W, H))
print(f"\n  PSD created: {W}x{H}")

# Background
bg_layer = psd.create_pixel_layer(bg, name="BACKGROUND")
print("  ✅ BACKGROUND")

# Text layers (πάνω από background)
for name, p in paths.items():
    t = Image.open(p).convert("RGBA")
    layer = psd.create_pixel_layer(t, name=name, top=0, left=0)
    print(f"  ✅ {name}")

# Guide
g = Image.open(sz_path).convert("RGBA")
gl = psd.create_pixel_layer(g, name="GUIDE-safe-zone", top=0, left=0)
print("  ✅ GUIDE-safe-zone")

psd.save(OUT)
print(f"\n  💾 SAVED: {OUT} ({os.path.getsize(OUT):,} bytes)")
