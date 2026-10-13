#!/usr/bin/env python3
"""Σβήνει το offer code TESTSERIAL1 — ΧΩΡΙΣ να εκθέσει το token."""
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

def _req(url, method="GET", data=None):
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "PrivacyYouTuber/1.0"}
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

# 1. Βρες το id του offer code
codes = _req(f"https://api.gumroad.com/v2/products/{pid}/offer_codes")
ocs = codes.get("offer_codes", [])
target = next((c for c in ocs if c.get("name") == "TESTSERIAL1"), None)

if not target:
    print("Το TESTSERIAL1 δεν βρέθηκε (ίσως ήδη σβησμένο). Τίποτα να γίνει.")
else:
    oc_id = target.get("id")
    # 2. DELETE
    req = urllib.request.Request(
        f"https://api.gumroad.com/v2/products/{pid}/offer_codes/{oc_id}",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "PrivacyYouTuber/1.0"},
        method="DELETE",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read().decode("utf-8"))
    print(f"✅ Offer code TESTSERIAL1 ΣΒΗΣΤΗΚΕ (id={oc_id})")
    print("   success =", resp.get("success", True))
