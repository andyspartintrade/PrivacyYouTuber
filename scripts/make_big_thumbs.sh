#!/bin/bash
# BIG TEXT thumbnails (MrBeast style) - 1280x720
cd "C:/Users/andys/privacy-yt/thumbnails"
SF="C\:/Users/andys/privacy-yt/fonts/sfpro/San-Francisco-Pro-Fonts-master/SF-Pro-Display-Black.otf"
ANTON="C\:/Users/andys/privacy-yt/fonts/Anton-Regular.ttf"
SRC="A4-shark-grin.png"
BASE="scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,eq=contrast=1.10:saturation=1.14:brightness=-0.02"

# B1: "THEY WANT MY DATA" - τεράστιο, 2 γραμμές, top
ffmpeg -y -v error -i "$SRC" -vf "$BASE,drawbox=x=0:y=0:w=1280:h=290:color=black@0.68:t=fill,drawtext=text='THEY WANT':fontcolor=0xFFE000:fontsize=132:fontfile='$SF':x=(w-text_w)/2:y=20:shadowcolor=black@0.95:shadowx=6:shadowy=6,drawtext=text='MY DATA':fontcolor=white:fontsize=132:fontfile='$SF':x=(w-text_w)/2:y=150:shadowcolor=black@0.95:shadowx=6:shadowy=6" "B1-big-center.png" 2>&1 | head -2
echo "  B1: $(stat -c%s B1-big-center.png 2>/dev/null) bytes"

# B2: "MY DATA. MY YOUTUBE." - Anton condensed
ffmpeg -y -v error -i "$SRC" -vf "$BASE,drawbox=x=0:y=0:w=1280:h=260:color=black@0.66:t=fill,drawtext=text='MY DATA.':fontcolor=0xFF3333:fontsize=124:fontfile='$ANTON':x=(w-text_w)/2:y=26:shadowcolor=black@0.95:shadowx=6:shadowy=6,drawtext=text='MY YOUTUBE.':fontcolor=white:fontsize=124:fontfile='$ANTON':x=(w-text_w)/2:y=142:shadowcolor=black@0.95:shadowx=6:shadowy=6" "B2-bold-red.png" 2>&1 | head -2
echo "  B2: $(stat -c%s B2-bold-red.png 2>/dev/null) bytes"

# B3: "I BUILT MY OWN" - τεράστιο
ffmpeg -y -v error -i "$SRC" -vf "$BASE,drawbox=x=0:y=0:w=1280:h=200:color=black@0.70:t=fill,drawtext=text='I BUILT MY OWN':fontcolor=0xFFE000:fontsize=112:fontfile='$SF':x=(w-text_w)/2:y=38:shadowcolor=black@0.95:shadowx=6:shadowy=6" "B3-built-big.png" 2>&1 | head -2
echo "  B3: $(stat -c%s B3-built-big.png 2>/dev/null) bytes"

# B4: "NO ONE SEES IT" + μικρό "but you"
ffmpeg -y -v error -i "$SRC" -vf "$BASE,drawbox=x=0:y=0:w=1280:h=230:color=black@0.68:t=fill,drawtext=text='NO ONE SEES IT':fontcolor=0x4CD964:fontsize=118:fontfile='$SF':x=(w-text_w)/2:y=28:shadowcolor=black@0.95:shadowx=6:shadowy=6,drawtext=text='not even Google':fontcolor=white:fontsize=48:fontfile='$SF':x=(w-text_w)/2:y=162:shadowcolor=black@0.95:shadowx=3:shadowy=3" "B4-green.png" 2>&1 | head -2
echo "  B4: $(stat -c%s B4-green.png 2>/dev/null) bytes"

# B5: BOTTOM text version (subject στο πάνω, text κάτω)
ffmpeg -y -v error -i "$SRC" -vf "$BASE,drawbox=x=0:y=520:w=1280:h=200:color=black@0.72:t=fill,drawtext=text='THEY WANT MY DATA.':fontcolor=0xFFE000:fontsize=104:fontfile='$SF':x=(w-text_w)/2:y=552:shadowcolor=black@0.95:shadowx=6:shadowy=6" "B5-bottom.png" 2>&1 | head -2
echo "  B5: $(stat -c%s B5-bottom.png 2>/dev/null) bytes"

# B6: 3 words MAX - "MY DATA" μόνο (τεράστιο)
ffmpeg -y -v error -i "$SRC" -vf "$BASE,drawbox=x=0:y=0:w=1280:h=190:color=black@0.70:t=fill,drawtext=text='MY DATA':fontcolor=0xFFE000:fontsize=168:fontfile='$SF':x=(w-text_w)/2:y=12:shadowcolor=black@0.95:shadowx=7:shadowy=7" "B6-huge.png" 2>&1 | head -2
echo "  B6: $(stat -c%s B6-huge.png 2>/dev/null) bytes"

echo
ls -la B*.png 2>/dev/null | awk '{print $5, $9}'
