"""
Έλεγχος tooltips (data-i18n-title): ποια έχουν ΕΛΛΗΝΙΚΗ μετάφραση στο i18n.json
και ποια ΟΧΙ (= μένουν αγγλικά σε ελληνικό mode).
"""
import re, json

h = open("web/index.html", encoding="utf-8").read()
d = json.load(open("web/i18n.json", encoding="utf-8"))

# Όλα τα data-i18n-title keys που χρησιμοποιούνται
keys = sorted(set(re.findall(r'data-i18n-title="([^"]+)"', h)))

print(f"=== TOOLTIPS ΠΟΥ ΧΡΗΣΙΜΟΠΟΙΟΥΝΤΑΙ: {len(keys)} ===\n")

missing = []
ok = []
for k in keys:
    if k not in d:
        missing.append((k, "❌ ΔΕΝ ΥΠΑΡΧΕΙ KEY"))
    else:
        el = d[k].get("el", "")
        en = d[k].get("en", "")
        if el == en:
            missing.append((k, f"⚠️ ΙΔΙΟ με EN: {en!r}"))
        else:
            ok.append((k, en, el))

print(f"✅ ΜΕ ΣΩΣΤΗ ΕΛΛΗΝΙΚΗ ΜΕΤΑΦΡΑΣΗ: {len(ok)}")
for k, en, el in ok:
    print(f"   {k}")
    print(f"      EN: {en}")
    print(f"      EL: {el}")

print(f"\n❌ ΠΡΟΒΛΗΜΑΤΙΚΑ (μένουν αγγλικά): {len(missing)}")
for k, why in missing:
    print(f"   {k} — {why}")
    if k in d:
        print(f"      EN: {d[k].get('en')}")
