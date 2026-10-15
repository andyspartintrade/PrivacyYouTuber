# Δημιουργεί το ambient track (αιθέριο drone) με ffmpeg — 0€.
# Απλό αλλά αποτελεσματικό: low drone + shimmer.

$out = "C:/Users/andys/privacy-yt/_video-work/ambient.wav"
$dur = 110

# 1. Low drone: 55Hz + 82.5Hz (fifth) — απαλό
ffmpeg -y -v error `
  -f lavfi -i "sine=frequency=55:duration=$dur" `
  -f lavfi -i "sine=frequency=82.5:duration=$dur" `
  -f lavfi -i "sine=frequency=110:duration=$dur" `
  -filter_complex "[0:a]volume=0.30[a0];[1:a]volume=0.18[a1];[2:a]volume=0.08[a2];[a0][a1][a2]amix=inputs=3:duration=longest,lowpass=f=400,volume=0.5" `
  -c:a pcm_s16le "C:/Users/andys/privacy-yt/_video-work/ambient-drone.wav" 2>&1 | Select-Object -Last 2

Write-Output "drone OK"
