#!/usr/bin/env python3
"""Βρίσκει το permalink/short_url του προϊόντος — ΜΟΝΟ δημόσια πεδία."""
import json, urllib.request, urllib.parse, urllib.error

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
token = env.get("GUMROAD_ACCESS_TOKEN", "")
pid = env.get("GUMROAD_PRODUCT_ID", "")

def _req(url, data=None):
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "PrivacyYouTuber/1.0"}
    if data is not None:
        data = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

# GET το ΕΝΑ προϊόν (όχι λίστα) — μπορεί να δίνει short_url/permalink
try:
    p = _req(f"https://api.gumroad.com/v2/products/{pid}")
    prod = p.get("product", p)
    print("Πεδία που επιστρέφει το προϊόν (ΜΟΝΟ δημόσια):")
    for k in sorted(prod.keys()):
        if k in ("name", "id", "permalink", "short_url", "url", "custom_permalink"):
            print(f"  {k} = {prod.get(k)}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode('utf-8','ignore')[:200]}")
