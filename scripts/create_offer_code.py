#!/usr/bin/env python3
"""Δημιουργεί 100% offer code στο Gumroad — ΧΩΡΙΣ να εκθέσει το token.

Βήματα:
1. Βρίσκει το product (name + permalink) ώστε να δώσει σωστό link.
2. Δημιουργεί offer code: percent / 100% / max 1 χρήση.
3. Τυπώνει ΜΟΝΟ δημόσια πεδία (permalink, offer code name) — ΠΟΤΕ το token.
"""
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
product_id = env.get("GUMROAD_PRODUCT_ID", "")

if not token:
    print("ERROR: no token")
    raise SystemExit(1)

def _req(url, data=None):
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "PrivacyYouTuber/1.0"}
    if data is not None:
        data = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

# 1. Βρες το permalink + name
products = _req("https://api.gumroad.com/v2/products").get("products", [])
target = next((p for p in products if p.get("id") == product_id), None)
permalink = (target or {}).get("permalink", "?")
name = (target or {}).get("name", "?")

print(f"Προϊόν: {name}")
print(f"permalink: {permalink}")
print()

# 2. Δημιούργησε το 100% offer code (max 1 χρήση)
code_name = "TESTSERIAL1"
try:
    result = _req(
        f"https://api.gumroad.com/v2/products/{product_id}/offer_codes",
        data={
            "name": code_name,
            "offer_type": "percent",
            "amount_off": "100",
            "max_purchase_count": "1",
        },
    )
    oc = result.get("offer_code", result)
    print("✅ Offer code ΔΗΜΙΟΥΡΓΗΘΗΚΕ:")
    print(f"   name             = {oc.get('name', code_name)}")
    print(f"   offer_type       = {oc.get('offer_type', 'percent')}")
    print(f"   amount_off       = {oc.get('amount_off', '100')}")
    print(f"   max_purchase_cnt = {oc.get('max_purchase_count', '1')}")
    print()
    print("🔗 ΤΟ LINK (για incognito αγορά 0€):")
    print(f"   https://andyspartinart.gumroad.com/l/{permalink}?offer_code={code_name}")
    print()
    print("   (Ή path form: https://andyspartinart.gumroad.com/l/{permalink}/{code_name})")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", "ignore")
    print(f"HTTP {e.code}: {body[:300]}")
