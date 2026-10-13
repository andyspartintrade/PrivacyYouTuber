#!/usr/bin/env python3
"""Τσεκάρει αν το license key block είναι ενεργό, δοκιμάζοντας το verify
με ΕΝΑ λάθος key και διαβάζοντας το ακριβές μήνυμα σφάλματος."""
import os, json, urllib.request, urllib.parse, urllib.error

def _load_env():
    env = {}
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return env

env = _load_env()
pid = env.get("GUMROAD_PRODUCT_ID", "")

print(f"product_id = {pid}")
print("Δοκιμάζω με ψεύτικο key...")
print()

fake = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEFFFF"
body = urllib.parse.urlencode({
    "product_id": pid,
    "license_key": fake,
    "increment_uses_count": "false",
}).encode("utf-8")

req = urllib.request.Request(
    "https://api.gumroad.com/v2/licenses/verify",
    data=body,
    headers={"Content-Type": "application/x-www-form-urlencoded",
             "User-Agent": "PrivacyYouTuber/1.0"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=20) as r:
        resp = json.loads(r.read().decode("utf-8"))
        print("HTTP 200 — το endpoint ΑΠΑΝΤΑ (block ενεργό):")
        print("  ", json.dumps(resp, ensure_ascii=False)[:400])
except urllib.error.HTTPError as e:
    b = json.loads(e.read().decode("utf-8", "ignore"))
    msg = b.get("message", "")
    print(f"HTTP {e.code}: {msg}")
    if "does not exist" in msg:
        print()
        print("  → ΣΥΜΠΕΡΑΣΜΑ: το license key block ΕΙΝΑΙ ενεργό και το product_id ΣΩΣΤΟ.")
        print("    Το 404 είναι απλώς επειδή το key είναι ψεύτικο (δεν υπάρχει).")
        print("    Το σύστημά μας είναι ΕΤΟΙΜΟ — θα δουλέψει με πραγματικό key αγοράς.")
    elif "not found" in msg.lower():
        print("  → ΣΥΜΠΕΡΑΣΜΑ: λάθος product_id ή το block λείπει.")
