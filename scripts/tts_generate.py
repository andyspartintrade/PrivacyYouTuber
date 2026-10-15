"""Πλήρες voiceover μέσω HiggsField (MiniMax Speech 2.8 HD).
Φωνή: English_expressive_narrator
Χωρίζει το σενάριο σε chunks (για καλύτερο έλεγχο pacing) και τα ενώνει.
"""
import os, json, urllib.request, time, subprocess

K = [l.split("=", 1)[1].strip().strip('"').strip("'")
     for l in open(os.path.expandvars(r"%LOCALAPPDATA%\hermes\.env"), encoding="utf-8").read().splitlines()
     if l.startswith("HIGGSFIELD_API_KEY=")][0]

API = "https://api.higgsfield.ai"
URL = f"{API}/minimax/speech-2.8-hd"
OUT = r"C:\Users\andys\privacy-yt\_video-work\vo-parts"
os.makedirs(OUT, exist_ok=True)
VOICE = "English_expressive_narrator"

# Το σενάριο σε chunks — κάθε chunk = μια ιδέα (φυσικές παύσεις)
CHUNKS = [
    "This is YouTube, with everything turned off.",
    "No account. No history. No recommendations.",
    "Sounds private, doesn't it?",
    "Open your subscriptions, and there is nothing there.",
    "Don't miss new videos. You already missed all of them.",
    "Open your history. Nothing.",
    "Keep track of what you watch. You can't. Not anymore.",
    "So you search for wildlife, and you get generic results. Nothing like what you are used to.",
    "Years of your saved preferences, gone.",
    "And YouTube becomes a search box that does not know you.",
    "I turned everything off because I wanted privacy. I did not want to start from zero.",
    "So I built PrivacyYouTuber. Your own library for YouTube.",
    "Search it. Save it. Tag it. Take notes at the exact second.",
    "No account. No tracking. No ads.",
    "Remember what you watch, without telling Google, YouTube, or their partners. No one.",
    "PrivacyYouTuber. Your YouTube, on your own terms.",
]

def submit(text):
    body = json.dumps({"text": text, "voice_setting": {"voice_id": VOICE}}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
        headers={"Authorization": f"Key {K}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))["request_id"]

def poll(rid, timeout=240):
    url = f"{API}/requests/{rid}/status"
    req = urllib.request.Request(url, headers={"Authorization": f"Key {K}"})
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = json.load(urllib.request.urlopen(req, timeout=30))
        st = d.get("status")
        if st == "completed":
            u = (d.get("audio") or {}).get("url")
            return u
        if st in ("failed", "error", "canceled"):
            return None
        time.sleep(3)
    return None

print(f"=== VOICEOVER: {len(CHUNKS)} chunks, φωνή={VOICE} ===")
for i, ch in enumerate(CHUNKS, 1):
    try:
        rid = submit(ch)
        u = poll(rid)
        if u:
            fp = os.path.join(OUT, f"chunk{i:02d}.mp3")
            urllib.request.urlretrieve(u, fp)
            dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                  "-of", "default=noprint_wrappers=1:nokey=1", fp],
                                 capture_output=True, text=True).stdout.strip()
            print(f"  [{i:02d}] {float(dur):5.2f}s  {ch[:45]}...")
        else:
            print(f"  [{i:02d}] ❌ FAILED: {ch[:40]}")
    except Exception as e:
        print(f"  [{i:02d}] ERR: {str(e)[:90]}")
    time.sleep(0.5)

print("\n✅ Τα chunks είναι στο:", OUT)
