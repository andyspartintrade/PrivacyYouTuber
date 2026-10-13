#!/usr/bin/env python3
"""Ελέγχει αν το product_id είναι το ΣΩΣΤΟ για licensing, καλώντας το /verify
με ένα προφανώς ψεύτικο key. ΑΣΦΑΛΕΣ: δεν τυπώνει token, δεν τυπώνει πραγματικό key."""
import os, json, urllib.request, urllib.parse

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

# Ένα προφανώς ψεύτικο key (δοκιμαστικό). Δεν είναι πραγματικό.
fake_key = "TEST-FAKE-KEY-0000-0000-0000"

body = urllib.parse.urlencode({
    "product_id": pid,
    "license_key": fake_key,
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
        print("HTTP 200 — το product_id ΕΙΝΑΙ σωστό για licensing (το block υπάρχει).")
        print("  success =", resp.get("success"))
        print("  (αναμένεται False, αφού το key είναι ψεύτικο)")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", "ignore")
    print(f"HTTP {e.code} — το endpoint επέστρεψε σφάλμα:")
    print("  ", body[:300])
    if e.code == 404:
        print("  → ΣΗΜΑΙΝΕΙ: το license key block ΔΕΝ είναι ενεργοποιημένο, ή το product_id είναι λάθος.")
