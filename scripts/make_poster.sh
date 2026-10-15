#!/bin/bash
# POSTER: εικόνα + 4 σειρές κειμένου δεξιά, αρμονικά χρώματα
cd "C:/Users/andys/privacy-yt/thumbnails/gemini"
SF="C\:/Users/andys/privacy-yt/fonts/sfpro/San-Francisco-Pro-Fonts-master/SF-Pro-Display-Black.otf"
SRC="G2-POSTER.jpg"

# Φόντο: scale 1280x720 + κενό πάνω (safe zone 150px για Gumroad)
BASE="scale=1280:-1,crop=1280:572:0:0,pad=1280:720:0:148:color=0x080e16,eq=contrast=1.06:saturation=1.08"

# --- ΕΚΔΟΧΗ Α: ANALOGOUS (ζεστό αμμώδες + παγωμένο λευκό) ---
ffmpeg -y -v error -i "$SRC" -vf "$BASE,\
drawtext=text='THEY':fontcolor=0xFFD9A0:fontsize=96:fontfile='$SF':x=w-text_w-48:y=170:shadowcolor=black@0.95:shadowx=5:shadowy=5,\
drawtext=text='WANT':fontcolor=0xFFD9A0:fontsize=96:fontfile='$SF':x=w-text_w-48:y=252:shadowcolor=black@0.95:shadowx=5:shadowy=5,\
drawtext=text='YOUR':fontcolor=0xE8F4F8:fontsize=96:fontfile='$SF':x=w-text_w-48:y=334:shadowcolor=black@0.95:shadowx=5:shadowy=5,\
drawtext=text='DATA':fontcolor=0xE8F4F8:fontsize=96:fontfile='$SF':x=w-text_w-48:y=416:shadowcolor=black@0.95:shadowx=5:shadowy=5" \
-frames:v 1 "POSTER-A-warm.png" 2>&1 | head -3
echo "  A: $(stat -c%s POSTER-A-warm.png 2>/dev/null) bytes"

# --- ΕΚΔΟΧΗ Β: COMPLEMENTARY (πορτοκαλί + turquoise) ---
ffmpeg -y -v error -i "$SRC" -vf "$BASE,\
drawtext=text='THEY':fontcolor=0xFFB347:fontsize=96:fontfile='$SF':x=w-text_w-48:y=170:shadowcolor=black@0.95:shadowx=5:shadowy=5,\
drawtext=text='WANT':fontcolor=0xFFB347:fontsize=96:fontfile='$SF':x=w-text_w-48:y=252:shadowcolor=black@0.95:shadowx=5:shadowy=5,\
drawtext=text='YOUR':fontcolor=0x4FE0D0:fontsize=96:fontfile='$SF':x=w-text_w-48:y=334:shadowcolor=black@0.95:shadowx=5:shadowy=5,\
drawtext=text='DATA':fontcolor=0x4FE0D0:fontsize=96:fontfile='$SF':x=w-text_w-48:y=416:shadowcolor=black@0.95:shadowx=5:shadowy=5" \
-frames:v 1 "POSTER-B-pop.png" 2>&1 | head -3
echo "  B: $(stat -c%s POSTER-B-pop.png 2>/dev/null) bytes"

# --- ΕΚΔΟΧΗ C: ICE LADDER (gradient κρύο, elegant) ---
ffmpeg -y -v error -i "$SRC" -vf "$BASE,\
drawtext=text='THEY':fontcolor=0xBFEAF5:fontsize=96:fontfile='$SF':x=w-text_w-48:y=170:shadowcolor=black@0.95:shadowx=5:shadowy=5,\
drawtext=text='WANT':fontcolor=0xD6F2FA:fontsize=96:fontfile='$SF':x=w-text_w-48:y=252:shadowcolor=black@0.95:shadowx=5:shadowy=5,\
drawtext=text='YOUR':fontcolor=0xE8F8FC:fontsize=96:fontfile='$SF':x=w-text_w-48:y=334:shadowcolor=black@0.95:shadowx=5:shadowy=5,\
drawtext=text='DATA':fontcolor=0xFFFFFF:fontsize=96:fontfile='$SF':x=w-text_w-48:y=416:shadowcolor=black@0.95:shadowx=5:shadowy=5" \
-frames:v 1 "POSTER-C-ice.png" 2>&1 | head -3
echo "  C: $(stat -c%s POSTER-C-ice.png 2>/dev/null) bytes"

echo
ls -la POSTER-*.png 2>/dev/null | awk '{print $5, $9}'
