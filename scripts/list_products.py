#!/usr/bin/env python3
"""Διαβάζει το σωστό product_id από το Gumroad API — ΧΩΡΙΣ να εκθέσει το token.

Ασφάλεια:
- Το GUMROAD_ACCESS_TOKEN διαβάζεται ΜΟΝΟ από το .env, και ΠΟΤΕ δεν τυπώνεται.
- Τυπώνει ΜΟΝΟ δημόσια πεδία: name, id, permalink, published.
"""
import os, json, urllib.request

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

if not token:
    print("ERROR: GUMROAD_ACCESS_TOKEN not found in .env")
    raise SystemExit(1)

req = urllib.request.Request(
    "https://api.gumroad.com/v2/products",
    headers={"Authorization": f"Bearer {token}", "User-Agent": "PrivacyYouTuber/1.0"},
)

with urllib.request.urlopen(req, timeout=30) as r:
    data = json.loads(r.read().decode("utf-8"))

products = data.get("products", [])

print("─" * 60)
print(f"Βρέθηκαν {len(products)} προϊόντα:")
print("─" * 60)
for p in products:
    # Τυπώνουμε ΜΟΝΟ δημόσια/ασφαλή πεδία. ΠΟΤΕ token, ΠΟΤΕ sales data.
    name = p.get("name", "(χωρίς όνομα)")
    pid = p.get("id", "?")
    permalink = p.get("permalink", "?")
    published = p.get("published", "?")
    price = p.get("price", "?")
    print(f"  • {name}")
    print(f"      id         = {pid}")
    print(f"      permalink  = {permalink}")
    print(f"      published  = {published}")
    print(f"      price      = {price}")
    print()
