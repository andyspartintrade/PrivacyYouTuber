"""
Ανακτά βίντεο από χαλασμένο MP4 (χωρίς moov atom).
Το ffmpeg έγραψε το `mdat` (raw AVC + AAC) αλλά όχι το `moov` index.
Λύση: Διαβάζω το mdat, βγάζω τα raw NAL units, τα ξαναχτίζω ως MP4.

Μέθοδος: ffmpeg με -f h264 για το video + -f aac για τον ήχο, μετά mux.
Επειδή το mdat έχει interleaved A/V, δοκιμάζω:
1. h264 extract (αγνοώ audio bytes)
2. Ξεχωριστά audio
"""
import struct, sys, os, subprocess

SRC = r"C:\Users\andys\privacy-yt\_video-work\_cap2.mp4"
OUT_DIR = r"C:\Users\andys\privacy-yt\_video-work"

print(f"=== ΑΝΑΛΥΣΗ: {SRC} ===")
print(f"  μέγεθος: {os.path.getsize(SRC):,} bytes")

# Διάβασε τα top-level boxes
def read_boxes(path, max_boxes=20):
    boxes = []
    with open(path, 'rb') as f:
        pos = 0
        fsize = os.path.getsize(path)
        while pos < fsize and len(boxes) < max_boxes:
            f.seek(pos)
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            size = struct.unpack('>I', hdr[:4])[0]
            btype = hdr[4:8].decode('latin-1')
            if size == 1:
                ext = f.read(8)
                size = struct.unpack('>Q', ext)[0]
            if size == 0:
                size = fsize - pos
            boxes.append((btype, pos, size))
            pos += size if size >= 8 else 8
    return boxes

boxes = read_boxes(SRC)
print("\n  TOP-LEVEL BOXES:")
for btype, pos, size in boxes:
    print(f"    {btype}  @ {pos:,}  size={size:,}")

# Το mdat περιέχει τα raw data
mdat = [b for b in boxes if b[0] == 'mdat']
if mdat:
    _, mpos, msize = mdat[0]
    print(f"\n  mdat ξεκινά @ {mpos} (header 8 bytes) → data @ {mpos+8}")
    print(f"  mdat size: {msize:,} bytes")

# Κόψε τα raw data (μετά το mdat header)
data_start = mpos + 8
data_end = mpos + msize
print(f"\n=== ΕΞΑΓΩΓΗ RAW DATA ===")
with open(SRC, 'rb') as f:
    f.seek(data_start)
    raw = f.read(data_end - data_start)

raw_path = os.path.join(OUT_DIR, "_raw_data.bin")
with open(raw_path, 'wb') as f:
    f.write(raw)
print(f"  ✅ {raw_path} ({len(raw):,} bytes)")

# Δοκίμασε h264 extraction
print("\n=== ΔΟΚΙΜΗ H264 EXTRACTION ===")
h264_out = os.path.join(OUT_DIR, "_rec.h264")
r = subprocess.run([
    "ffmpeg", "-y", "-v", "error",
    "-f", "h264", "-i", raw_path,
    "-c", "copy", "-bsf:v", "h264_mp4toannexb",
    "-f", "h264", h264_out
], capture_output=True, text=True)
print(f"  exit: {r.returncode}")
if r.stderr: print(f"  stderr: {r.stderr[:300]}")
if os.path.exists(h264_out):
    print(f"  ✅ {h264_out} ({os.path.getsize(h264_out):,} bytes)")
