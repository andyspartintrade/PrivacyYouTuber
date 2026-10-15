"""Δοκιμή 3 φωνών MiniMax Speech 2.8 HD μέσω HiggsField API.
Κείμενο: το hook του βίντεο. Σκοπός: να διαλέξει ο χρήστης.
"""
import os, json, urllib.request, time

KEY = None
for line in open(os.path.expandvars(r"%LOCALAPPDATA%\hermes\.env"), encoding="utf-8"):
    if line.strip().startswith("HIGGSFIELD_API_KEY="):
        KEY = line.split("=", 1)[1].strip().strip('"').strip("'")

API = "https://api.higgsfield.ai"
URL = f"{API}/minimax/speech-2.8-hd"
OUT = r"C:\Users\andys\privacy-yt\_video-work\voice-tests"
os.makedirs(OUT, exist_ok=True)

TEXT = ("This is YouTube, with everything turned off. "
        "No account. No history. No recommendations. "
        "Sounds private, doesn't it?")

VOICES = [
    ("English_Deep-VoicedGentleman", "deep-gentleman"),
    ("English_expressive_narrator", "expressive-narrator"),
    ("English_Trustworth_Man", "trustworthy"),
]

def submit(text, voice_id):
    body = json.dumps({"text": text, "voice_setting": {"voice_id": voice_id}}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
        headers={"Authorization": f"Key {KEY}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))

def poll(rid, timeout=180):
    url = f"{API}/requests/{rid}/status"
    req = urllib.request.Request(url, headers={"Authorization": f"Key {KEY}"})
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = json.load(urllib.request.urlopen(req, timeout=30))
        st = d.get("status")
        if st in ("completed", "succeeded", "done"):
            return d
        if st in ("failed", "error", "canceled"):
            return d
        time.sleep(4)
    return {"status": "timeout"}

print("=== ΔΟΚΙΜΗ 3 ΦΩΝΩΝ ===")
for voice_id, tag in VOICES:
    try:
        r = submit(TEXT, voice_id)
        rid = r.get("request_id")
        print(f"\n[{tag}] submitted: {rid}")
        res = poll(rid)
        print(f"  status: {res.get('status')}")
        # Βρες το output URL
        out = res.get("output") or res.get("result") or {}
        urls = []
        if isinstance(out, dict):
            for k in ("audio_url", "url", "audio", "files"):
                v = out.get(k)
                if isinstance(v, str): urls.append(v)
                elif isinstance(v, list):
                    for it in v:
                        if isinstance(it, str): urls.append(it)
                        elif isinstance(it, dict) and it.get("url"): urls.append(it["url"])
        elif isinstance(out, list):
            for it in out:
                if isinstance(it, str): urls.append(it)
                elif isinstance(it, dict) and it.get("url"): urls.append(it["url"])
        print(f"  urls: {urls}")
        if urls:
            ext = "mp3"
            fp = os.path.join(OUT, f"{tag}.{ext}")
            urllib.request.urlretrieve(urls[0], fp)
            print(f"  ✅ {fp} ({os.path.getsize(fp)//1024} KB)")
        else:
            print(f"  RAW: {json.dumps(res)[:400]}")
    except Exception as e:
        print(f"  [{tag}] ERR: {str(e)[:200]}")
