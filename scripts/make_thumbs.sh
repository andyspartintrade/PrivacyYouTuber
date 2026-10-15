#!/bin/bash
# Φτιάχνει thumbnails 1280x720 με text overlay
cd "C:/Users/andys/privacy-yt/thumbnails"

FONT='C\:/Windows/Fonts/arialbd.ttf'
FONT2='C\:/Windows/Fonts/impact.ttf'

make_thumb() {
  local SRC="$1" OUT="$2" LINE1="$3" LINE2="$4" SZ1="$5"
  ffmpeg -y -v error -i "$SRC" \
    -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,eq=contrast=1.10:saturation=1.12,drawbox=x=0:y=0:w=1280:h=175:color=black@0.60:t=fill,drawtext=text='$LINE1':fontcolor=0xFFE000:fontsize=$SZ1:fontfile='$FONT':x=40:y=26:shadowcolor=black@0.95:shadowx=5:shadowy=5,drawtext=text='$LINE2':fontcolor=white:fontsize=46:fontfile='$FONT':x=44:y=124:shadowcolor=black@0.95:shadowx=3:shadowy=3" \
    "$OUT" 2>&1 | head -3
  [ -f "$OUT" ] && echo "  ✅ $OUT ($(stat -c%s "$OUT") bytes)" || echo "  ❌ $OUT"
}

echo "=== Β/C/D + ΚΕΙΜΕΝΟ ==="
make_thumb "B-hug-split.png"   "B-final.png" "THEY ARE WATCHING" "Your YouTube, 100% private" 72
make_thumb "C-hug-shield.png"  "C-final.png" "100% PRIVATE"      "No account. No tracking. No ads." 88
make_thumb "D-hug-circle.png"  "D-final.png" "NO ONE SEES IT"    "Your own YouTube library" 82
make_thumb "A1-fae-hug.png"    "A1-final.png" "NO TRACKING"      "Nothing leaves your PC" 88

echo
echo "=== ΟΛΑ ==="
ls -la *final.png A-frame7-text.png 2>/dev/null | awk '{print $5, $9}'
