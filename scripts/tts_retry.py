"""Ξανατρέχει ΜΟΝΟ τα χαμένα chunks (09,10,11,12,13,16) με μεγαλύτερο timeout.
Επίσης: retry σε αποτυχία.
"""
import os, json, urllib.request, time, subprocess

K = [l.split("=", 1)[1].strip().strip('"').strip("'")
     for l in open(os.path.expandvars(r"%LOCALAPPDATA%\hermes\.env"), encoding="utf-8").read().splitlines()
     if l.startswith("HIGGSFIELD_API_KEY=")][0]

API = "https://api.higgsfield.ai"
URL = f"{API}/minimax/speech-2.8-hd"
OUT = r"C:\Users\andys\privacy-yt\_video-work\vo-parts"
VOICE = "English_expressive_narrator"

ALL_CHUNKS = {
    9:  "Years of your saved preferences, gone.",
    10: "And YouTube becomes a search box that does not know you.",
    11: "I turned everything off because I wanted privacy. I did not want to start from zero.",
    12: "So I built PrivacyYouTuber. Your own library for YouTube.",
    13: "Search it. Save it. Tag it. Take notes at the exact second.",
    16: "PrivacyYouTuber. Your YouTube, on your own terms.",
}

def submit(text):
    body = json.dumps({"text": text, "voice_setting": {"voice_id": VOICE}}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
        headers={"Authorization": f"Key {K}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=90))["request_id"]

def poll(rid, timeout=400):
    url = f"{API}/requests/{rid}/status"
    req = urllib.request.Request(url, headers={"Authorization": f"Key {K}"})
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30))
            st = d.get("status")
            if st == "completed":
                return (d.get("audio") or {}).get("url")
            if st in ("failed", "error", "canceled"):
                return None
        except Exception:
            pass
        time.sleep(5)
    return None

print("=== ΞΑΝΑΤΡΕΧΩ ΤΑ ΧΑΜΕΝΑ ===")
for i in sorted(ALL_CHUNKS):
    fp = os.path.join(OUT, f"chunk{i:02d}.mp3")
    if os.path.exists(fp):
        print(f"  [{i:02d}] υπάρχει, skip")
        continue
    ok = False
    for attempt in range(3):
        try:
            rid = submit(ALL_CHUNKS[i])
            u = poll(rid)
            if u:
                urllib.request.urlretrieve(u, fp)
                dur = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                                      "-of","default=noprint_wrappers=1:nokey=1", fp],
                                     capture_output=True, text=True).stdout.strip()
                print(f"  [{i:02d}] ✅ {float(dur):5.2f}s (attempt {attempt+1})")
                ok = True
                break
        except Exception as e:
            print(f"  [{i:02d}] attempt {attempt+1} ERR: {str(e)[:60]}")
        time.sleep(3)
    if not ok:
        print(f"  [{i:02d}] ❌ ΑΠΕΤΥΧΕ")

print("\n=== ΣΥΝΟΛΟ ===")
n = len([f for f in os.listdir(OUT) if f.endswith('.mp3')])
print(f"  {n}/16 chunks")
