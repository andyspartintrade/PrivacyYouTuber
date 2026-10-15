#!/bin/bash
# Καθαρίζει το "Privacy YouTuber" logo -> 600x600 sharp icon
cd "C:/Users/andys/privacy-yt/icon-work"
BG="0x0D1017"

echo "=== 1. ΣΚΕΠΑΖΩ ΤΟ ΚΕΙΜΕΝΟ (y=0..150) με #0D1017 ==="
ffmpeg -y -v error -i original.png -vf "drawbox=x=0:y=0:w=720:h=150:color=${BG}@1.0:t=fill" "clean-bg.png" 2>&1 | head -3
echo "  ✅ clean-bg.png"

echo
echo "=== 2. ΠΑΙΡΝΩ ΚΑΘΑΡΟ LOGO ΣΕ ΥΨΗΛΗ ΑΝΑΛΥΣΗ (upscale 4x με lanczos) ==="
# Crop το logo (y=18..133) και upscale 4x για sharpness
ffmpeg -y -v error -i original.png -vf "crop=720:110:0:20,scale=2880:440:flags=lanczos" "logo-4x.png" 2>&1 | head -3
echo "  ✅ logo-4x.png"

echo
echo "=== 3. 600x600: background + logo ==="
# Background: crop την εικόνα καλά (χωρίς το πάνω κείμενο) -> τετράγωνο
ffmpeg -y -v error -i original.png -vf "crop=720:620:0:100,scale=600:517:flags=lanczos,pad=600:600:0:83:color=${BG}" "base-600.png" 2>&1 | head -3
echo "  ✅ base-600.png"

echo
echo "=== 4. ΣΥΝΘΕΣΗ: base + logo (4x downscaled σε 600) ==="
# Το logo γίνεται 600 πλάτος, μπαίνει στο πάνω μέρος
ffmpeg -y -v error -i "base-600.png" -i "logo-4x.png" -filter_complex "\
[1:v]scale=600:-1:flags=lanczos[logo];\
[0:v][logo]overlay=x=(W-w)/2:y=28:format=auto" -frames:v 1 "icon-600.png" 2>&1 | head -3
ls -la icon-600.png 2>/dev/null | awk '{print "  ", $5, $9}'
ffprobe -v error -show_entries stream=width,height -of csv=p=0 icon-600.png 2>/dev/null | awk '{print "  Διαστάσεις: " $0}'
