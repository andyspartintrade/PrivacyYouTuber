#!/bin/bash
# 4 εκδοχές thumbnail με διαφορετικές γραμματοσειρές
cd "C:/Users/andys/privacy-yt/thumbnails"
SF="C\:/Users/andys/privacy-yt/fonts/sfpro/San-Francisco-Pro-Fonts-master"
BEBAS="C\:/Users/andys/privacy-yt/fonts/BebasNeue-Regular.ttf"
ANTON="C\:/Users/andys/privacy-yt/fonts/Anton-Regular.ttf"
OSW="C\:/Users/andys/privacy-yt/fonts/Oswald-Bold.ttf"

SRC="A4-shark-grin.png"
BASE="scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,eq=contrast=1.08:saturation=1.12:brightness=-0.01"

mk() {
  local OUT="$1" F1="$2" SZ="$3"
  ffmpeg -y -v error -i "$SRC" -vf "$BASE,drawbox=x=0:y=0:w=1280:h=172:color=black@0.62:t=fill,drawtext=text='They Want My Data.':fontcolor=0xFFE000:fontsize=$SZ:fontfile='$F1':x=38:y=26:shadowcolor=black@0.95:shadowx=5:shadowy=5,drawtext=text='I built my own YouTube instead.':fontcolor=white:fontsize=42:fontfile='${SF}/SF-Pro-Display-Medium.otf':x=42:y=122:shadowcolor=black@0.95:shadowx=3:shadowy=3" "$OUT" 2>&1 | head -2
  [ -f "$OUT" ] && echo "  ✅ $OUT ($(stat -c%s "$OUT") bytes)" || echo "  ❌ $OUT FAILED"
}

echo "=== 4 ΕΚΔΟΧΕΣ ΓΡΑΜΜΑΤΟΣΕΙΡΑΣ ==="
mk "V1-SFProBlack.png"  "${SF}/SF-Pro-Display-Black.otf"    80
mk "V2-SFProHeavy.png"  "${SF}/SF-Pro-Display-Heavy.otf"    84
mk "V3-BebasNeue.png"   "$BEBAS"                             96
mk "V4-Anton.png"       "$ANTON"                             86

echo
ls -la V*.png 2>/dev/null | awk '{print $5, $9}'
